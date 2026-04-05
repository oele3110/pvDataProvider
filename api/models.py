from datetime import datetime

from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LiveDataPayload(BaseModel):
    timestamp: datetime
    # Flat sensor values from the collector.
    # Full device-grouped structure (inverter/smartmeter/wallbox/…) will be
    # added once InfluxDB integration is in place and derived fields are available.
    data: dict


class DeviceStatus(BaseModel):
    name: str
    available: bool
    last_seen: datetime | None = None


class StatusResponse(BaseModel):
    status: str
    uptime_s: float
    devices: list[DeviceStatus]
