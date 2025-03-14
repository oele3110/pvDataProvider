import paho.mqtt.client as mqtt


class MqttClient:
    def __init__(self, broker, port, topics, data_store):
        self.broker = broker
        self.port = port
        self.data_store = data_store
        self.topics = [(topic, 0) for topic in topics]
        print("🚀 starting MQTT client ...")
        # setup MQTT-Client
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.client.on_message = self.on_message

    # callback for incoming messages
    def on_message(self, mqtt_client, userdata, message):
        self.data_store[message.topic] = message.payload.decode()

    async def start(self):
        print("Starting MQTT client ...")
        # connect to MQTT server
        self.client.connect(self.broker, self.port, 60)
        print("Subscribing to topics ...")
        # subscribe MQTT topics
        self.client.subscribe(self.topics)
        # loop forever to handle incoming messages
        self.client.loop_start()

    async def stop(self):
        print("Stopping MQTT client ...")
        self.client.disconnect()
