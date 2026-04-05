import asyncio
import logging

import aiohttp

from collector.base_reader import BaseReader

logger = logging.getLogger(__name__)


def _apply_transforms(raw_value: float, field_cfg: dict) -> int | float:
    value: float = raw_value
    if "factor" in field_cfg:
        value *= field_cfg["factor"]
    digits = field_cfg.get("digits_round")
    if digits is not None:
        value = round(value, digits)
        if digits == 0:
            value = int(value)
    return value


class HttpReader(BaseReader):
    def __init__(self, heater_rod_cfg: dict, data_store: dict, on_success: callable = None) -> None:
        self._host: str = heater_rod_cfg["host"]
        self._api_path: str = heater_rod_cfg.get("api_path", "/data.jsn")
        self._poll_interval: float = heater_rod_cfg.get("poll_interval_s", 5)
        self._fields: dict = heater_rod_cfg["fields"]
        self._data_store = data_store
        self._on_success = on_success
        self._stop_event = asyncio.Event()

        logger.info("Initializing HttpReader (host=%s) ...", self._host)

    @property
    def _url(self) -> str:
        return f"http://{self._host}{self._api_path}"

    async def start(self) -> None:
        logger.info("Starting HttpReader ...")
        async with aiohttp.ClientSession() as session:
            while not self._stop_event.is_set():
                await self._poll(session)
                await asyncio.sleep(self._poll_interval)

    async def _poll(self, session: aiohttp.ClientSession) -> None:
        try:
            async with session.get(self._url) as response:
                if response.status == 200:
                    payload: dict = await response.json()
                    for field_name, field_cfg in self._fields.items():
                        raw = payload.get(field_name)
                        if raw is not None:
                            self._data_store[field_name] = _apply_transforms(raw, field_cfg)
                    if self._on_success:
                        self._on_success()
                else:
                    logger.warning("HttpReader: unexpected status %s from %s", response.status, self._url)
        except Exception:
            logger.exception("HttpReader: failed to poll %s", self._url)

    async def stop(self) -> None:
        logger.info("Stopping HttpReader ...")
        self._stop_event.set()
