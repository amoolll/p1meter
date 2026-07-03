"""
Dashboard view-model endpoint.

This module exists to move business logic (self-sufficiency %, net kWh,
monthly cost projections, "yesterday" comparisons) OUT of the frontend
JavaScript and into the backend, so there is exactly one place each number
is calculated. The frontend should only format these values for display
(e.g. toFixed(), adding units) — it should not derive them.

/api/dashboard?date=YYYY-MM-DD  -> full view-model for the 4 cards + chart
                                    for a specific date (defaults to today)
/api/live                       -> real-time power reading, independent of
                                    whatever date is selected in the UI
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, date as date_cls
from typing import Optional
import calendar
import logging

from app.database import get_db
from app.models import Telemetry, TariffSettings
from app.api.energy import get_solar_daily_kwh

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["dashboard"])


def _aggregate_day(db: Session, target_date: date_cls) -> dict:
    """
    Aggregate raw telemetry rows for a single calendar day into:
    - a chart-ready history list
    - daily totals (import/export/gas), derived the same way for ANY date

    NOTE: this fixes a bug in the original /api/energy endpoint where gas_m3
    was always computed from *today's* rows regardless of which date was
    requested. Here gas is computed from the same day's data as everything
    else, so viewing a past date shows that day's actual gas usage.
    """
    start = datetime.combine(target_date, datetime.min.time())
    end = datetime.combine(target_date, datetime.max.time())

    rows = (
        db.query(Telemetry)
        .filter(Telemetry.timestamp >= start, Telemetry.timestamp <= end)
        .order_by(Telemetry.timestamp)
        .all()
    )

    if not rows:
        return {
            "has_data": False,
            "history": [],
            "import_kwh": 0.0,
            "export_kwh": 0.0,
            "gas_m3": 0.0,
            "grid_power_w": 0,
            "solar_power_w": 0,
        }

    history = [
        {
            "time": r.timestamp.strftime("%H:%M"),
            "import_w": r.grid_power_w if r.grid_power_w > 0 else 0,
            "export_w": abs(r.grid_power_w) if r.grid_power_w < 0 else 0,
            "gas_m3": r.gas_m3,
            "solar_w": r.solar_power_w,
        }
        for r in rows
    ]

    first, last = rows[0], rows[-1]
    import_kwh = max(0.0, last.total_import_kwh - first.total_import_kwh)
    export_kwh = max(0.0, last.total_export_kwh - first.total_export_kwh)

    gas_first = next((r for r in rows if r.gas_m3 > 0), None)
    gas_m3 = max(0.0, last.gas_m3 - gas_first.gas_m3) if gas_first else 0.0

    return {
        "has_data": True,
        "history": history,
        "import_kwh": import_kwh,
        "export_kwh": export_kwh,
        "gas_m3": gas_m3,
        "grid_power_w": last.grid_power_w,
        "solar_power_w": last.solar_power_w,
    }


def _get_tariff_rates(db: Session) -> dict:
    latest = db.query(TariffSettings).order_by(TariffSettings.created_at.desc()).first()
    if latest:
        return {
            "import_rate": latest.import_rate,
            "export_rate": latest.export_rate,
            "gas_rate": latest.gas_rate,
        }
    return {"import_rate": 0.25, "export_rate": 0.11, "gas_rate": 1.35}


@router.get("/dashboard")
async def get_dashboard(date: Optional[str] = Query(None), db: Session = Depends(get_db)):
    today = datetime.now().date()
    target_date = datetime.strptime(date, "%Y-%m-%d").date() if date else today
    is_today = target_date == today

    agg = _aggregate_day(db, target_date)
    import_kwh = agg["import_kwh"]
    export_kwh = agg["export_kwh"]
    gas_m3 = agg["gas_m3"]

    solar_kwh = await get_solar_daily_kwh(target_date.isoformat())

    # --- Net kWh / total card ---
    net_kwh = export_kwh - import_kwh
    net_is_surplus = net_kwh >= 0

    # --- Self sufficiency ---
    self_consumed = max(0.0, solar_kwh - export_kwh)
    total_consumption = self_consumed + import_kwh
    self_sufficiency = (self_consumed / total_consumption * 100) if total_consumption > 0 else 0.0
    self_sufficiency = min(self_sufficiency, 100.0)
    if self_sufficiency < 50:
        suff_band = "low"
    elif self_sufficiency < 75:
        suff_band = "medium"
    else:
        suff_band = "high"

    # --- Yesterday: REAL historical data, not an estimate ---
    yesterday_date = target_date - timedelta(days=1)
    y_agg = _aggregate_day(db, yesterday_date)
    y_solar_kwh = await get_solar_daily_kwh(yesterday_date.isoformat()) if y_agg["has_data"] else 0.0

    # --- Tariffs & costs ---
    rates = _get_tariff_rates(db)
    import_cost = import_kwh * rates["import_rate"]
    export_cost = export_kwh * rates["export_rate"]
    gas_cost = gas_m3 * rates["gas_rate"]

    # --- Monthly projection, based on the viewed date's month ---
    days_in_month = calendar.monthrange(target_date.year, target_date.month)[1]
    m_grid_kwh = import_kwh * days_in_month
    m_surplus_kwh = export_kwh * days_in_month
    m_gas_m3 = gas_m3 * days_in_month
    # Same rough estimate the frontend used previously (total generation ~1.5x net throughput)
    m_solar_kwh = (import_kwh + export_kwh) * days_in_month * 1.5

    return {
        "date": target_date.isoformat(),
        "is_today": is_today,
        "history": agg["history"],
        "daily": {
            "import_kwh": round(import_kwh, 2),
            "export_kwh": round(export_kwh, 2),
            "gas_m3": round(gas_m3, 3),
            "solar_kwh": round(solar_kwh, 2),
            "net_kwh": round(net_kwh, 2),
            "net_is_surplus": net_is_surplus,
            "total_label": "Total Surplus" if net_is_surplus else "Total Grid",
            "total_css_class": "surplus" if net_is_surplus else "grid",
            "self_sufficiency_percent": round(self_sufficiency, 1),
            "self_sufficiency_band": suff_band,
        },
        "yesterday": {
            "solar_kwh": round(y_solar_kwh, 2),
            "gas_m3": round(y_agg["gas_m3"], 3),
        },
        "tariff": rates,
        "costs": {
            "import_cost": round(import_cost, 2),
            "export_cost": round(export_cost, 2),
            "gas_cost": round(gas_cost, 2),
        },
        "monthly_projection": {
            "days_in_month": days_in_month,
            "grid_kwh": round(m_grid_kwh, 2),
            "grid_cost": round(m_grid_kwh * rates["import_rate"], 2),
            "surplus_kwh": round(m_surplus_kwh, 2),
            "surplus_cost": round(m_surplus_kwh * rates["export_rate"], 2),
            "solar_kwh": round(m_solar_kwh, 2),
            "gas_m3": round(m_gas_m3, 3),
            "gas_cost": round(m_gas_m3 * rates["gas_rate"], 2),
        },
    }


@router.get("/dashboard/month")
async def get_dashboard_month(month: str = Query(..., description="YYYY-MM"), db: Session = Depends(get_db)):
    """
    Monthly summary card data. Kept separate from /api/dashboard since it
    represents a different UI section (the monthly projection panel) with
    its own selector, independent of the daily date picker.
    """
    year_str, month_str = month.split("-")
    year, month_num = int(year_str), int(month_str)
    days_in_month = calendar.monthrange(year, month_num)[1]
    first_of_month = date_cls(year, month_num, 1)

    agg = _aggregate_day(db, first_of_month)
    solar_kwh = await get_solar_daily_kwh(first_of_month.isoformat())

    total_solar = solar_kwh * days_in_month
    total_import = agg["import_kwh"] * days_in_month
    total_export = agg["export_kwh"] * days_in_month
    total_gas = agg["gas_m3"] * days_in_month

    m_self_consumed = max(0.0, total_solar - total_export)
    m_total_consumption = m_self_consumed + total_import
    m_self_sufficiency = (m_self_consumed / m_total_consumption * 100) if m_total_consumption > 0 else 0.0
    m_self_sufficiency = min(m_self_sufficiency, 100.0)
    if m_self_sufficiency < 50:
        suff_band = "low"
    elif m_self_sufficiency < 75:
        suff_band = "medium"
    else:
        suff_band = "high"

    rates = _get_tariff_rates(db)
    m_solar_est = (agg["import_kwh"] + agg["export_kwh"]) * days_in_month * 1.5

    return {
        "month": month,
        "days_in_month": days_in_month,
        "self_sufficiency_percent": round(m_self_sufficiency, 1),
        "self_sufficiency_band": suff_band,
        "grid_kwh": round(total_import, 2),
        "grid_cost": round(total_import * rates["import_rate"], 2),
        "surplus_kwh": round(total_export, 2),
        "surplus_cost": round(total_export * rates["export_rate"], 2),
        "solar_kwh": round(m_solar_est, 2),
        "gas_m3": round(total_gas, 3),
        "gas_cost": round(total_gas * rates["gas_rate"], 2),
    }


@router.get("/live")
async def get_live(db: Session = Depends(get_db)):
    """
    Real-time power reading, independent of whatever date is selected in
    the dashboard. Polled every ~10s by the frontend to keep the browser
    tab title and header status live, regardless of which historical date
    the user is currently viewing.
    """
    last = db.query(Telemetry).order_by(Telemetry.timestamp.desc()).first()
    grid_power_w = last.grid_power_w if last else 0
    solar_power_w = last.solar_power_w if last else 0
    is_surplus = grid_power_w <= 0
    abs_w = abs(grid_power_w)

    return {
        "grid_power_w": grid_power_w,
        "solar_power_w": solar_power_w,
        "is_surplus": is_surplus,
        "abs_power_w": abs_w,
        "title": f"🟢 Surplus: {abs_w:.0f}W" if is_surplus else f"🔴 Grid: {grid_power_w:.0f}W",
        "status_label": f"Surplus: {abs_w:.0f} W" if is_surplus else f"Grid: {grid_power_w:.0f} W",
    }
