import yaml
from pathlib import Path

_CONFIG_PATH = Path(__file__).parent / "config.yaml"


def load_config(path: Path = _CONFIG_PATH) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_modbus_config(cfg: dict) -> dict:
    return cfg["devices"]["modbus"]


def get_heater_rod_config(cfg: dict) -> dict:
    return cfg["devices"]["heater_rod"]


def get_mqtt_config(cfg: dict) -> dict:
    return cfg["devices"]["mqtt"]


def get_influxdb_config(cfg: dict) -> dict:
    return cfg["influxdb"]
