import logging
import time

from fastapi import APIRouter, Depends

from api.auth import get_current_user
from api.models import DeviceStatus, StatusResponse

logger = logging.getLogger(__name__)

router = APIRouter()

_start_time = time.monotonic()


@router.get("/status", response_model=StatusResponse)
async def get_status(
    _username: str = Depends(get_current_user),
) -> StatusResponse:
    return StatusResponse(
        status="ok",
        uptime_s=round(time.monotonic() - _start_time, 1),
        devices=[
            DeviceStatus(name="modbus", available=True),
            DeviceStatus(name="heater_rod", available=True),
            DeviceStatus(name="mqtt", available=True),
            # TODO: derive actual availability from collector health checks
        ],
    )
