import sys

import paho.mqtt.client as mqtt


# callback for incoming messages
def on_message(mqtt_client, userdata, message):
    print(f"Received: {message.topic} -> {message.payload.decode()}")


class MqttClient:
    def __init__(self, broker, port, topics):
        topics = [(topic, 0) for topic in topics]
        print("🚀 starting MQTT client ...")
        # setup MQTT-Client
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.client.on_message = on_message

        # connect to MQTT server
        self.client.connect(broker, port, 60)

        print("Subscribing to topics ...")
        for topic in topics:
            print(f"\t{topic}")
        print("")
        # subscribe MQTT topics
        self.client.subscribe(topics)
        # loop forever to handle incoming messages
        self.client.loop_start()

    def shutdown(self, callback):
        print("🔴 shutting down MQTT client ...")
        self.client.disconnect()
        callback()
