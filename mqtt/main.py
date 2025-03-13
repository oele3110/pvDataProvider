import signal
import sys
import time

from MqttClient import MqttClient

# configuration
MQTT_BROKER = "192.168.178.182"
MQTT_PORT = 1883
MQTT_TOPICS = [
    "mqtt/0/knx/Warmwasser_Temperatur"
]


def stop(_signal, _frame):
    mqttClient.shutdown(sys.exit(0))


mqttClient = MqttClient(MQTT_BROKER, MQTT_PORT, MQTT_TOPICS)

signal.signal(signal.SIGINT, stop)

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    pass
