import logging
import os
from datetime import datetime, timezone

from influxdb_client import Point
from influxdb_client.client.influxdb_client_async import InfluxDBClientAsync

logger = logging.getLogger(__name__)

_MEASUREMENT = "energy"

# Maps logical device names (used in /api/history?device=X) to sensor keys
# stored in InfluxDB. "all" is handled separately.
DEVICE_SENSORS: dict[str, list[str]] = {
    "inverter": [
        "sum_output_inverter_ac",
        "sum_pv_power_inverter_dc",
        "home_consumption_from_pv",
    ],
    "smartmeter": [
        "grid_power_total",
        "home_consumption",
        "home_consumption_from_grid",
        "home_consumption_from_battery",
    ],
    "wallbox": [
        "sum_wallbox_charge_power_total",
        "active_power_charging",
        "current_session_energy",
        "current_session_duration",
    ],
    "battery": [
        "sum_battery_charge_discharge_dc",
        "system_state_of_charge",
    ],
    "heater": ["power_elwa2", "temp1", "temp2"],
    "consumers": [
        "knx/Leistung_Backofen",
        "knx/Leistung_Badheizkoerper_oben",
        "knx/Leistung_Badheizkoerper_unten",
        "knx/Leistung_Geschirrspueler",
        "knx/Leistung_KWL",
        "knx/Leistung_Kuehlschrank",
        "knx/Leistung_Kuehlschrank_HWR",
        "knx/Leistung_TV",
        "knx/Leistung_TV_Zubehoer",
        "knx/Leistung_Trockner",
        "knx/Leistung_Waschmaschine",
        "knx/Leistung_Wasserenthaertung",
        "knx/Warmwasser_Temperatur",
    ],
}


class InfluxClient:
    def __init__(self, influx_cfg: dict) -> None:
        self._url: str = influx_cfg["url"]
        self._org: str = influx_cfg["org"]
        self._buckets: dict = influx_cfg["buckets"]
        self._token: str = os.environ.get("PV_INFLUX_TOKEN", "")
        if not self._token:
            logger.warning(
                "PV_INFLUX_TOKEN is not set — InfluxDB writes will fail. "
                "Set the environment variable before starting."
            )
        self._client: InfluxDBClientAsync | None = None

    async def start(self) -> None:
        self._client = InfluxDBClientAsync(
            url=self._url, token=self._token, org=self._org
        )
        logger.info("InfluxClient connected to %s (org=%s)", self._url, self._org)

    async def stop(self) -> None:
        if self._client:
            await self._client.close()
            logger.info("InfluxClient closed")

    async def ping(self) -> bool:
        """Return True if InfluxDB is reachable."""
        if not self._client:
            return False
        try:
            return await self._client.ping()
        except Exception:
            return False

    async def write_raw(self, data: dict, timestamp: datetime | None = None) -> None:
        """Write all sensor values from *data* as a batch to the raw bucket."""
        if not self._client:
            return
        ts = timestamp or datetime.now(timezone.utc)
        points = [
            Point(_MEASUREMENT)
            .tag("sensor", name)
            .field("value", float(value))
            .time(ts)
            for name, value in data.items()
            if value is not None
        ]
        if not points:
            return
        try:
            write_api = self._client.write_api()
            await write_api.write(bucket=self._buckets["raw"], record=points)
        except Exception:
            logger.exception("InfluxDB write failed")

    async def query_range(
        self,
        bucket_key: str,
        start: datetime,
        stop: datetime,
        sensors: list[str] | None = None,
        field: str = "energy_wh",
    ) -> list[dict]:
        """
        Return a list of {'time': datetime, 'sensor': str, 'field': str, 'value': float}.

        *sensors*    — if None, all sensors are returned.
        *bucket_key* — one of 'raw', 'hourly', 'daily'.
        *field*      — which aggregated field to return: 'energy_wh', 'mean_w', 'min_w', 'max_w',
                       'daily_kwh'. Ignored for the 'raw' bucket (only '_value' exists there).
        """
        if not self._client:
            return []

        bucket = self._buckets[bucket_key]
        sensor_filter = _build_sensor_filter(sensors)
        field_filter = "" if bucket_key == "raw" else f'|> filter(fn: (r) => r._field == "{field}")'

        flux = f"""
from(bucket: "{bucket}")
  |> range(start: {_flux_time(start)}, stop: {_flux_time(stop)})
  |> filter(fn: (r) => r._measurement == "{_MEASUREMENT}")
  {sensor_filter}
  {field_filter}
  |> keep(columns: ["_time", "sensor", "_field", "_value"])
"""
        return await self._run_query(flux)

    async def query_derived(self, start: datetime, stop: datetime) -> list[dict]:
        """Return daily derived metrics (Eigenverbrauchsquote, Autarkiegrad) from the daily bucket."""
        if not self._client:
            return []

        bucket = self._buckets["daily"]
        flux = f"""
from(bucket: "{bucket}")
  |> range(start: {_flux_time(start)}, stop: {_flux_time(stop)})
  |> filter(fn: (r) => r._measurement == "derived")
  |> keep(columns: ["_time", "_field", "_value"])
"""
        return await self._run_query(flux)

    async def _run_query(self, flux: str) -> list[dict]:
        try:
            query_api = self._client.query_api()
            tables = await query_api.query(flux)
            return [
                {
                    "time": record.get_time(),
                    "sensor": record.values.get("sensor"),
                    "field": record.values.get("_field"),
                    "value": record.get_value(),
                }
                for table in tables
                for record in table.records
            ]
        except Exception:
            logger.exception("InfluxDB query failed")
            return []

    @staticmethod
    def sensors_for_device(device: str) -> list[str] | None:
        """Return sensor key list for a device name, or None for 'all'."""
        if device == "all":
            return None
        return DEVICE_SENSORS.get(device, [])


# ---------------------------------------------------------------------------
# Flux helpers
# ---------------------------------------------------------------------------

def _flux_time(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _build_sensor_filter(sensors: list[str] | None) -> str:
    if not sensors:
        return ""
    conditions = " or ".join(f'r.sensor == "{s}"' for s in sensors)
    return f"|> filter(fn: (r) => {conditions})"
