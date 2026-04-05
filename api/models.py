from datetime import datetime

from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class InverterData(BaseModel):
    power_ac_w: float | None = None
    power_dc_w: float | None = None
    home_consumption_from_pv_w: float | None = None


class SmartmeterData(BaseModel):
    grid_power_w: float | None = None       # positive = feed-in, negative = consume
    home_consumption_w: float | None = None
    home_consumption_from_grid_w: float | None = None
    home_consumption_from_battery_w: float | None = None


class WallboxData(BaseModel):
    power_w: float | None = None
    power_pv_w: float | None = None
    power_battery_w: float | None = None
    power_grid_w: float | None = None
    session_energy_wh: float | None = None
    session_duration_min: float | None = None
    active_charge_mode: int | None = None


class BatteryData(BaseModel):
    power_w: float | None = None            # positive = charging, negative = discharging
    state_of_charge_pct: float | None = None


class HeaterData(BaseModel):
    power_w: float | None = None
    temp1_c: float | None = None
    temp2_c: float | None = None


class CalculatedData(BaseModel):
    self_consumption_w: float | None = None
    self_consumption_rate_pct: float | None = None
    autarky_rate_pct: float | None = None


class LiveDataPayload(BaseModel):
    timestamp: datetime
    inverter: InverterData
    smartmeter: SmartmeterData
    wallbox: WallboxData
    battery: BatteryData
    heater: HeaterData
    consumers: dict[str, float | None]      # sensor key → power in W
    calculated: CalculatedData


class DeviceStatus(BaseModel):
    name: str
    available: bool
    last_seen: datetime | None = None


class StatusResponse(BaseModel):
    status: str
    uptime_s: float
    devices: list[DeviceStatus]
