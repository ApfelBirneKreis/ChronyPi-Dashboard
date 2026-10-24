# 🕒 ChronyPi Master Dashboard

Ein modernes, leichtgewichtiges Web-Dashboard für den **Chrony NTP-Server** auf dem Raspberry Pi. Es kombiniert historische Offsets & Drifts (im Stil von *Time-Pi*) mit detailliertem Telemetrie- und Client-Monitoring (im Stil von *TICC-DASH*) in einer übersichtlichen Single-Page-App.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.9%2B-green.svg)
![Flask](https://img.shields.io/badge/framework-Flask-000000.svg)
![TailwindCSS](https://img.shields.io/badge/style-TailwindCSS-06B6D4.svg)

---

## 🌟 Key Features

* **Real-time KPI Summary:** Anzeige von Stratum, System Offset (µs), Referenzquelle (z. B. GPS PPS / Upstream NTP), Root Delay und Root Dispersion.
* **Historische Diagramme:** Chart.js-Visualisierung von Uhrzeit-Offset (Microseconds) und Frequenz-Drift (PPM) über die Zeit.
* **Client Telemetrie (TICC-DASH):** Übersicht aller verbundenen Netzwerk-Geräte, die Zeit vom Pi abfragen (inkl. IPv4/IPv6-Zuordnung, Paketanzahlen, Intervallraten und Drop-Anzeigen).
* **Upstream Sources (`chronyc sources`):** Live-Status aller konfigurierten NTP-Peer-Server und Referenz-Uhren.
* **Dark Mode & Responsive UI:** Optimiertes Design mit TailwindCSS und FontAwesome für Desktop und mobile Endgeräte.
* **Leichtgewichtiges Backend:** Python (Flask) speichert historische Messdaten in einer lokalen SQLite-Datenbank.

---

## 📁 Projektstruktur

```text
ChronyPi-Dashboard/
├── app.py                  # Flask Backend & chronyc Parser
├── templates/
│   └── index.html          # Frontend Dashboard (HTML/JS/Chart.js/Tailwind)
├── .gitignore              # Ignorierte Dateien (venv, db, caches)
└── README.md               # Dokumentation


🚀 Installation & Setup
1. Voraussetzungen
Stelle sicher, dass chrony und python3 auf deinem Raspberry Pi installiert sind:

Bash
sudo apt update
sudo apt install -y chrony python3 python3-venv git
2. Repository klonen
Bash
cd /opt
sudo git clone [https://github.com/ApfelBirneKreis/ChronyPi-Dashboard.git](https://github.com/ApfelBirneKreis/ChronyPi-Dashboard.git) chrony-dashboard
sudo chown -R $USER:$USER /opt/chrony-dashboard
cd /opt/chrony-dashboard
3. Virtuelle Python-Umgebung einrichten
Bash
python3 -m venv venv
source venv/bin/activate
pip install flask flask-cors
⚙️ Als Systemd-Dienst einrichten (Autostart)
Damit das Dashboard im Hintergrund läuft und nach jedem Reboot automatisch startet:

Service-Datei erstellen:

Bash
sudo nano /etc/systemd/system/chrony-dashboard.service
Folgenden Inhalt einfügen:

Ini, TOML
[Unit]
Description=Chrony Master Dashboard Service
After=network.target chrony.service

[Service]
User=root
WorkingDirectory=/opt/chrony-dashboard
ExecStart=/opt/chrony-dashboard/venv/bin/python /opt/chrony-dashboard/app.py
Restart=always

[Install]
WantedBy=multi-user.target
Dienst aktivieren und starten:

Bash
sudo systemctl daemon-reload
sudo systemctl enable --now chrony-dashboard.service
Das Dashboard ist nun in deinem Netzwerk unter http://<IP-deines-Pi>:8080 erreichbar!

🛠️ Technologien
Backend: Python 3, Flask, Flask-CORS, SQLite3

Frontend: HTML5, JavaScript (ES6+), TailwindCSS (CDN), FontAwesome 6, Chart.js

System Metrics: chronyc tracking, chronyc sources, chronyc clients
