import re
import sqlite3
import subprocess
import threading
import time
from flask import Flask, jsonify, render_template
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

DB_PATH = "/opt/chrony-dashboard/chrony_history.db"


def init_db():
  conn = sqlite3.connect(DB_PATH)
  cursor = conn.cursor()
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS history (
            timestamp INTEGER PRIMARY KEY,
            offset REAL,
            freq REAL,
            stratum INTEGER,
            root_delay REAL
        )
    """)
  conn.commit()
  conn.close()


def run_cmd(cmd):
  try:
    return subprocess.check_output(cmd, shell=True, text=True, timeout=5)
  except Exception as e:
    return ""


def parse_tracking():
  raw = run_cmd("chronyc tracking")
  data = {}
  for line in raw.splitlines():
    if ":" in line:
      k, v = line.split(":", 1)
      data[k.strip()] = v.strip()

  sys_time = data.get("System time", "0.000000000 seconds slow of NTP time")
  offset_us = 0.0
  match = re.search(r"([0-9\.]+)\s+seconds\s+(slow|fast)", sys_time)
  if match:
    val = float(match.group(1)) * 1_000_000
    offset_us = -val if match.group(2) == "slow" else val

  freq_ppm = 0.0
  freq_str = data.get("Frequency", "0.0 ppm")
  match_freq = re.search(r"([-+]?[0-9\.]+)", freq_str)
  if match_freq:
    freq_ppm = float(match_freq.group(1))

  stratum = 2
  try:
    stratum = int(data.get("Stratum", "2"))
  except ValueError:
    pass

  return {
      "reference_id": data.get("Reference ID", "N/A"),
      "system_offset": f"{offset_us:+.2f} µs",
      "offset_raw": offset_us,
      "stratum": stratum,
      "frequency": f"{freq_ppm:+.3f} ppm",
      "freq_raw": freq_ppm,
      "root_delay": data.get("Root delay", "0.000000000 seconds"),
      "root_dispersion": data.get("Root dispersion", "0.000000000 seconds"),
      "rms_offset": data.get("RMS offset", "0.000000 seconds"),
  }


def parse_sources():
  raw = run_cmd("chronyc sources")
  sources = []
  for line in raw.splitlines():
    if line.startswith("MS") or line.startswith("==") or not line.strip():
      continue
    parts = line.split()
    if len(parts) >= 9:
      mode_state = parts[0]
      state_char = mode_state[1] if len(mode_state) > 1 else mode_state[0]
      sources.append({
          "state": state_char,
          "name": parts[1],
          "ip": parts[1],
          "stratum": parts[2],
          "poll": parts[3],
          "reach": parts[4],
          "lastRx": parts[5],
          "offset": parts[6] + " " + parts[7],
          "jitter": parts[8] if len(parts) > 8 else "N/A",
      })
  return sources


def parse_clients():
  raw = run_cmd("chronyc clients")
  clients = []
  parsing = False
  for line in raw.splitlines():
    if "===" in line:
      parsing = True
      continue
    if parsing and line.strip():
      parts = line.split()
      if len(parts) >= 8:
        ip = parts[0]
        proto = "IPv6" if ":" in ip else "IPv4"
        clients.append({
            "ip": ip,
            "hostname": ip,
            "type": proto,
            "packets": int(parts[1]),
            "version": 4,
            "drops": int(parts[4]) if len(parts) > 4 else 0,
            "lastAccess": (
                parts[6] + "s ago" if len(parts) > 6 else parts[5] + "s ago"
            ),
            "poll": parts[2] if len(parts) > 2 else "N/A",
        })
  return clients


def background_poller():
  while True:
    try:
      t_data = parse_tracking()
      conn = sqlite3.connect(DB_PATH)
      cursor = conn.cursor()
      cursor.execute(
          "INSERT OR REPLACE INTO history (timestamp, offset, freq, stratum,"
          " root_delay) VALUES (?, ?, ?, ?, ?)",
          (
              int(time.time()),
              t_data["offset_raw"],
              t_data["freq_raw"],
              t_data["stratum"],
              0.0,
          ),
      )
      conn.commit()
      conn.close()
    except Exception as e:
      print("Poller error:", e)
    time.sleep(30)


@app.route("/")
def index():
  return render_template("index.html")


@app.route("/api/chrony")
def get_chrony():
  tracking = parse_tracking()
  sources = parse_sources()
  clients = parse_clients()

  conn = sqlite3.connect(DB_PATH)
  cursor = conn.cursor()
  cursor.execute(
      "SELECT timestamp, offset, freq FROM history ORDER BY timestamp ASC"
  )
  rows = cursor.fetchall()
  conn.close()

  history = [{"ts": r[0], "offset": r[1], "freq": r[2]} for r in rows]

  return jsonify({
      "status": "synchronized",
      "tracking": tracking,
      "sources": sources,
      "clients": clients,
      "history": history,
  })


if __name__ == "__main__":
  init_db()
  t = threading.Thread(target=background_poller, daemon=True)
  t.start()
  app.run(host="0.0.0.0", port=8080)
