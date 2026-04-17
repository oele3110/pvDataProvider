import asyncio
import logging
from datetime import datetime, timezone

from collector.http_reader import HttpReader
from collector.modbus_reader import ModbusReaderClient
from collector.mqtt_reader import MqttReader
from config.loader import load_config, get_modbus_config, get_heater_rod_config, get_mqtt_config, get_influxdb_config
from db.influx_client import InfluxClient

logger = logging.getLogger(__name__)

_INFLUX_WRITE_INTERVAL_S = 1


class CollectorService:
    def __init__(self) -> None:
        cfg = load_config()

        # Separate data stores per source — same pattern as the original main.py
        self.modbus_data: dict = {}
        self.heater_rod_data: dict = {}
        self.mqtt_data: dict = {}

        # Tracks the last successful read timestamp per device
        self.last_seen: dict[str, datetime | None] = {
            "modbus": None,
            "heater_rod": None,
            "mqtt": None,
        }

        def _on_modbus_success() -> None:
            self.last_seen["modbus"] = datetime.now(timezone.utc)

        def _on_heater_success() -> None:
            self.last_seen["heater_rod"] = datetime.now(timezone.utc)

        def _on_mqtt_success() -> None:
            self.last_seen["mqtt"] = datetime.now(timezone.utc)

        mqtt_cfg = get_mqtt_config(cfg)
        # Build mapping: short topic key → endpoint name (for stable consumer keys)
        self._consumer_key_map: dict[str, str] = {
            short: topic_cfg.get("endpoint", short.replace("knx/", ""))
            for short, topic_cfg in mqtt_cfg["topics"].items()
        }

        self._modbus_reader = ModbusReaderClient(get_modbus_config(cfg), self.modbus_data, _on_modbus_success)
        self._http_reader = HttpReader(get_heater_rod_config(cfg), self.heater_rod_data, _on_heater_success)
        self._mqtt_reader = MqttReader(mqtt_cfg, self.mqtt_data, _on_mqtt_success)
        self._influx = InfluxClient(cfg["influxdb"])

        self._stop_event = asyncio.Event()
        self._tasks: list[asyncio.Task] = []

    async def start(self) -> None:
        logger.info("Starting CollectorService ...")
        await self._influx.start()
        # ModbusReaderClient.start() creates an internal task and returns immediately
        await self._modbus_reader.start()
        # MqttReader.start() connects and starts the paho thread, returns immediately
        await self._mqtt_reader.start()
        # HttpReader.start() runs a blocking while-loop → wrap as task
        self._tasks = [
            asyncio.create_task(self._http_reader.start(), name="HttpReader"),
            asyncio.create_task(self._influx_write_loop(), name="InfluxWriteLoop"),
        ]

    async def stop(self) -> None:
        logger.info("Stopping CollectorService ...")
        self._stop_event.set()
        await self._modbus_reader.stop()
        await self._http_reader.stop()
        await self._mqtt_reader.stop()

        for task in self._tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        await self._influx.stop()

    def get_live_data(self) -> dict:
        """Return a snapshot of all current sensor values, keyed by sensor name."""
        return {
            **self.modbus_data,
            **self.heater_rod_data,
            **self.mqtt_data,
        }

    def get_structured_live_data(self) -> dict:
        """Return sensor values grouped by device, ready for the WebSocket payload."""
        d = self.get_live_data()

        pv = d.get("sum_pv_power_inverter_dc")
        grid = d.get("grid_power_total")
        home = d.get("home_consumption")

        # Derived calculations
        self_consumption_w = None
        self_consumption_rate_pct = None
        autarky_rate_pct = None
        if pv is not None and grid is not None:
            grid_feed = max(grid, 0)
            self_consumption_w = pv - grid_feed
            if pv > 0:
                self_consumption_rate_pct = round(self_consumption_w / pv * 100, 1)
        if self_consumption_w is not None and home is not None and home > 0:
            autarky_rate_pct = round(self_consumption_w / home * 100, 1)

        # All expected consumer keys pre-filled with None, then overwritten with live values
        consumers = {
            endpoint: self.mqtt_data.get(short)
            for short, endpoint in self._consumer_key_map.items()
        }

        return {
            "inverter": {
                "power_ac_w": d.get("sum_output_inverter_ac"),
                "power_dc_w": d.get("sum_pv_power_inverter_dc"),
                "home_consumption_from_pv_w": d.get("home_consumption_from_pv"),
            },
            "smartmeter": {
                "grid_power_w": d.get("grid_power_total"),
                "home_consumption_w": d.get("home_consumption"),
                "home_consumption_from_grid_w": d.get("home_consumption_from_grid"),
                "home_consumption_from_battery_w": d.get("home_consumption_from_battery"),
            },
            "wallbox": {
                "power_w": d.get("sum_wallbox_charge_power_total"),
                "power_pv_w": d.get("sum_wallbox_charge_power_pv"),
                "power_battery_w": d.get("sum_wallbox_charge_power_battery"),
                "power_grid_w": d.get("sum_wallbox_charge_power_grid"),
                "session_energy_wh": d.get("current_session_energy"),
                "session_duration_min": d.get("current_session_duration"),
                "active_charge_mode": d.get("active_charge_mode"),
                "status_code": d.get("wallbox_status_code"),
            },
            "battery": {
                "power_w": d.get("sum_battery_charge_discharge_dc"),
                "state_of_charge_pct": d.get("system_state_of_charge"),
            },
            "heater": {
                "power_w": d.get("power_elwa2"),
                "temp1_c": d.get("temp1"),
                "temp2_c": d.get("temp2"),
            },
            "consumers": consumers,
            "calculated": {
                "self_consumption_w": self_consumption_w,
                "self_consumption_rate_pct": self_consumption_rate_pct,
                "autarky_rate_pct": autarky_rate_pct,
            },
        }

    @property
    def influx(self) -> InfluxClient:
        return self._influx

    async def _influx_write_loop(self) -> None:
        while not self._stop_event.is_set():
            data = self.get_live_data()
            if data:
                await self._influx.write_raw(data, datetime.now(timezone.utc))
            await asyncio.sleep(_INFLUX_WRITE_INTERVAL_S)
