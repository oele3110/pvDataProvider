import paho.mqtt.client as mqtt

from utils.Utils import process_sensor_value


class MqttClient:
    def __init__(self, broker, port, config, data_store):
        self.broker = broker
        self.port = port
        self.data_store = data_store
        self.config = config
        self.topics = [(topic, 0) for topic in config]
        print("Initializing MqttClient ...")
        # setup MQTT-Client
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.client.on_message = self.on_message

    # callback for incoming messages
    def on_message(self, mqtt_client, userdata, message):
        self.data_store[message.topic] = process_sensor_value(float(message.payload.decode()), self.config["mqtt/0/" + message.topic])

    async def start(self):
        print("Starting MqttClient ...")
        # connect to MQTT server
        self.client.connect(self.broker, self.port, 60)
        print("Subscribing to topics ...")
        # subscribe MQTT topics
        self.client.subscribe(self.topics)
        # loop forever to handle incoming messages
        self.client.loop_start()

    async def stop(self):
        print("Stopping MqttClient ...")
        self.client.disconnect()
