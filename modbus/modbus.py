import asyncio
import json

from modbusReader.ModbusReader import ModbusReader

from modbus.ModbusConfig import modbus_config


def read_smartmeter_config():
    with open('smartMeterConfig.json', 'r') as file:
        data = json.load(file)
    return data.get('host')


class Modbus:
    def __init__(self, data_store):
        host = read_smartmeter_config()
        self.modbusReader = ModbusReader(host)
        self.dataStore = data_store
        self._stop_event = asyncio.Event()

    async def start(self):
        while not self._stop_event.is_set():
            try:
                for config in modbus_config:
                    data = self.modbusReader.read_modbus(modbus_config[config])
                    self.dataStore[config] = data
                await asyncio.sleep(1)
            except Exception as e:
                print(f"Modbus error: {e}")

    async def stop(self):
        print("Stopping Modbus ...")
        self._stop_event.set()
