from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Telemetry, TariffSettings
from datetime import datetime, timedelta, time
from typing import Optional
import logging
import httpx
from os import getenv

logger = logging.getLogger(__name__)

SOLAREDGE_SITE_ID = getenv("SOLAREDGE_SITE_ID", "202106")
SOLAREDGE_API_KEY = getenv("SOLAREDGE_API_KEY", "")
SOLAREDGE_DAILY_API = "https://monitoringapi.solaredge.com/site/{}/energyDetails.json"

async def get_solar_daily_kwh(date_str):
    """Get daily solar energy from SolarEdge API (e.g., '2026-06-20')"""
    if not SOLAREDGE_API_KEY:
        logger.warning("[SOLAREDGE-DAILY] No API key configured")
        return 0
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            url = SOLAREDGE_DAILY_API.format(SOLAREDGE_SITE_ID)
            # SolarEdge requires startTime and endTime in ISO format with timezone
            # Format: 2026-06-20 00:00:00 to 2026-06-20 23:59:59
            params = {
                "api_key": SOLAREDGE_API_KEY,
                "startTime": f"{date_str} 00:00:00",
                "endTime": f"{date_str} 23:59:59",
                "timeUnit": "DAY"
            }
            logger.info(f"[SOLAREDGE-DAILY] Fetching {url} for {date_str}")
            response = await client.get(url, params=params)
            logger.info(f"[SOLAREDGE-DAILY] Response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"[SOLAREDGE-DAILY] Response keys: {data.keys()}")
                
                # Find Production meter
                meters = data.get("energyDetails", {}).get("meters", [])
                logger.info(f"[SOLAREDGE-DAILY] Found {len(meters)} meters")
                
                for i, meter in enumerate(meters):
                    meter_type = meter.get("type")
                    logger.info(f"[SOLAREDGE-DAILY] Meter {i}: type={meter_type}")
                    
                    if meter_type == "Production":
                        values = meter.get("values", [])
                        logger.info(f"[SOLAREDGE-DAILY] Production meter has {len(values)} values")
                        
                        if values and len(values) > 0:
                            wh = values[0].get("value")
                            logger.info(f"[SOLAREDGE-DAILY] Value (Wh): {wh}")
                            if wh:
                                kwh = float(wh) / 1000.0
                                logger.info(f"[SOLAREDGE-DAILY] {date_str}: {kwh} kWh ✓")
                                return kwh
                
                logger.warning(f"[SOLAREDGE-DAILY] No Production meter found in response")
            else:
                logger.error(f"[SOLAREDGE-DAILY] API returned {response.status_code}: {response.text}")
    except Exception as e:
        logger.error(f"[SOLAREDGE-DAILY] Error: {e}")
    
    logger.warning(f"[SOLAREDGE-DAILY] Returning 0 for {date_str}")
    return 0

router = APIRouter(prefix="/api", tags=["energy"])

@router.get("/energy")
async def get_energy(date: Optional[str] = Query(None), db: Session = Depends(get_db)):
    if date:
        target_date = datetime.strptime(date, "%Y-%m-%d").date()
        start = datetime.combine(target_date, datetime.min.time())
        end = datetime.combine(target_date, datetime.max.time())
    else:
        # Use current local time, not UTC
        end = datetime.now()
        start = end - timedelta(hours=24)
    
    data = db.query(Telemetry).filter(Telemetry.timestamp >= start, Telemetry.timestamp <= end).order_by(Telemetry.timestamp).all()
    
    if not data:
        return {"history": [], "daily": {"import_kwh": 0, "export_kwh": 0, "gas_m3": 0, "solar_kwh": 0, "self_sufficiency_percent": 0}, "current": {"grid_power_w": 0, "solar_power_w": 0}}
    
    history = [{"time": t.timestamp.strftime("%H:%M"), "import_w": t.grid_power_w if t.grid_power_w > 0 else 0, "export_w": abs(t.grid_power_w) if t.grid_power_w < 0 else 0, "gas_m3": t.gas_m3, "solar_w": t.solar_power_w} for t in data]
    
    first, last = data[0], data[-1]
    import_kwh = max(0, last.total_import_kwh - first.total_import_kwh)
    export_kwh = max(0, last.total_export_kwh - first.total_export_kwh)
    
    # Get solar energy from SolarEdge daily API (more accurate than 15-sec samples)
    solar_kwh = 0
    if date:
        solar_kwh = await get_solar_daily_kwh(date)
    else:
        # For rolling 24h, still use calculated value from samples
        solar_kwh = 0
        solar_count = 0
        if data:
            for i in range(len(data)):
                solar_kw = data[i].solar_power_w or 0
                if solar_kw > 0:
                    solar_count += 1
                    solar_kwh += solar_kw * (15.0 / 3600.0)
    
    today_start = datetime.combine(datetime.now().date(), time.min)
    today_data = db.query(Telemetry).filter(Telemetry.timestamp >= today_start, Telemetry.timestamp <= datetime.now()).order_by(Telemetry.timestamp).all()
    
    gas_m3 = 0
    if today_data and len(today_data) > 1:
        first_non_zero = next((r for r in today_data if r.gas_m3 > 0), None)
        if first_non_zero:
            gas_m3 = max(0, today_data[-1].gas_m3 - first_non_zero.gas_m3)
    
    # Calculate self sufficiency: (solar - export) / (solar - export + import)
    # self_consumed = solar - export (solar used at home)
    # total_consumption = self_consumed + import
    self_consumed = max(0, solar_kwh - export_kwh)
    total_consumption = self_consumed + import_kwh
    self_sufficiency = (self_consumed / total_consumption * 100) if total_consumption > 0 else 0
    
    return {"history": history, "daily": {"import_kwh": round(import_kwh, 2), "export_kwh": round(export_kwh, 2), "gas_m3": round(gas_m3, 3), "solar_kwh": round(solar_kwh, 2), "self_sufficiency_percent": round(self_sufficiency, 1)}, "current": {"grid_power_w": last.grid_power_w, "solar_power_w": last.solar_power_w}}

@router.get("/tariff")
async def get_tariff(db: Session = Depends(get_db)):
    """Get the current tariff settings"""
    latest = db.query(TariffSettings).order_by(TariffSettings.created_at.desc()).first()
    if latest:
        return {"import_rate": latest.import_rate, "export_rate": latest.export_rate, "gas_rate": latest.gas_rate}
    return {"import_rate": 0.25, "export_rate": 0.11, "gas_rate": 1.35}

@router.post("/tariff")
async def save_tariff(import_rate: float, export_rate: float, gas_rate: float, db: Session = Depends(get_db)):
    """Save new tariff settings"""
    tariff = TariffSettings(
        created_at=datetime.utcnow(),
        import_rate=import_rate,
        export_rate=export_rate,
        gas_rate=gas_rate
    )
    db.add(tariff)
    db.commit()
    return {"status": "ok", "import_rate": import_rate, "export_rate": export_rate, "gas_rate": gas_rate}

@router.get("/health")
async def health():
    return {"status": "ok"}
