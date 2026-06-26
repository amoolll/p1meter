from sqlalchemy import Column, Integer, Float, DateTime
from app.database import Base

class Telemetry(Base):
    __tablename__ = "telemetry"
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, index=True)
    grid_power_w = Column(Float, default=0)
    gas_m3 = Column(Float, default=0)
    total_import_kwh = Column(Float, default=0)
    total_export_kwh = Column(Float, default=0)
    solar_power_w = Column(Float, default=0)

class TariffSettings(Base):
    __tablename__ = "tariff_settings"
    
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, index=True)
    import_rate = Column(Float, default=0.25)
    export_rate = Column(Float, default=0.11)
    gas_rate = Column(Float, default=1.35)
