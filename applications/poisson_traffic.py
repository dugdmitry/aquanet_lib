#!/usr/bin/python3

"""
@package aquanet-lib
Created on Jul 17, 2023

@author: Dmitrii Dugaev


This application generates and sends random messages according to Poisson distribution to AquaNet.

The app also receives incmoing messages from AquaNet and gathers basic statistics:
- Packet Delivery Ratio (PDR): percentage of delivered messages vs. total number of sent messages;
- Throughput: current inbound data rate;
- Delay: end-to-end packet latency, i.e. how long it took for a packet to get received by destination.
"""


from threading import Thread
import struct
import string
import random


# Import aquanet_lib module
from __init__ import *

# Define AquaNet parameters. Note: change them according to your config
AQUANET_NODE_ID = 1     # address of local/source node
AQUANET_DEST_ID = 2     # destination address of generated messages
AQUANET_BASE_FOLDER = "/home/dmitrii/aquanet_lib"

# Define Poisson parameters
LAMBDA = 0.01       # pkts/sec


# create, serialize/deserialize a message with the following format:
# | SRC_ID | SEQ_NO |    PAYLOAD     |   CRC   |
# |  1Byte | 4Bytes |   1-N Bytes    |  1Byte  |
class Message:
    def __init__(self, src_id, seq_no, payload, crc=0):
        self.src_id = src_id
        self.seq_no = seq_no
        self.payload = payload
        self.crc = crc

    def calculate_crc(self):
        crc_value = (self.src_id + self.seq_no + sum(ord(char) for char in self.payload)) % 256
        return crc_value

    def toBytes(self):
        payload_length = len(self.payload)
        self.crc = self.calculate_crc()
        message_format = '>BI{}sB'.format(payload_length)
        print(message_format)
        message_data = struct.pack(message_format, self.src_id, self.seq_no, self.payload.encode(), self.crc)
        return bytearray(message_data)

    @classmethod
    def fromBytes(self, message_bytearray):
        message_format = '>BI'
        src_id, seq_no = struct.unpack(message_format, message_bytearray[:5])
        payload_length = len(message_bytearray[5:-1])
        payload_format = '>{}sB'.format(payload_length)
        payload, crc = struct.unpack(payload_format, message_bytearray[5:])
        return Message(src_id, seq_no, payload, crc)

# return random delay in milliseconds, according to Poisson/exponential distribution
def poisson_ms(l):
    return 1000


# generate next random message
def generateMsg(src_id, seq_no, str_length):
    def generate_random_string(length):
        letters = string.ascii_letters + string.digits + string.punctuation
        return ''.join(random.choice(letters) for _ in range(length))

    # payload = "Hello, World!"
    payload = generate_random_string(str_length)

    # Creating a message object
    message = Message(src_id, seq_no, payload)

    # Converting the message to a bytearray
    message_bytearray = message.toBytes()
    print(message_bytearray)
    print(len(message_bytearray))

    # Converting the bytearray back to a message object
    reconstructed_message = Message.fromBytes(message_bytearray)
    print(reconstructed_message.src_id)
    print(reconstructed_message.seq_no)
    print(reconstructed_message.payload)
    print(reconstructed_message.crc)


# receive thread
def receive(aquaNet):
    def callback(msg):
        print("Callback on received msg:", msg)

    try:
        # Receive messages from AquaNet
        print("receiving messages from AquaNet")
        aquaNet.recv(callback)
    except KeyboardInterrupt:
        print("Keyboard interrupt received. Exiting gracefully.")
        aquaNet.stop()


# init AquaNet, init receive thread, keep sending in main thread
def main():
    # initialize aquanet-stack
    aquaNetManager = AquaNetManager(AQUANET_NODE_ID, AQUANET_BASE_FOLDER)
    aquaNetManager.initAquaNet()

    # start the receive thread
    recvThread = Thread(target=receive, args=(aquaNetManager,))
    recvThread.start()

    # keep sending messages to AquaNet
    print("start sending messages to AquaNet")
    try:
        i = 0
        while True:
            generateMsg(AQUANET_NODE_ID, i, 44)
            aquaNetManager.send(("hello: " + str(i)).encode(), AQUANET_DEST_ID)
            time.sleep(1)
            i += 1
    except KeyboardInterrupt:
        print("Keyboard interrupt received. Exiting gracefully.")
        aquaNetManager.stop()

    # stop aquanet stack at the end
    recvThread.join()
    aquaNetManager.stop()


if __name__ == '__main__':
    main()
