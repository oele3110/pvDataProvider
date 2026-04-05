import calendar
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from api.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


def _month_range(month_str: str) -> tuple[datetime, datetime]:
    """Parse 'YYYY-MM' and return (first_second_of_month, first_second_of_next_month)."""
    try:
        year, month = int(month_str[:4]), int(month_str[5:7])
    except (ValueError, IndexError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="month must be YYYY-MM")
    _, last_day = calendar.monthrange(year, month)
    start = datetime(year, month, 1, tzinfo=timezone.utc)
    # first second of next month = exclusive stop
    if month == 12:
        stop = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        stop = datetime(year, month + 1, 1, tzinfo=timezone.utc)
    return start, stop


def _year_range(year: int) -> tuple[datetime, datetime]:
    start = datetime(year, 1, 1, tzinfo=timezone.utc)
    stop = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    return start, stop


def _today_range() -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    stop = now
    return start, stop


@router.get("/history")
async def get_history(
    request: Request,
    range: str = Query(..., description="today | month | year"),
    device: str = Query("all", description="all | inverter | smartmeter | wallbox | battery | heater | consumers"),
    month: str | None = Query(None, description="YYYY-MM — required when range=month"),
    year: int | None = Query(None, description="YYYY — required when range=year"),
    _username: str = Depends(get_current_user),
) -> list[dict]:
    influx = request.app.state.collector.influx

    # Resolve time range and bucket
    if range == "today":
        start, stop = _today_range()
        bucket_key = "hourly"
    elif range == "month":
        if not month:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="month parameter required")
        start, stop = _month_range(month)
        bucket_key = "daily"
    elif range == "year":
        if not year:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="year parameter required")
        start, stop = _year_range(year)
        bucket_key = "daily"
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="range must be today, month, or year")

    sensors = influx.sensors_for_device(device)
    if sensors is not None and len(sensors) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown device '{device}'")

    results = await influx.query_range(bucket_key, start, stop, sensors)

    # Serialize: convert datetime → ISO string for JSON response
    return [
        {"time": r["time"].isoformat(), "sensor": r["sensor"], "value": r["value"]}
        for r in results
    ]
