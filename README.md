🕒 ChronyPi Dashboard
A modern, lightweight web dashboard for the Chrony NTP server running on a Raspberry Pi. It combines high-precision system tracking and historical metrics with detailed telemetry, client monitoring, SoC temperature tracking, and a centralized settings management interface into a sleek single-page application.
📸 Dashboard Preview
🌟 Key Features
📊 Real-Time KPI Overview: Live display of Stratum level, system offset (ns/µs), reference source (e.g., GPS PPS / Upstream NTP), root delay, root dispersion, and active client count at a glance.
🌡️ Raspberry Pi SoC Temperature Monitoring: Tracks processor thermal metrics to help correlate thermal fluctuations with crystal oscillator frequency drift.
📈 Historical Tracking & Charts (Tab 1): Interactive Chart.js visualization of clock offset and frequency drift (PPM), complete with 24h and 72h min/max historical statistical analysis cards.
📊 System Telemetry & Advanced Metrics (Tab 2): Dedicated graphs for Raspberry Pi SoC temperature over time, as well as advanced timing metrics including Skew (ppm) and Residual Frequency (ppm).
👥 Client Monitoring (Tab 3): Overview of all connected network devices querying time from the Pi (including NTP packet counts, drop packets, polling intervals, and last-seen metrics).
⚙️ Settings & Administration (Tab 4): Adjust polling intervals, warning thresholds, toggle invalid source filters, export historical data as CSV, and reset the SQLite database directly from the UI.
🌐 Upstream Sources (`chronyc sources`): Live status of all configured NTP peer servers and reference clocks with dynamic validation and status badges.
🌙 Dark Mode & Responsive Design: Modern UI built with TailwindCSS, FontAwesome, and fail-safe inline SVG branding, optimized for desktops, tablets, and mobile devices.
📁 Project Structure
```
ChronyPi-Dashboard/
├── app.py                  # Flask backend, SQLite database & chronyc/telemetry parser
├── chrony_history.db       # SQLite historical database (auto-created)
├── templates/
│   └── index.html          # Frontend Single-Page Application (HTML/JS/Chart.js)
├── .gitignore              # Ignored files (venv, db, caches)
└── README.md               # Project documentation

```
🚀 Installation & Setup
1. System Requirements
Ensure that `chrony`, `python3`, and `git` are installed on your Raspberry Pi:
```
sudo apt update
sudo apt install -y chrony python3 python3-venv git

```
2. Clone the Repository
Clone the repository into the `/opt` directory and configure ownership permissions:
```
cd /opt
sudo git clone https://github.com/ApfelBirneKreis/ChronyPi-Dashboard.git chrony-dashboard
sudo chown -R $USER:$USER /opt/chrony-dashboard
cd /opt/chrony-dashboard

```
3. Setup Python Virtual Environment
Create a virtual environment and install the required Python packages:
```
python3 -m venv venv
source venv/bin/activate
pip install flask flask-cors

```
⚙️ Autostart as a Systemd Service
To ensure the dashboard runs continuously in the background and starts automatically on boot:
1. Create the Service File
```
sudo nano /etc/systemd/system/chrony-dashboard.service

```
2. Insert Configuration
```
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
3. Enable and Start the Service
```
sudo systemctl daemon-reload
sudo systemctl enable --now chrony-dashboard.service

```
The dashboard is now accessible in your browser at:
`http://<YOUR-PI-IP>:8080`
🔄 Updating
To pull future updates and restart the service, run the following commands on your Raspberry Pi:
```
cd /opt/chrony-dashboard
git pull origin main
sudo systemctl restart chrony-dashboard.service

```
🛠️ Technologies Used
Backend: Python 3, Flask, Flask-CORS, SQLite3, Linux Thermal Zones / `vcgencmd`
Frontend: HTML5, JavaScript (ES6+), TailwindCSS (CDN), Chart.js, FontAwesome, Inline SVG
System Metrics: `chronyc tracking`, `chronyc sources`, `chronyc clients`
📜 License
This project is open source under the MIT License.
