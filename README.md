# P1 Energy Monitor v3  Dashboard🔌⚡

Use it as always on Display at home to see Surplus and Grid Enerfy used

A real-time home energy monitoring dashboard with solar generation tracking, built with FastAPI and Chart.js.

![Status](https://img.shields.io/badge/status-active-brightgreen)
![Python](https://img.shields.io/badge/python-3.10+-blue)
![License](https://img.shields.io/badge/license-MIT-green)

<img width="2846" height="1382" alt="image" src="https://github.com/user-attachments/assets/3a3e36ea-a520-4f67-be1c-434bc3c50edf" />

Mobile Browser

<img width="225" height="427" alt="image" src="https://github.com/user-attachments/assets/aba8a2c4-d63a-42c8-b7cf-b092e91758b1" />

## ✨ Features

- **📊 Real-time Power Flow** - Live visualization of grid import, surplus export, and solar generation
- **☀️ Solar Integration** - SolarEdge API integration for accurate solar production data
- **📈 Historical Charts** - View energy patterns with multiple time ranges (1h, 6h, 12h, 24h, 7d)
- **💾 15-Second Data Recording** - High-frequency telemetry stored in PostgreSQL
- **💰 Cost Tracking** - Automatic cost calculations based on configurable tariff rates
- **🌓 Self-Sufficiency Metrics** - Track what percentage of your energy comes from solar
- **📱 Responsive UI** - Works on desktop, tablet, and mobile
- **🎨 Dark Mode** - Professional glassmorphism design
- **🔄 Date Navigation** - Review any day from the last 30 days

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│         HomeWizard P1 Smart Meter                        │
│         (192.168.60.124:18000)                          │
└──────────────────────┬──────────────────────────────────┘
                       │ /api/v1/data (every 15s)
┌──────────────────────▼──────────────────────────────────┐
│     FastAPI Backend (Python)                             │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ - P1 Meter Data Collection                          │ │
│  │ - SolarEdge API Integration                         │ │
│  │ - Energy Calculations                              │ │
│  │ - Database Operations                              │ │
│  └─────────────────────────────────────────────────────┘ │
└──────────────────────┬──────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
        ▼              ▼              ▼
   PostgreSQL   SolarEdge API   Frontend (HTML/JS)
   (p1db)       (Monitoring)    (Dashboard)
```

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- HomeWizard P1 Smart Meter (WiFi enabled)
- SolarEdge inverter with monitoring API access
- Basic knowledge of environment variables

### Installation (5 minutes)

1. **Clone the repository:**
```bash
git clone https://github.com/amoolll/p1meter-v3.git
cd p1meter-v3
```

2. **Create environment configuration:**
```bash
cp .env.example .env
```

3. **Fill in your configuration:**
```bash
nano .env
```

Required values:
- `P1_IP` - Your HomeWizard P1 meter's IP address
- `SOLAREDGE_SITE_ID` - Your SolarEdge site ID
- `SOLAREDGE_API_KEY` - Your SolarEdge API key

4. **Start the application:**
```bash
docker compose up -d
```

5. **Access the dashboard:**
```
http://localhost:4999
```

Done! The dashboard will start collecting data immediately.

## 🔧 Configuration

### Finding Your P1 Meter IP

1. Press the button on your HomeWizard P1 meter
2. Navigate to WiFi info
3. Note the displayed IP address (e.g., 192.168.xx.xx)

### Getting SolarEdge API Access ( you can have your own solar monitoring api )

1. Log in to https://monitoring.solaredge.com
2. Go to Account Settings → API Access
3. Copy your **API Key**
4. Find your **Site ID** from the dashboard URL or Account Settings

### Tariff Rates

Edit `.env` to set your local energy tariffs:
```
TARIFF_IMPORT=0.22      # €/kWh from grid
TARIFF_EXPORT=0.12      # €/kWh to grid
TARIFF_GAS=2.50         # €/m³ for gas
```

## 📊 Dashboard Features

### Top Card: Live Status
```
Grid: 1245 W ⬇  (or Surplus: 2365 W ⬆)
```
Shows real-time power flow with animated arrows.

### Chart Controls
- **Date Selector** - Review any date from last 30 days
- **Time Range** - 1h, 6h, 12h, 24h, or 7d
- **Interval** - Raw data or 5min/10min/1h averages

### Cards
- **Total Surplus/Grid** - Daily net energy + Self Sufficiency %
- **Solar Generated** - Today's solar + Yesterday's estimate
- **Gas Consumed** - Daily gas usage + Yesterday estimate
- **Monthly Aggregates** - Grid/Surplus/Solar/Gas totals with costs

### Charts
- **Power Flow** - Stacked area chart: Grid, Surplus, Solar
- **Gas Consumption** - Daily gas usage trend
- **Solar Production** - Daily solar generation trend

## 🗂️ Project Structure

```
p1meter-v3/
├── app/
│   ├── main.py                    # FastAPI application & P1 collection
│   ├── database.py                # SQLAlchemy configuration
│   ├── models.py                  # Database models (Telemetry)
│   └── api/
│       └── energy.py              # Energy calculation endpoints
├── index.html                     # Dashboard UI (Chart.js, vanilla JS)
├── Dockerfile                     # Container image definition
├── docker-compose.yaml            # Service orchestration
├── .env.example                   # Configuration template
├── .gitignore                     # Git exclusions (protects .env)
├── requirements.txt               # Python dependencies
└── README.md                      # This file
```

## 🔌 API Endpoints

### Daily Energy Data
```
GET /api/energy?date=2026-06-26
```

Response:
```json
{
  "date": "2026-06-26",
  "current": {
    "grid_power_w": 150,
    "solar_power_w": 2500
  },
  "daily": {
    "import_kwh": 12.50,
    "export_kwh": 8.75,
    "solar_kwh": 15.36,
    "self_sufficiency_percent": 47.2
  },
  "history": [
    {"timestamp": "2026-06-26T00:15:00", "grid_power_w": 0, "solar_power_w": 0, ...},
    ...
  ]
}
```

### Tariff Rates
```
GET /api/tariff
```

Returns current tariff rates in €/kWh.

## 🛡️ Security

### Sensitive Data Protection

✅ **What's protected:**
- `.env` file (environment variables) - listed in `.gitignore`
- API keys - never hardcoded
- Database credentials - stored in `.env` only
- IP addresses - in `.env.example` as placeholders only

✅ **Best practices implemented:**
- Environment variables loaded from `.env`
- `.env` excluded from git via `.gitignore`
- `.env.example` shows format without credentials
- Secrets never appear in logs or error messages


## 📈 Database

**PostgreSQL** stores:
- Telemetry data (15-second intervals)
- Daily aggregates
- Historical data retention: Configurable

### Sample Data

```
timestamp          | grid_power_w | solar_power_w | total_import | total_export
───────────────────┼──────────────┼───────────────┼──────────────┼─────────────
2026-06-26 00:00   | 150          | 0             | 0.00         | 0.00
2026-06-26 06:00   | 1200         | 0             | 4.50         | 0.00
2026-06-26 12:00   | -500         | 2800          | 4.50         | 3.75
2026-06-26 18:00   | 800          | 1500          | 8.25         | 6.25
2026-06-26 23:59   | 250          | 0             | 12.50        | 8.75
```

## 🚨 Troubleshooting

### P1 Meter Connection Error

```
ERROR:app.main:Collection error: ConnectionError
```

**Solution:**
1. Verify `P1_IP` in `.env` matches your meter
2. Check meter is on same network
3. Ping the meter: `ping 192.168.60.124`
4. View logs: `docker compose logs p1meter-v2`

### SolarEdge API Error

```
INFO:app.api.energy:[SOLAREDGE] Error fetching data: 401 Unauthorized
```

**Solution:**
1. Verify API key is correct in `.env`
2. Check site ID is correct
3. Verify API access is enabled in SolarEdge settings
4. Generate a new API key if needed

### Database Connection Error

```
FATAL: database "p1db" does not exist
```

**Solution:**
```bash
# Recreate database volume
docker compose down
docker volume rm p1meter-v3_p1-data
docker compose up -d
```

### Dashboard Shows No Data

1. Wait 30 seconds - data collection takes time
2. Check browser console for JavaScript errors (F12)
3. Verify API calls succeed: `curl http://localhost:4999/api/energy?date=2026-06-26`

## 📝 Development

### Local Development

```bash
# Start services
docker compose up -d

# Watch logs
docker compose logs -f p1meter-v2

# Make code changes
vim app/main.py

# Rebuild and restart
docker compose up -d --build

# View specific logs
docker compose logs p1meter-v2 | tail -50
```

### Database Access

```bash
# Connect to PostgreSQL
docker exec p1-postgres psql -U p1user -d p1db

# Run queries
SELECT COUNT(*) FROM telemetry;
SELECT DATE(timestamp), COUNT(*) FROM telemetry GROUP BY DATE(timestamp);
```

### Testing Changes

After modifying code:

```bash
# Rebuild the container
docker compose up -d --build

# Check if app started correctly
docker compose logs p1meter-v2 | grep -i "error\|startup"

# Test API
curl http://localhost:4999/api/energy?date=2026-06-26
```

## 🤝 Contributing

Contributions are welcome! 

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

## 📄 License

MIT License - See LICENSE file for details

## 🙋 Support & Issues

Found a bug? Have a question?

1. Check [existing issues](https://github.com/YOUR_USERNAME/p1meter-v3/issues)
2. Create a [new issue](https://github.com/YOUR_USERNAME/p1meter-v3/issues/new) with:
   - Clear description
   - Steps to reproduce
   - Expected vs actual behavior
   - Relevant logs (sanitized of secrets)

## 📚 Resources

- [HomeWizard P1 Meter Documentation](https://homewizard.readthedocs.io/en/latest/)
- [SolarEdge Monitoring API](https://www.solaredge.com/sites/default/files/se_monitoring_api.pdf)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Chart.js Documentation](https://www.chartjs.org/docs/latest/)

## 🎯 Roadmap

- [ ] Real-time notifications for high usage
- [ ] Energy export to Home Assistant
- [ ] Machine learning for consumption prediction
- [ ] Battery storage integration
- [ ] Mobile app
- [ ] Advanced analytics and reporting

## ⭐ Acknowledgments

- HomeWizard for the excellent P1 meter
- SolarEdge for the comprehensive monitoring API
- FastAPI and Chart.js communities

---

**Happy monitoring! 🌞⚡**
