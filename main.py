import json
import asyncio
import websockets

from modbusReader.ModbusConfig import modbus_wallbox_config
from modbusReader.ModbusReader import ModbusReader

myModbusReader = None


async def send_data(websocket):
    while True:
        connection_status = myModbusReader.read_modbus(modbus_wallbox_config["wallbox_status_code"])
        print("Send current connection status to client: " + str(connection_status))
        await websocket.send("Connection Status: " + str(connection_status))
        await asyncio.sleep(1)


async def start_websocket():
    async with websockets.serve(send_data, "localhost", 8765):
        await asyncio.Future()  # keep server running


def read_smartmeter_config():
    with open('smartMeterConfig.json', 'r') as file:
        data = json.load(file)
    return data.get('host')


if __name__ == '__main__':
    host = read_smartmeter_config()
    print("PV Data Provider")
    myModbusReader = ModbusReader(host)
    asyncio.run(start_websocket())  # start event loop
