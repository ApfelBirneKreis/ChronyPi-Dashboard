from flask import Flask, render_template, jsonify, request, Response
from flask_cors import CORS
import subprocess
import sqlite3
import datetime
import os

app = Flask(__name__)
CORS(app)

DB_NAME = "chrony_history.db"

def init_db():
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                system_offset REAL,
                frequency REAL,
                stratum INTEGER,
                temperature REAL,
                skew REAL,
                residual_freq REAL
            )
        ''')
        # Migration für bestehende Datenbanken (falls Spalten fehlen)
        for col, col_type in [('temperature', 'REAL'), ('skew', 'REAL'), ('residual_freq', 'REAL')]:
            try:
                cursor.execute(f"ALTER TABLE history ADD COLUMN {col} {col_type}")
            except sqlite3.OperationalError:
                pass

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        defaults = {
            'polling_interval': '5',
            'warning_offset': '10.0',
            'warning_drift': '50.0',
            'retention_days': '7',
            'show_invalid_sources': 'false'
        }
        for k, v in defaults.items():
            cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error initializing DB: {e}")

def safe_float(val, default=0.0):
    try:
        clean_val = str(val).split()[0]
        return float(clean_val)
    except (ValueError, TypeError):
        return default

def safe_int(val, default=0):
    try:
        clean_val = str(val).split()[0]
        return int(clean_val)
    except (ValueError, TypeError):
        return default

def get_pi_temperature():
    try:
        output = subprocess.check_output(["vcgencmd", "measure_temp"], universal_newlines=True, timeout=1)
        if "=" in output and "'C" in output:
            val = output.split("=")[1].split("'C")[0]
            return float(val)
    except Exception:
        pass
    
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            val = int(f.read().strip()) / 1000.0
            return float(val)
    except Exception:
        return 0.0

def parse_tracking():
    data = {
        "reference_id": "-",
        "reference_name": "-",
        "system_time": "-",
        "stratum": "-",
        "frequency": "-",
        "rms_offset": "-",
        "root_delay": "-",
        "root_dispersion": "-",
        "skew": "0.0",
        "residual_freq": "0.0",
        "leap_status": "Not Synchronized",
        "is_synced": False,
        "chrony_alive": False,
        "temperature": get_pi_temperature()
    }
    try:
        output = subprocess.check_output(["chronyc", "tracking"], universal_newlines=True, timeout=2)
        data["chrony_alive"] = True
        for line in output.splitlines():
            parts = line.split(":", 1)
            if len(parts) == 2:
                key = parts[0].strip().lower().replace(" ", "_")
                val = parts[1].strip()
                data[key] = val
        
        ref_id = data.get("reference_id", "")
        leap = data.get("leap_status", "").lower()
        if ref_id and not ref_id.startswith("00000000") and "not synchronized" not in leap:
            data["is_synced"] = True
            
    except Exception as e:
        print(f"Warning: Could not run 'chronyc tracking': {e}")
    return data

def parse_sources():
    sources = []
    ref_ip = "-"
    ref_name = "-"
    has_active_source = False
    try:
        output = subprocess.check_output(["chronyc", "sources"], universal_newlines=True, timeout=2)
        lines = output.splitlines()
        for line in lines[2:]:
            if not line.strip():
                continue
            parts = line.split()
            if len(parts) >= 7:
                ms = parts[0]
                name = parts[1]
                
                mode = ms[0] if len(ms) > 0 else "^"
                state_char = ms[1] if len(ms) > 1 else "?"
                
                if mode == '#':
                    source_type = "GPS / Local"
                elif mode == '=':
                    source_type = "Peer"
                else:
                    source_type = "NTP / NTS"
                    
                is_valid = state_char not in ['?', 'x', '~'] and parts[4] != '0'
                
                sources.append({
                    "state": ms,
                    "mode": mode,
                    "state_char": state_char,
                    "type": source_type,
                    "is_valid": is_valid,
                    "name": name,
                    "stratum": parts[2],
                    "poll": parts[3],
                    "reach": parts[4],
                    "last_rx": parts[5],
                    "sample": " ".join(parts[6:])
                })
                if "*" in ms:
                    ref_name = name
                    ref_ip = name
                    has_active_source = True
    except Exception as e:
        print(f"Warning: Could not run 'chronyc sources': {e}")
    return sources, ref_ip, ref_name, has_active_source

def parse_clients():
    clients = []
    try:
        output = subprocess.check_output(["chronyc", "clients"], universal_newlines=True, timeout=2)
        lines = output.splitlines()
        for line in lines:
            if "Hostname" in line or "===" in line or not line.strip():
                continue
            parts = line.split()
            if len(parts) >= 2:
                clients.append({
                    "hostname": parts[0],
                    "ntp_packets": safe_int(parts[1]),
                    "drop_packets": safe_int(parts[5]) if len(parts) > 5 else 0,
                    "interval": f"{parts[6]}s" if len(parts) > 6 else "-",
                    "last": f"{parts[3]}s ago" if len(parts) > 3 else "-"
                })
    except Exception as e:
        print(f"Warning: Could not run 'chronyc clients': {e}")
    return clients

def prune_database():
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = 'retention_days'")
        row = cursor.fetchone()
        days = int(row[0]) if row and row[0].isdigit() else 7
        
        cursor.execute("DELETE FROM history WHERE timestamp < datetime('now', ?)", (f"-{days} days",))
        cursor.execute("DELETE FROM history WHERE id NOT IN (SELECT id FROM history ORDER BY id DESC LIMIT 20000)")
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error pruning DB: {e}")

def save_history(tracking):
    try:
        sys_offset_raw = tracking.get("system_time", "0")
        sys_offset = safe_float(sys_offset_raw)
        if "slow" in sys_offset_raw:
            sys_offset = -sys_offset

        freq = safe_float(tracking.get("frequency", "0"))
        stratum = safe_int(tracking.get("stratum", "0"))
        temp = tracking.get("temperature", 0.0)
        skew = safe_float(tracking.get("skew", "0"))
        res_freq = safe_float(tracking.get("residual_freq", "0"))

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO history (timestamp, system_offset, frequency, stratum, temperature, skew, residual_freq) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (datetime.datetime.now().isoformat(), sys_offset, freq, stratum, temp, skew, res_freq)
        )
        conn.commit()
        conn.close()
        prune_database()
    except Exception as e:
        print(f"Error saving history: {e}")

def get_min_max_stats():
    stats = {
        "24h": {"min_offset": 0, "max_offset": 0, "min_freq": 0, "max_freq": 0},
        "72h": {"min_offset": 0, "max_offset": 0, "min_freq": 0, "max_freq": 0}
    }
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute("SELECT MIN(system_offset), MAX(system_offset), MIN(frequency), MAX(frequency) FROM history WHERE timestamp >= datetime('now', '-1 day')")
        row24 = cursor.fetchone()
        if row24 and row24[0] is not None:
            stats["24h"] = {
                "min_offset": row24[0] * 1000000,
                "max_offset": row24[1] * 1000000,
                "min_freq": row24[2] or 0,
                "max_freq": row24[3] or 0
            }
            
        cursor.execute("SELECT MIN(system_offset), MAX(system_offset), MIN(frequency), MAX(frequency) FROM history WHERE timestamp >= datetime('now', '-3 days')")
        row72 = cursor.fetchone()
        if row72 and row72[0] is not None:
            stats["72h"] = {
                "min_offset": row72[0] * 1000000,
                "max_offset": row72[1] * 1000000,
                "min_freq": row72[2] or 0,
                "max_freq": row72[3] or 0
            }
        conn.close()
    except Exception as e:
        print(f"Error calculating min/max stats: {e}")
    return stats

def get_db_size_formatted():
    try:
        if os.path.exists(DB_NAME):
            size_bytes = os.path.getsize(DB_NAME)
            if size_bytes < 1024 * 1024:
                return f"{size_bytes / 1024:.1f} KB"
            else:
                return f"{size_bytes / (1024 * 1024):.2f} MB"
    except Exception:
        pass
    return "Unknown"

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/chrony")
def get_chrony():
    try:
        tracking = parse_tracking()
        save_history(tracking)
        sources, ref_ip, ref_name, has_active_source = parse_sources()
        clients = parse_clients()
        stats = get_min_max_stats()
        
        is_fully_synced = tracking.get("is_synced", False) and has_active_source
        
        history = []
        try:
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("SELECT timestamp, system_offset, frequency, stratum, temperature, skew, residual_freq FROM history ORDER BY id DESC LIMIT 100")
            rows = cursor.fetchall()
            conn.close()
            for row in reversed(rows):
                history.append({
                    "timestamp": row[0],
                    "system_offset": row[1] if row[1] is not None else 0,
                    "frequency": row[2] if row[2] is not None else 0,
                    "stratum": row[3] if row[3] is not None else 0,
                    "temperature": row[4] if row[4] is not None else 0,
                    "skew": row[5] if row[5] is not None else 0,
                    "residual_freq": row[6] if row[6] is not None else 0
                })
        except Exception as e:
            print(f"Error reading history: {e}")

        return jsonify({
            "tracking": tracking,
            "sources": sources,
            "clients": clients,
            "history": history,
            "ref_ip": ref_ip,
            "ref_name": ref_name,
            "stats": stats,
            "is_synced": is_fully_synced,
            "db_size": get_db_size_formatted()
        })
    except Exception as e:
        print(f"API Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/reset-history", methods=["POST"])
def reset_history():
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM history")
        conn.commit()
        conn.close()
        return jsonify({"status": "success", "message": "Statistiken wurden zurückgesetzt."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/export/csv")
def export_csv():
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT timestamp, system_offset, frequency, stratum, temperature, skew, residual_freq FROM history ORDER BY id ASC")
        rows = cursor.fetchall()
        conn.close()
        
        csv_data = "timestamp,system_offset_seconds,frequency_ppm,stratum,temperature_c,skew_ppm,residual_freq_ppm\n"
        for row in rows:
            csv_data += f"{row[0]},{row[1]},{row[2]},{row[3]},{row[4]},{row[5]},{row[6]}\n"
            
        return Response(
            csv_data,
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment;filename=chrony_history_export.csv"}
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/settings", methods=["GET", "POST"])
def handle_settings():
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        if request.method == "POST":
            data = request.json or {}
            for key, value in data.items():
                cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
            conn.commit()
            conn.close()
            return jsonify({"status": "success", "message": "Settings saved"})
        else:
            cursor.execute("SELECT key, value FROM settings")
            settings = {row[0]: row[1] for row in cursor.fetchall()}
            conn.close()
            return jsonify(settings)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=8080)
