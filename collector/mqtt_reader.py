import asyncio
import logging
import threading

import paho.mqtt.client as mqtt

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


class MqttReader(BaseReader):
    def __init__(self, mqtt_cfg: dict, data_store: dict, on_success: callable = None) -> None:
        self._broker: str = mqtt_cfg["broker"]
        self._port: int = mqtt_cfg["port"]
        self._prefix: str = mqtt_cfg.get("topic_prefix", "")
        self._topics: dict = mqtt_cfg["topics"]
        self._data_store = data_store
        self._on_success = on_success
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None

        self._topic_lookup: dict[str, tuple[str, dict]] = {
            self._prefix + short: (short, cfg)
            for short, cfg in self._topics.items()
        }

        logger.info("Initializing MqttReader (broker=%s:%s) ...", self._broker, self._port)
        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self._client.on_message = self._on_message
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        # Aktiviert paho's eingebautes Reconnect in loop_forever()
        self._client.reconnect_delay_set(min_delay=1, max_delay=30)
        # Temporär: paho internen Debug-Logger aktivieren
        paho_logger = logging.getLogger("paho.mqtt")
        paho_logger.setLevel(logging.DEBUG)
        self._client.enable_logger(paho_logger)

    # ── paho callbacks (laufen im MqttReader-Thread) ───────────────────────

    def _on_connect(self, client, userdata, flags, reason_code, properties) -> None:
        if reason_code == 0:
            subscriptions = [(topic, 0) for topic in self._topic_lookup]
            client.subscribe(subscriptions)
            logger.info("MqttReader: connected and subscribed to %d topics", len(subscriptions))
            if self._on_success:
                self._on_success()
        else:
            logger.error("MqttReader: connection failed with reason code %s", reason_code)

    def _on_disconnect(self, client, userdata, flags, reason_code, properties) -> None:
        if reason_code != 0:
            logger.warning("MqttReader: unexpected disconnect (reason=%s), reconnecting ...", reason_code)

    def _on_message(self, client, userdata, message) -> None:
        full_topic: str = message.topic
        logger.info("MqttReader: message topic='%s' payload='%s'", full_topic, message.payload)
        entry = self._topic_lookup.get(full_topic)
        if entry is None:
            logger.warning("MqttReader: received message on unknown topic '%s'", full_topic)
            return
        short_key, field_cfg = entry
        try:
            raw = float(message.payload.decode())
            self._data_store[short_key] = _apply_transforms(raw, field_cfg)
            if self._on_success:
                self._on_success()
        except (ValueError, UnicodeDecodeError):
            logger.warning("MqttReader: could not parse payload for topic '%s'", full_topic)

    # ── paho network thread ────────────────────────────────────────────────

    def _run_loop(self) -> None:
        # connect_async() setzt nur den State — kein internes loop_start()
        # loop_forever() stellt die Verbindung her und hält sie aufrecht (inkl. PINGREQ)
        try:
            self._client.connect_async(self._broker, self._port, keepalive=60)
            self._client.loop_forever()
        except Exception:
            logger.exception("MqttReader: loop_forever exited with exception")

    # ── lifecycle ──────────────────────────────────────────────────────────

    async def start(self) -> None:
        logger.info("Starting MqttReader ...")
        self._loop = asyncio.get_running_loop()
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="MqttReader")
        self._thread.start()

    async def stop(self) -> None:
        logger.info("Stopping MqttReader ...")
        self._client.disconnect()
        if self._thread:
            await self._loop.run_in_executor(None, lambda: self._thread.join(timeout=5))
