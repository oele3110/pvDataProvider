import json

from modbusReader.ModbusConfig import modbus_wallbox_config
from modbusReader.ModbusReader import ModbusReader


def read_smartmeter_config():
    with open('smartMeterConfig.json', 'r') as file:
        data = json.load(file)
    return data.get('host')


if __name__ == '__main__':
    host = read_smartmeter_config()
    print("PV Data Provider")
    modbusReader = ModbusReader(host)
    print(modbusReader.read_modbus(modbus_wallbox_config["wallbox_status_code"]))
    modbusReader.__shutdown__()
