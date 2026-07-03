# P1 Energy Monitor v4

A real-time energy monitoring dashboard for Dutch P1 smart meters with SolarEdge solar integration. **v4 features a backend-driven architecture** — all business logic runs server-side, the frontend is thin and modular.

## Features

- 📊 **Real-time power flow** - Live updates in browser tab title (🟢 Surplus or 🔴 Grid)
- 📈 **Interactive charts** - Power, gas, and solar data with configurable time ranges
- 🌱 **Solar integration** - SolarEdge API support for solar generation data
- ⚡ **Self-sufficiency tracking** - See what % of your home runs on your own solar
- 💰 **Cost tracking** - Automatic calculation based on configurable tariffs
- 📅 **Historical data** - View and compare any past date
- 💾 **Backup & restore** - One-click database backup/restore with schema migration support
- 🔒 **Secure** - All credentials via environment variables, no hardcoded secrets

## Quick Start

```bash
cp .env.example .env
# Edit .env with your P1 meter IP and SolarEdge credentials
docker compose up -d --build
# Access at http://localhost:4999
```

## Architecture (v4)

### Backend (FastAPI + PostgreSQL)
- `/api/dashboard?date=YYYY-MM-DD` — Full view-model for cards + chart (pre-computed)
- `/api/live` — Real-time power reading
- `/api/dashboard/month?month=YYYY-MM` — Monthly projection data
- `/api/tariff` — Tariff settings
- `/api/backup`, `/api/restore` — Database backup/restore

### Frontend (Modular JavaScript)
- `index.html` (262 lines — markup only)
- `static/dashboard.js` — Card updates, date picker, UI state
- `static/charts.js` — Chart rendering (presentation only)
- `static/tariffs.js` — Tariff settings
- `static/backup.js` — Backup/restore handlers
- `static/state.js` — Shared state
- `static/init.js` — Bootstrap
- `static/style.css` — Styles

## What's New in v4

- ✅ Business logic moved to backend (no client-side math)
- ✅ HTML reduced from 2,400 to 262 lines
- ✅ Static assets served separately with cache-busting
- ✅ Fixed gas usage on past dates (was always today's)
- ✅ Fixed chart tooltips (now show actual date)
- ✅ Fixed Safari date-parsing bugs
- ✅ Better browser cache handling with ETags

## API Examples

### GET /api/dashboard?date=2026-07-03
```json
{
  "daily": {
    "import_kwh": 1.44,
    "export_kwh": 9.13,
    "net_kwh": 7.69,
    "self_sufficiency_percent": 74.9
  }
}
```

### GET /api/live
```json
{
  "grid_power_w": -1389,
  "is_surplus": true,
  "title": "🟢 Surplus: 1389W"
}
```

## Troubleshooting

- **Cards show zeros**: Check `docker logs p1meter-v2` and verify P1_IP is correct
- **Safari shows old version**: Quit Safari completely, clear website data, reopen
- **P1 meter connection fails**: Verify `P1_IP` in `.env` matches your meter IP

## License

See LICENSE file

---

**v4.0.0** - Backend-driven architecture with modular frontend
