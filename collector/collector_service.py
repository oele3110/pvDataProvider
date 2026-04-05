import asyncio
import logging
from datetime import datetime, timezone

from collector.http_reader import HttpReader
from collector.modbus_reader import ModbusReaderClient
from collector.mqtt_reader import MqttReader
from config.loader import load_config, get_modbus_config, get_heater_rod_config, get_mqtt_config
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

        self._modbus_reader = ModbusReaderClient(get_modbus_config(cfg), self.modbus_data, _on_modbus_success)
        self._http_reader = HttpReader(get_heater_rod_config(cfg), self.heater_rod_data, _on_heater_success)
        self._mqtt_reader = MqttReader(get_mqtt_config(cfg), self.mqtt_data, _on_mqtt_success)
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

    @property
    def influx(self) -> InfluxClient:
        return self._influx

    async def _influx_write_loop(self) -> None:
        while not self._stop_event.is_set():
            data = self.get_live_data()
            if data:
                await self._influx.write_raw(data, datetime.now(timezone.utc))
            await asyncio.sleep(_INFLUX_WRITE_INTERVAL_S)
