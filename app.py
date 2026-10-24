from flask import Flask, render_template, jsonify
from flask_cors import CORS
import subprocess
import sqlite3
import datetime

app = Flask(__name__)
CORS(app)

DB_NAME = "chrony_history.db"

def init_db():
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
    conn.commit()
    conn.close()

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
        output = subprocess.check_output(["chronyc", "tracking"], universal_newlines=True)
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
    try:
        output = subprocess.check_output(["chronyc", "sources"], universal_newlines=True)
        lines = output.splitlines()
        for line in lines[2:]:
            if not line.strip():
                continue
            parts = line.split()
            if len(parts) >= 7:
                sources.append({
                    "state": parts[0],
                    "name": parts[1],
                    "stratum": parts[2],
                    "poll": parts[3],
                    "reach": parts[4],
                    "last_rx": parts[5],
                    "sample": " ".join(parts[6:])
                })
    except Exception as e:
        print(f"Error parsing sources: {e}")
    return sources

def parse_clients():
    clients = []
    try:
        output = subprocess.check_output(["chronyc", "clients"], universal_newlines=True)
        lines = output.splitlines()
        for line in lines:
            if "Hostname" in line or "===" in line or not line.strip():
                continue
            parts = line.split()
            if len(parts) >= 2:
                clients.append({
                    "hostname": parts[0],
                    "ntp_packets": safe_int(parts[1]),
                    "drop_packets": safe_int(parts[2]) if len(parts) > 2 else 0,
                    "interval": parts[3] if len(parts) > 3 else "-",
                    "last": parts[5] if len(parts) > 5 else "-"
                })
    except Exception as e:
        print(f"Error parsing clients: {e}")
    return clients

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
    except Exception as e:
        print(f"Error saving history: {e}")

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/chrony")
def get_chrony():
    tracking = parse_tracking()
    save_history(tracking)
    sources = parse_sources()
    clients = parse_clients()
    
    history = []
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT timestamp, system_offset, frequency, stratum FROM history ORDER BY id DESC LIMIT 50")
        rows = cursor.fetchall()
        conn.close()
        for row in reversed(rows):
            history.append({
                "timestamp": row[0],
                "system_offset": row[1],
                "frequency": row[2],
                "stratum": row[3]
            })
    except Exception as e:
        print(f"Error reading history: {e}")

    return jsonify({
        "tracking": tracking,
        "sources": sources,
        "clients": clients,
        "history": history
    })

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=8080)
