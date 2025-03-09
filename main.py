import asyncio
import json
import signal
import sys

import websockets
from modbusReader.ModbusReader import ModbusReader

from ModbusConfig import modbus_wallbox_config

myModbusReader = None
connected_clients = set()
shutdown_event = asyncio.Event()  # event for shutdown


async def send_data():
    # stop sending data if shutdown event is set
    while not shutdown_event.is_set():
        # only send data if there are connected clients
        if connected_clients:
            connection_status = myModbusReader.read_modbus(modbus_wallbox_config["home_consumption"])
            data = "Current consumption: " + str(connection_status) + "W"
            print(f"Data sent:")
            print(f">>> {data}")
            await asyncio.gather(*(client.send(data) for client in connected_clients))
        await asyncio.sleep(1)


async def handle_client(websocket):
    connected_clients.add(websocket)
    print(f"✅ Client connected: {websocket.remote_address}")
    try:
        await websocket.wait_closed()
    finally:
        if websocket in connected_clients:
            connected_clients.remove(websocket)
            print(f"❌ Client disconnected: {websocket.remote_address}")


async def shutdown():
    print(f"🔴 shutting down server ...")

    if connected_clients:
        print(f"📢 all clients informed about shutdown")
        tasks = [client.close(code=1001, reason="Server shutdown") for client in connected_clients]
        # await asyncio.gather(*(client.close(code=1001, reason="Server shutdown") for client in connected_clients))
        await asyncio.gather(*tasks)
        await asyncio.sleep(1)  # wait a bit to ensure that all close frames are sent

    shutdown_event.set()


async def start_websocket():
    # start websocket server and stop it if shutdown event is set
    stop = asyncio.Future()  # future to stop server

    async with websockets.serve(handle_client, "0.0.0.0", 8765):
        print("🚀 websocket server running of port 8765...")
        try:
            await asyncio.gather(send_data(), stop)  # run server until stop signal
        except asyncio.CancelledError:
            pass
        finally:
            await shutdown()


def read_smartmeter_config():
    with open('smartMeterConfig.json', 'r') as file:
        data = json.load(file)
    return data.get('host')


if __name__ == '__main__':
    host = read_smartmeter_config()
    print("PV Data Provider")
    myModbusReader = ModbusReader(host)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # signal handler for shutdown (only linux)
    if sys.platform != "win32":
        loop.add_signal_handler(signal.SIGINT, lambda: asyncio.create_task(shutdown()))
    try:
        loop.run_until_complete(start_websocket())  # start event loop
    except KeyboardInterrupt:
        print("\n🛑 server stopped")
        loop.run_until_complete(shutdown())
        sys.exit(0)
