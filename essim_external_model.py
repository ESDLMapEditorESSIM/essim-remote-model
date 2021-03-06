#!/usr/bin/python
import base64
import os
import json
import log4p
import struct
import paho.mqtt.client as mqtt
from esdl.esdl_handler import EnergySystemHandler

from protobuf_scaling_messages.lifecycle_pb2 import ReadyForProcessing

LOG4P_JSON_LOCATION = os.getenv('LOG4P_JSON_LOCATION', r'log4p.json')
log = log4p.GetLogger(__name__, config=LOG4P_JSON_LOCATION).logger


class ESSIMExternalModel:
    def __init__(self,
                 server='localhost',
                 port=1883,
                 mqtt_username=None,
                 mqtt_password=None,
                 env_essim_id=None,
                 env_simulation_id=None,
                 env_NODE_ID=None):

        # MQTT information
        self.server = server
        self.port = port
        self.mqtt_username = mqtt_username
        self.mqtt_password = mqtt_password
        self.topic = None
        self.node_id = None
        self.client = None

        # Config information
        self.energy_system = None
        self.simulation_id = None

        # Scaling node information
        self.env_essim_id = '' if env_essim_id is None else env_essim_id
        self.env_simulation_id = '' if env_simulation_id is None else env_simulation_id
        self.env_NODE_ID = '' if env_NODE_ID is None else env_NODE_ID

    def connect(self, topic, node_id):
        self.topic = topic
        self.node_id = node_id

        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

        if self.mqtt_username and self.mqtt_password:
            log.info(f"Using MQTT username {self.mqtt_username} & password <hidden> for connecting.")
            self.client.username_pw_set(self.mqtt_username, self.mqtt_password)
        self.client.connect(host=self.server, port=self.port)

        self.client.publish(f'/lifecycle/model/mso/{self.env_simulation_id}/{self.env_NODE_ID}/ReadyForProcessing',
                            ReadyForProcessing().SerializeToString())

    def on_connect(self, client, userdata, flags, rc):
        log.info("Connected with result code " + str(rc))
        topic = "{}/node/{}/#".format(self.topic, self.node_id)
        log.debug("Subscribed to {}".format(topic))
        self.client.subscribe(topic, 2)

    def on_message(self, client, userdata, msg):
        log.info(f'Received message {msg.payload} on topic {msg.topic}')
        log.info(msg.payload)
        try:
            if str(msg.topic).endswith("/config"):
                log.debug('Received config message!')
                message = json.loads(msg.payload.decode('utf-8'))
                esdl_contents = message['esdlContents']
                self.energy_system = ESSIMExternalModel.parse_esdl(esdl_contents)
                self.simulation_id = message['simulationId']

                # Initialize model with

            elif str(msg.topic).endswith("/stop"):
                log.debug('Received stop message!')

                # Clean up after a simulation here

            elif str(msg.topic).endswith("/createBid"):
                log.debug('Received createBid message!')
                message = json.loads(msg.payload.decode('utf-8'))
                timestep = message['timeStamp']
                minprice = message['minPrice']
                maxprice = message['maxPrice']
                duration = message['timeStepInSeconds']
                carrier_id = message['carrierId']

                # Logic to convert model physics to bid curve goes here

                e = 0
                response = struct.pack(">qdddddd", timestep, minprice, e, (minprice + maxprice) / 2, e, maxprice, e)
                client.publish("{}/simulation/{}/bid".format(self.topic, self.node_id), response)

            elif str(msg.topic).endswith("/allocate"):
                log.debug('Received allocate message!')
                message = json.loads(msg.payload.decode('utf-8'))
                timestep = message['timeStamp']
                price = message['price']
                carrier_id = message['carrierId']

                log.debug('Received price for timestep {}:{}'.format(timestep, price))

                # Process allocation here

        except Exception as e:
            log.error(e)

    def loop(self):
        try:
            self.client.loop_forever()
        except KeyboardInterrupt:
            self.client.disconnect()
            log.debug("")

    @staticmethod
    def parse_esdl(esdl_contents):
        esdlstr_bytes = esdl_contents.encode("ascii")
        esdlstr_base64_bytes = base64.b64decode(esdlstr_bytes)
        esdlstr = esdlstr_base64_bytes.decode("ascii")
        esh = EnergySystemHandler()
        return esh.load_from_string(esdlstr)


if __name__ == '__main__':
    MQTT_HOST = os.getenv('MQTT_HOST', 'localhost')
    MQTT_PORT = int(os.getenv('MQTT_PORT', '1883'))
    MQTT_USERNAME = os.getenv('MQTT_USERNAME', None)
    MQTT_PASSWORD = os.getenv('MQTT_PASSWORD', None)
    NODE_ID = os.getenv('NODE_ID', None)
    ESSIM_ID = os.getenv('ESSIM_ID', None)
    SIMULATION_ID = os.getenv('SIMULATION_ID', None)
    ESSIM_TOPIC = os.getenv('ESSIM_TOPIC', 'essim')

    log.debug(f'MQTT_HOST:     {MQTT_HOST}')
    log.debug(f'MQTT_PORT:     {MQTT_PORT}')
    log.debug(f'MQTT_USERNAME: {MQTT_USERNAME}')
    log.debug(f'MQTT_PASSWORD: "<hidden>"')
    log.debug(f'ESSIM_ID:      {ESSIM_ID}')
    log.debug(f'SIMULATION_ID: {SIMULATION_ID}')
    log.debug(f'NODE_ID:       {NODE_ID}')

    essim_mqtt_client = ESSIMExternalModel(MQTT_HOST,
                                           MQTT_PORT,
                                           mqtt_username=MQTT_USERNAME,
                                           mqtt_password=MQTT_PASSWORD,
                                           env_essim_id=ESSIM_ID,
                                           env_simulation_id=SIMULATION_ID,
                                           env_NODE_ID=NODE_ID)
    essim_mqtt_client.connect(topic=ESSIM_TOPIC, node_id=NODE_ID)
    log.debug(f'ESSIM external model started for {NODE_ID}.')
    log.debug(f'Connected to MQTT Server {MQTT_HOST}:{MQTT_PORT} and subscribed to topic {ESSIM_TOPIC}.')
    log.debug('Waiting for messages...')
    essim_mqtt_client.loop()
