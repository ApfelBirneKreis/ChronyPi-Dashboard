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
