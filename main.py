import asyncio

from configs.HeaterRodConfig import heater_rod_config
from configs.MqttConfig import mqtt_config
from heaterRod.HeaterRodClient import HeaterRodClient
from modbus.ModbusClient import ModbusClient
from mqtt.MqttClient import MqttClient

# heater rod configuration
heater_rod_ipaddress = "192.168.178.174"

# mqtt configuration
MQTT_BROKER = "192.168.178.182"
MQTT_PORT = 1883

# data stores
heater_rod_data_store = {}
mqtt_data_store = {}
modbus_data_store = {}


async def print_data_store(label, data_store):
    while True:
        print(f"{label}: {data_store}")
        await asyncio.sleep(1)


async def main():
    heater_rod_client = HeaterRodClient(heater_rod_ipaddress, heater_rod_config, heater_rod_data_store)
    modbus_client = ModbusClient(modbus_data_store)
    mqtt_client = MqttClient(MQTT_BROKER, MQTT_PORT, mqtt_config, mqtt_data_store)

    print("Start HeaterRodClient")
    heater_rod_task = asyncio.create_task(heater_rod_client.start())
    print("Start ModbusClient")
    modbus_task = asyncio.create_task(modbus_client.start())
    print("Start MqttClient")
    mqtt_task = asyncio.create_task(mqtt_client.start())

    print_task_modbus = asyncio.create_task(print_data_store("ModbusClient", modbus_data_store))
    print_task_heater_rod = asyncio.create_task(print_data_store("HeaterRodClient", heater_rod_data_store))
    print_task_mqtt = asyncio.create_task(print_data_store("MqttClient", mqtt_data_store))

    tasks = [heater_rod_task, modbus_task, mqtt_task, print_task_modbus, print_task_heater_rod, print_task_mqtt]

    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        print("Tasks cancelled, shutting down ...")
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        print("Stopping all tasks ...")
        await asyncio.gather(heater_rod_client.stop(), modbus_client.stop(), mqtt_client.stop(), return_exceptions=True)
        # wait 200 ms to give the tasks time to stop and shutdown clean
        await asyncio.sleep(0.2)
        # cancel all tasks
        for task in tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        print("All tasks stopped")


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Program stopped")
