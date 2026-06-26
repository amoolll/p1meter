from fastapi import FastAPI
from fastapi.responses import FileResponse
import asyncio
import httpx
from app.database import init_db, SessionLocal
from app.models import Telemetry
from app.api.energy import router as energy_router
from app.api.backup_restore import router as backup_router
from os import getenv
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="P1 Energy Monitor v3")
app.include_router(energy_router)
app.include_router(backup_router)

P1_IP = getenv("P1_IP", "")
P1_API = f"http://{P1_IP}/api/v1/data" if P1_IP else ""
SOLAREDGE_SITE_ID = getenv("SOLAREDGE_SITE_ID", "")
SOLAREDGE_API_KEY = getenv("SOLAREDGE_API_KEY", "")
SOLAREDGE_API = "https://monitoringapi.solaredge.com/site/{}/currentPowerFlow.json"
SOLAREDGE_DAILY_API = "https://monitoringapi.solaredge.com/site/{}/energyDetails.json"

@app.on_event("startup")
async def startup():
    init_db()
    logger.info("Database initialized")
    if SOLAREDGE_API_KEY:
        logger.info(f"SolarEdge integration enabled for site {SOLAREDGE_SITE_ID}")
    else:
        logger.warning("SolarEdge API key not set - solar data will be 0")
    asyncio.create_task(collect_data())

async def get_solar_power():
    """Get current solar power from SolarEdge API"""
    if not SOLAREDGE_API_KEY:
        return 0
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            url = SOLAREDGE_API.format(SOLAREDGE_SITE_ID)
            params = {"api_key": SOLAREDGE_API_KEY}
            response = await client.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                solar_w = data.get("siteCurrentPowerFlow", {}).get("PV", {}).get("currentPower", 0)
                return float(solar_w)
    except Exception as e:
        logger.warning(f"SolarEdge API error: {e}")
    return 0

async def get_solar_daily_energy(date_str):
    """Get daily solar energy from SolarEdge API (e.g., '2026-06-20')"""
    if not SOLAREDGE_API_KEY:
        return 0
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            url = SOLAREDGE_DAILY_API.format(SOLAREDGE_SITE_ID)
            # SolarEdge energyDetails endpoint requires startDate and endDate
            params = {
                "api_key": SOLAREDGE_API_KEY,
                "startDate": date_str,
                "endDate": date_str,
                "timeUnit": "DAY"
            }
            response = await client.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                # Response structure: energyDetails.meters[0].values[0].value (in Wh)
                values = data.get("energyDetails", {}).get("meters", [])
                if values and len(values) > 0:
                    # Find PV (production) meter
                    for meter in values:
                        if meter.get("type") == "Production":
                            meter_values = meter.get("values", [])
                            if meter_values and len(meter_values) > 0:
                                wh = meter_values[0].get("value", 0)
                                if wh:
                                    kwh = float(wh) / 1000.0
                                    logger.info(f"[SOLAREDGE-DAILY] {date_str}: {kwh} kWh")
                                    return kwh
    except Exception as e:
        logger.warning(f"SolarEdge daily energy error: {e}")
    return 0

async def collect_data():
    """Collect P1 meter data every 15 seconds (local API call) and SolarEdge every 60 seconds"""
    solar_counter = 0
    last_solar_w = 0  # Cache solar reading between API calls
    while True:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(P1_API)
                if response.status_code == 200:
                    p1_data = response.json()
                    
                    # Get solar data every 4 cycles (15s * 4 = 60s)
                    # Cache it between API calls to avoid losing data
                    if solar_counter % 4 == 0:
                        last_solar_w = await get_solar_power()
                    
                    db = SessionLocal()
                    telemetry = Telemetry(
                        timestamp=datetime.now(),
                        grid_power_w=p1_data.get("active_power_w", 0),
                        gas_m3=p1_data.get("total_gas_m3", 0),
                        total_import_kwh=p1_data.get("total_power_import_kwh", 0),
                        total_export_kwh=p1_data.get("total_power_export_kwh", 0),
                        solar_power_w=last_solar_w  # Use cached solar value
                    )
                    db.add(telemetry)
                    db.commit()
                    db.close()
                    
                    solar_counter += 1
        except Exception as e:
            logger.error(f"Collection error: {type(e).__name__}: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        await asyncio.sleep(15)

@app.get("/")
async def root():
    return FileResponse("index.html")
