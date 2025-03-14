import asyncio

from heaterRod.heaterRod import HeaterRod
from modbus.modbus import Modbus
from mqtt.MqttClient import MqttClient

# heater rod configuration
heater_rod_ipaddress = "192.168.178.174"
heater_rod_data_store = {}
values = ['power_elwa2', 'temp1', 'temp2']

# mqtt configuration
MQTT_BROKER = "192.168.178.182"
MQTT_PORT = 1883
MQTT_TOPICS = [
    "mqtt/0/knx/Warmwasser_Temperatur"
]
mqtt_data_store = {}

# modbus configuration
modbus_data_store = {}


async def print_data_store(label, data_store):
    while True:
        print(f"{label}: {data_store}")
        await asyncio.sleep(1)


async def main():
    heater_rod = HeaterRod(heater_rod_ipaddress, values, heater_rod_data_store)
    modbus = Modbus(modbus_data_store)
    mqtt = MqttClient(MQTT_BROKER, MQTT_PORT, MQTT_TOPICS, mqtt_data_store)

    print("Start HeaterRod")
    heater_rod_task = asyncio.create_task(heater_rod.start())
    print("Start Modbus")
    modbus_task = asyncio.create_task(modbus.start())
    print("Start MQTT")
    mqtt_task = asyncio.create_task(mqtt.start())

    print_task_modbus = asyncio.create_task(print_data_store("Modbus", modbus_data_store))
    print_task_heater_rod = asyncio.create_task(print_data_store("Heater Rod", heater_rod_data_store))
    print_task_mqtt = asyncio.create_task(print_data_store("MQTT", mqtt_data_store))

    tasks = [heater_rod_task, modbus_task, mqtt_task, print_task_modbus, print_task_heater_rod, print_task_mqtt]

    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        pass
    finally:
        print("Stopping tasks")
        await heater_rod.stop()
        await modbus.stop()
        await mqtt.stop()
        for task in tasks:
            task.cancel()
        print("All tasks stopped")


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Program stopped")
