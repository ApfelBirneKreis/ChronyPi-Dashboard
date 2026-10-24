# 🕒 ChronyPi Dashboard

Ein modernes, leichtgewichtiges Web-Dashboard für den **Chrony NTP-Server** auf dem Raspberry Pi. Es kombiniert historische Offsets & Drifts (im Stil von *Time-Pi*) mit detailliertem Telemetrie- und Client-Monitoring (im Stil von *TICC-DASH*) sowie einer zentralen Einstellungsverwaltung in einer übersichtlichen Single-Page-App.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.9%2B-green.svg)
![Flask](https://img.shields.io/badge/framework-Flask-000000.svg)
![TailwindCSS](https://img.shields.io/badge/style-TailwindCSS-06B6D4.svg)
![Platform](https://img.shields.io/badge/platform-Raspberry%20Pi-red.svg)

---

## 📸 Dashboard Vorschau

![ChronyPi Dashboard Preview](https://github.com/ApfelBirneKreis/ChronyPi-Dashboard/blob/f45ccaf4df5cb74dbbb8c0db2f61694da54897be/Chrony-Dashboard%20example.png)

---

## 🌟 Hauptfunktionen

- **📊 Echtzeit-KPI-Übersicht:** Anzeige von Stratum, System-Offset (µs), Referenzquelle (z. B. GPS PPS / Upstream NTP), Root Delay und Root Dispersion auf einen Blick.
- **📈 Historische Diagramme (Tab 1):** Interaktive Visualisierung von Uhrzeit-Offset (Microseconds) und Frequenz-Drift (PPM) über die Zeit mittels Chart.js.
- **👥 Client-Telemetrie & Search (Tab 2):** Übersicht aller verbundenen Geräte im Netzwerk, die Zeit vom Pi abfragen (inkl. IPv4/IPv6-Zuordnung, Paketanzahlen, Intervallraten und Filter-Funktion).
- **⚙️ Konfigurations-Management (Tab 3):** Einstellungen für Polling-Intervalle, Warnschwellen und Speicherdauer direkt über die Oberfläche anpassen und in einer SQLite-Datenbank sichern.
- **🌐 Upstream Sources (`chronyc sources`):** Live-Status aller konfigurierten NTP-Peer-Server und Referenz-Uhren.
- **🌙 Dark Mode & Responsive Design:** Modernes UI mit TailwindCSS und FontAwesome, optimiert für Desktop, Tablets und Smartphones.

---

## 📁 Projektstruktur

```text
ChronyPi-Dashboard/
├── app.py                  # Flask-Backend, SQLite-Datenbank & chronyc-Parser
├── chrony_history.db       # SQLite-Datenbank (wird automatisch erstellt)
├── templates/
│   └── index.html          # Frontend Single-Page Application (HTML/JS/Chart.js)
├── .gitignore              # Ignorierte Dateien (venv, db, caches)
└── README.md               # Projektdokumentation
```

---

## 🚀 Installation & Setup

### 1. System-Voraussetzungen
Stelle sicher, dass `chrony`, `python3` und `git` auf deinem Raspberry Pi installiert sind:

```bash
sudo apt update
sudo apt install -y chrony python3 python3-venv git
```

### 2. Repository klonen
Klone das Repository in das `/opt`-Verzeichnis und passe die Zugriffsrechte an:

```bash
cd /opt
sudo git clone https://github.com/ApfelBirneKreis/ChronyPi-Dashboard.git chrony-dashboard
sudo chown -R $USER:$USER /opt/chrony-dashboard
cd /opt/chrony-dashboard
```

### 3. Virtuelle Python-Umgebung einrichten
Erstelle eine virtuelle Umgebung und installiere die benötigten Abhängigkeiten:

```bash
python3 -m venv venv
source venv/bin/activate
pip install flask flask-cors
```

---

## ⚙️ Autostart als Systemd-Dienst

Damit das Dashboard dauerhaft im Hintergrund läuft und nach jedem Systemstart automatisch geladen wird:

### 1. Service-Datei erstellen
```bash
sudo nano /etc/systemd/system/chrony-dashboard.service
```

### 2. Konfiguration einfügen
```ini
[Unit]
Description=Chrony Master Dashboard Service
After=network.target chrony.service

[Service]
User=root
WorkingDirectory=/opt/chrony-dashboard
ExecStart=/opt/chrony-dashboard/venv/bin/python /opt/chrony-dashboard/app.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### 3. Dienst aktivieren und starten
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now chrony-dashboard.service
```

Das Dashboard ist nun in deinem Browser erreichbar unter:
`http://<DEINE-PI-IP>:8080`

---

## 🔄 Updates installieren

Um spätere Aktualisierungen einzuspielen, führe einfach folgende Befehle auf deinem Raspberry Pi aus:

```bash
cd /opt/chrony-dashboard
git pull origin main
sudo systemctl restart chrony-dashboard.service
```

---

## 🛠️ Verwendete Technologien

* **Backend:** Python 3, Flask, Flask-CORS, SQLite3
* **Frontend:** HTML5, JavaScript (ES6+), TailwindCSS (CDN), Chart.js, FontAwesome 6
* **System Metrics:** `chronyc tracking`, `chronyc sources`, `chronyc clients`

---

## 📜 Lizenz

Dieses Projekt steht unter der [MIT License](LICENSE).
