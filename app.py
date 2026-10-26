from flask import Flask, render_template, jsonify, request, Response
from flask_cors import CORS
import subprocess
import sqlite3
import datetime

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
                stratum INTEGER
            )
        ''')
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
            'retention_days': '7'
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

def parse_tracking():
    data = {}
    try:
        output = subprocess.check_output(["chronyc", "tracking"], universal_newlines=True, timeout=2)
        for line in output.splitlines():
            parts = line.split(":", 1)
            if len(parts) == 2:
                key = parts[0].strip().lower().replace(" ", "_")
                val = parts[1].strip()
                data[key] = val
    except Exception as e:
        print(f"Error parsing tracking: {e}")
    return data

def parse_sources():
    sources = []
    ref_ip = "-"
    ref_name = "-"
    try:
        output = subprocess.check_output(["chronyc", "sources"], universal_newlines=True, timeout=2)
        lines = output.splitlines()
        for line in lines[2:]:
            if not line.strip():
                continue
            parts = line.split()
            if len(parts) >= 7:
                state = parts[0]
                name = parts[1]
                sources.append({
                    "state": state,
                    "name": name,
                    "stratum": parts[2],
                    "poll": parts[3],
                    "reach": parts[4],
                    "last_rx": parts[5],
                    "sample": " ".join(parts[6:])
                })
                if "*" in state:
                    ref_name = name
                    ref_ip = name
    except Exception as e:
        print(f"Error parsing sources: {e}")
    return sources, ref_ip, ref_name

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
        print(f"Error parsing clients: {e}")
    return clients

def prune_database():
    """ Überwacht und begrenzt die Datenbankgröße & löscht alte Einträge """
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Auf Retention-Days prüfen (Standard 7 Tage)
        cursor.execute("SELECT value FROM settings WHERE key = 'retention_days'")
        row = cursor.fetchone()
        days = int(row[0]) if row and row[0].isdigit() else 7
        
        # Alte Daten löschen
        cursor.execute("DELETE FROM history WHERE timestamp < datetime('now', ?)", (f"-{days} days",))
        
        # Absolute Obergrenze erzwingen (maximal 20.000 Messpunkte, um Aufblähen zu verhindern)
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

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO history (timestamp, system_offset, frequency, stratum) VALUES (?, ?, ?, ?)",
            (datetime.datetime.now().isoformat(), sys_offset, freq, stratum)
        )
        conn.commit()
        conn.close()
        
        # Datenbankgröße regulieren
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

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/chrony")
def get_chrony():
    try:
        tracking = parse_tracking()
        save_history(tracking)
        sources, ref_ip, ref_name = parse_sources()
        clients = parse_clients()
        stats = get_min_max_stats()
        
        history = []
        try:
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("SELECT timestamp, system_offset, frequency, stratum FROM history ORDER BY id DESC LIMIT 100")
            rows = cursor.fetchall()
            conn.close()
            for row in reversed(rows):
                history.append({
                    "timestamp": row[0],
                    "system_offset": row[1] if row[1] is not None else 0,
                    "frequency": row[2] if row[2] is not None else 0,
                    "stratum": row[3] if row[3] is not None else 0
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
            "stats": stats
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
        cursor.execute("SELECT timestamp, system_offset, frequency, stratum FROM history ORDER BY id ASC")
        rows = cursor.fetchall()
        conn.close()
        
        csv_data = "timestamp,system_offset_seconds,frequency_ppm,stratum\n"
        for row in rows:
            csv_data += f"{row[0]},{row[1]},{row[2]},{row[3]}\n"
            
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
