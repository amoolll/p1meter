# Changelog

## [4.0.0] - 2026-07-03

### Major Changes
- **Architecture**: Moved all business logic (self-sufficiency %, cost calculations, date aggregations) from browser JavaScript to backend FastAPI endpoints
- **Frontend Split**: Refactored 2400-line monolithic `index.html` into modular files:
  - `static/dashboard.js` - card updates, date picker, UI state
  - `static/charts.js` - Chart.js rendering (presentation only)
  - `static/tariffs.js` - tariff settings panel
  - `static/backup.js` - backup/restore buttons
  - `static/state.js` - shared global state
  - `static/init.js` - page bootstrap
  - `static/style.css` - extracted styles

### New Backend Endpoints
- `GET /api/dashboard?date=YYYY-MM-DD` - Full view-model for cards + chart (replaces complex client-side calculations)
- `GET /api/dashboard/month?month=YYYY-MM` - Monthly projection card data
- `GET /api/live` - Real-time power reading (independent of selected date)

### Bug Fixes
- **Gas on past dates**: Previously always computed from today's data. Now correctly reads the selected date's actual gas_m3 delta
- **Chart tooltip date label**: Was hardcoded "Today" even when viewing past dates. Now shows actual date (Today/Yesterday/specific date)
- **Safari date parsing**: Fixed non-ISO date string `new Date('2000-01-01 ' + time)` that Safari's WebKit rejected. Now uses spec-compliant multi-arg constructor
- **Browser caching**: Added ETag and Cache-Control headers to prevent Safari/Chrome from serving stale HTML with old script paths after redeploy

### Dependencies
- Added `aiofiles==23.2.1` for serving static files

### Breaking Changes
None - all APIs are backward compatible. v3 backups restore cleanly on v4.

### Testing
- ✅ All /api/dashboard, /api/live, /api/dashboard/month endpoints verified with real telemetry data
- ✅ Date picker correctly displays different dates' actual aggregated data
- ✅ Cards sync with selected date (all 4 cards, not just total)
- ✅ Chrome/Brave/Safari all render correctly after cache clear
- ✅ Backup/restore continues to work unchanged
- ✅ Live power title updates independent of date selection

---

## [3.0.0] - 2026-06-XX
(Previous v3 release notes here if needed)
