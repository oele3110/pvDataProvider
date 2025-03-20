import json

JSON_VERSION = 1.0


def _convert_data(heater_rod_data_store, config):
    data = []
    for key, value in heater_rod_data_store.items():
        try:
            obj = {}
            config_data = config[key]
            if "endpoint" in config_data:
                obj["endpoint"] = config_data["endpoint"]
            else:
                obj["endpoint"] = key
            obj["value"] = value
            obj["datatype"] = config_data["datatype"]
            obj["unit"] = config_data["unit"]
            obj["displayString"] = config_data["displayString"]

            if "division" in config_data:
                obj["division"] = config_data["division"]
            if "divisionUnit" in config_data:
                obj["divisionUnit"] = config_data["divisionUnit"]
            if "divisionDigits" in config_data:
                obj["divisionDigits"] = config_data["divisionDigits"]
            if "mapping" in config_data:
                obj["mapping"] = config_data["mapping"]

            data.append(obj)
        except KeyError:
            print(f"KeyError: {key}")
    return data


class JsonConverter:
    def __init__(self, heater_rod_config, mqtt_config, modbus_config):
        self.heater_rod_config = heater_rod_config
        self.mqtt_config = mqtt_config
        self.modbus_config = modbus_config

    def convert_data(self, heater_rod_data_store, mqtt_data_store, modbus_data_store):
        heater_rod_data = _convert_data(heater_rod_data_store, self.heater_rod_config)
        mqtt_data = _convert_data(mqtt_data_store, self.mqtt_config)
        modbus_data = _convert_data(modbus_data_store, self.modbus_config)
        print(f"HeaterRodData: {heater_rod_data}")
        print(f"MqttData: {mqtt_data}")
        print(f"ModbusData: {modbus_data}")
        data = heater_rod_data.copy()
        data.extend(mqtt_data)
        data.extend(modbus_data)
        return json.dumps({"version": JSON_VERSION, "pvData": data}, indent=2)
