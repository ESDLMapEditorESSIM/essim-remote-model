#!/usr/bin/python

import paho.mqtt.client as mqtt
import struct

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))
    topic = "TESTTOPIC/node/#"
    print("Subscribed to {}".format(topic))
    client.subscribe(topic,2)
    
# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    print(msg.topic)
    print(len(msg.payload))

    try:
        [simId, timestep, duration, minprice, maxprice] = struct.unpack(">qqqdd",msg.payload)
        print("Received message from client " + str(simId))
        response = struct.pack(">qdddd", timestep, minprice, -1337, maxprice, -1337)
        client.publish("TESTTOPIC/simulation/bid", response);
    except Exception as e:
        print(e)

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect("localhost")

client.loop_forever()
