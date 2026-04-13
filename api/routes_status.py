import logging
import time

from fastapi import APIRouter, Depends, Request

from api.auth import get_current_user
from api.models import DeviceStatus, StatusResponse

logger = logging.getLogger(__name__)

router = APIRouter()

_start_time = time.monotonic()


@router.get("/status", response_model=StatusResponse)
async def get_status(
    request: Request,
    _username: str = Depends(get_current_user),
) -> StatusResponse:
    collector = request.app.state.collector
    influxdb_available = await collector.influx.ping()
    devices = [
        DeviceStatus(
            name=name,
            available=ts is not None,
            last_seen=ts,
        )
        for name, ts in collector.last_seen.items()
    ]
    return StatusResponse(
        status="ok",
        uptime_s=round(time.monotonic() - _start_time, 1),
        influxdb_available=influxdb_available,
        devices=devices,
    )
