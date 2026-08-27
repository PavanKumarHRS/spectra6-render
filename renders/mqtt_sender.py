import json
import paho.mqtt.client as mqtt

# MQTT Broker
MQTT_HOST = "broker.hivemq.com"
MQTT_PORT = 1883

# MQTT Topic
MQTT_TOPIC = "gateways/RIGHTO/commands"


def send_to_device(device_name):

    client = mqtt.Client(client_id="cloudrun")

    try:

        # Connect to broker
        client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)

        # Start MQTT network loop
        client.loop_start()

        # Payload
        payload = {
            "nrf": device_name
        }

        print(f"Publishing to: {MQTT_TOPIC}")
        print(f"Payload: {payload}")

        # Publish
        info = client.publish(
            MQTT_TOPIC,
            json.dumps(payload),
            qos=1
        )

        # Wait max 5 seconds
        info.wait_for_publish(timeout=5)

        if info.is_published():
            print("MQTT message published successfully")
        else:
            print("MQTT publish timeout")

        return True

    except Exception as e:

        print(f"MQTT Error: {e}")
        return False

    finally:

        try:
            client.loop_stop()
        except Exception:
            pass

        try:
            client.disconnect()
        except Exception:
            pass