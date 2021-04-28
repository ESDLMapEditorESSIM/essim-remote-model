#!/usr/bin/python

import paho.mqtt.client as mqtt
import struct
import random
import math

essimTopic = "essim"
nodeId = "PVInstallation_3559"
mwp = 10


def on_connect(client, userdata, flags, rc):
    print("Connected with result code " + str(rc))
    topic = "{}/node/{}/#".format(essimTopic, nodeId)
    print("Subscribed to {}".format(topic))
    client.subscribe(topic, 2)


def on_message(client, userdata, msg):
    # print(msg.topic)
    # print(len(msg.payload))
    try:
        if str(msg.topic).endswith("/config"):
            print('Received config message!')
            print(msg.payload)
        elif str(msg.topic).endswith("/createBid"):
            print('Received createBid message!')
            [timestep, duration, minprice, maxprice] = struct.unpack(">qqdd", msg.payload)
            # print("Received message from client: ")
            # print("\tTimestep: {}".format(timestep))
            # print("\tDuration: {}".format(duration))
            # print("\tminprice: {}".format(minprice))
            # print("\tmaxprice: {}".format(maxprice))
            time_of_day = timestep % 86400
            e = min(0, mwp * 1000000 * duration * (0.8 + 0.4 * random.random()) * math.pow(
                math.cos(time_of_day / (86400 / (2 * math.pi))), 3))

            response = struct.pack(">qdddd", timestep, minprice, e, maxprice, e)
            client.publish("{}/simulation/{}/bid".format(essimTopic, nodeId), response)
        elif str(msg.topic).endswith("/allocate"):
            [timestep, price] = struct.unpack(">qd", msg.payload)
            print('Received price for timestep {}:{}'.format(timestep, price))
    except Exception as e:
        print(e)


client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect("localhost")

try:
    client.loop_forever()
except KeyboardInterrupt:
    client.disconnect()
    print("")
