import asyncio
import json
import signal
import sys

from configs.HeaterRodConfig import heater_rod_config
from configs.ModbusConfig import modbus_config
from configs.MqttConfig import mqtt_config
from heaterRod.HeaterRodClient import HeaterRodClient
from jsonParser.JsonConverter import JsonConverter
from modbus.ModbusClient import ModbusClient
from mqtt.MqttClient import MqttClient
from websocket.WebsocketServer import start_websocket_server, shutdown_websocket_server, update_data, shutdown_event

# heater rod configuration
heater_rod_ipaddress = "192.168.178.174"

# mqtt configuration
MQTT_BROKER = "192.168.178.182"
MQTT_PORT = 1883

# data stores
heater_rod_data_store = {}
mqtt_data_store = {}
modbus_data_store = {}

json_converter = JsonConverter(heater_rod_config, mqtt_config, modbus_config)
json_data = json.dumps({})


def setup_signal_handling():
    def trigger_shutdown():
        print("\n🛑 Shutdown signal received")
        shutdown_event.set()

    if sys.platform != "win32":
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, trigger_shutdown)
    else:
        print("⚠️ Signal handling not supported on Windows – use CTRL+C")


async def convert_data_stores():
    global json_data
    while not shutdown_event.is_set():
        json_data = json_converter.convert_data(heater_rod_data_store, mqtt_data_store, modbus_data_store)
        update_data(json_data)
        await asyncio.sleep(1)


async def main():
    setup_signal_handling()

    heater_rod_client = HeaterRodClient(heater_rod_ipaddress, heater_rod_config, heater_rod_data_store)
    modbus_client = ModbusClient(modbus_data_store)
    mqtt_client = MqttClient(MQTT_BROKER, MQTT_PORT, mqtt_config, mqtt_data_store)

    print("Start HeaterRodClient")
    heater_rod_task = asyncio.create_task(heater_rod_client.start(), name="HeaterRodClient")
    print("Start ModbusClient")
    modbus_task = asyncio.create_task(modbus_client.start(), name="ModbusClient")
    print("Start MqttClient")
    mqtt_task = asyncio.create_task(mqtt_client.start(), name="MqttClient")

    convert_task = asyncio.create_task(convert_data_stores(), name="DataConverter")
    websocket_task = asyncio.create_task(start_websocket_server(), name="WebSocketServer")

    tasks = [heater_rod_task, modbus_task, mqtt_task, convert_task, websocket_task]

    try:
        await shutdown_event.wait()  # wait until SIGINT or manuel shutdown is set (CTRL + C)
    finally:
        print("\n🔻 Shutdown event triggered – stopping all tasks ...")

        await shutdown_websocket_server()
        await heater_rod_client.stop()
        await modbus_client.stop()
        await mqtt_client.stop()

        # cancel all running tasks
        for task in tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    print(f"❌ Task {task.get_name()} cancelled")

        await asyncio.sleep(0.2)  # wait a bit to ensure that all tasks are stopped
        print("✅ All tasks stopped")
        print("👋 Program stopped")


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 KeyboardInterrupt fallback – triggering shutdown")
        shutdown_event.set()
