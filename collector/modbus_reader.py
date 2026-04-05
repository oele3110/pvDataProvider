import asyncio
import logging

from modbusReader.ModbusDataType import ModbusDataType
from modbusReader.ModbusReader import ModbusReader

from collector.base_reader import BaseReader

logger = logging.getLogger(__name__)

_TYPE_MAP: dict[str, ModbusDataType] = {
    "INT32": ModbusDataType.INT32,
    "UINT16": ModbusDataType.UINT16,
    "UINT32": ModbusDataType.UINT32,
    "UINT64": ModbusDataType.UINT64,
}


def _resolve_types(registers: dict) -> dict:
    """Return a copy of registers with type strings replaced by ModbusDataType enums."""
    resolved = {}
    for name, cfg in registers.items():
        entry = dict(cfg)
        raw_type = cfg.get("type")
        if raw_type not in _TYPE_MAP:
            raise ValueError(f"Unknown Modbus type '{raw_type}' for register '{name}'")
        entry["type"] = _TYPE_MAP[raw_type]
        resolved[name] = entry
    return resolved


class ModbusReaderClient(BaseReader):
    def __init__(self, modbus_cfg: dict, data_store: dict, on_success: callable = None) -> None:
        host: str = modbus_cfg["host"]
        self._poll_interval: float = modbus_cfg.get("poll_interval_s", 1)
        self._registers: dict = _resolve_types(modbus_cfg["registers"])
        self._data_store = data_store
        self._on_success = on_success
        self._stop_event = asyncio.Event()
        self._task: asyncio.Task | None = None

        logger.info("Initializing ModbusReaderClient (host=%s) ...", host)
        self._reader = ModbusReader(host)

    async def start(self) -> None:
        logger.info("Starting ModbusReaderClient ...")
        self._task = asyncio.create_task(self._run())

    async def _run(self) -> None:
        while not self._stop_event.is_set():
            success = False
            for name, cfg in self._registers.items():
                try:
                    value = self._reader.read_modbus(cfg)
                    self._data_store[name] = value
                    success = True
                except Exception:
                    logger.exception("Modbus read failed for register '%s'", name)
            if success and self._on_success:
                self._on_success()
            await asyncio.sleep(self._poll_interval)

    async def stop(self) -> None:
        logger.info("Stopping ModbusReaderClient ...")
        self._stop_event.set()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._reader.__shutdown__()
