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
import sys

# Import aquanet_lib module
from __init__ import *

# Define AquaNet parameters. Note: change them according to your config
AQUANET_NODE_ID = 1     # address of local/source node
AQUANET_DEST_ID = 2     # destination address of generated messages
AQUANET_BASE_FOLDER = "/home/dmitrii/aquanet_lib"
AQUANET_MAX_PAYLOAD_SIZE_BYTES = 500    # maximum user payload allowed by AquaNet app stack


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
        # print(message_format)
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
def poisson_ms(rate):
    time_interval = random.expovariate(rate)
    return time_interval * 1000     # in milliseconds


# generate next random message
def generateMsg(src_id, seq_no, str_length):
    def generate_random_string(length):
        letters = string.ascii_letters + string.digits + string.punctuation
        return ''.join(random.choice(letters) for _ in range(length))

    # payload = "Hello, World!"
    payload = generate_random_string(str_length)

    # create a message object
    message = Message(src_id, seq_no, payload)
    return message.toBytes()

    # # Converting the bytearray back to a message object
    # reconstructed_message = Message.fromBytes(message_bytearray)
    # print(reconstructed_message.src_id)
    # print(reconstructed_message.seq_no)
    # print(reconstructed_message.payload)
    # print(reconstructed_message.crc)


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
def main(lambda_rate, msg_size):
    # initialize aquanet-stack
    aquaNetManager = AquaNetManager(AQUANET_NODE_ID, AQUANET_BASE_FOLDER)
    aquaNetManager.initAquaNet()

    # start the receive thread
    recvThread = Thread(target=receive, args=(aquaNetManager,))
    recvThread.start()

    # check if lambda is zero. If yes, do not generate any traffic, just sleep
    try:
        while lambda_rate == 0.0:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Keyboard interrupt received. Exiting gracefully.")
        aquaNetManager.stop()
        return 0

    # keep sending messages to AquaNet
    print("start sending messages to AquaNet")
    try:
        i = 0
        while True:
            msg = generateMsg(AQUANET_NODE_ID, i, msg_size)
            aquaNetManager.send(msg, AQUANET_DEST_ID)
            delay = round(poisson_ms(lambda_rate) / 1000., 2)
            print("Sending message after a delay of {} seconds.".format(delay))
            time.sleep(delay)
            i += 1
    except KeyboardInterrupt:
        print("Keyboard interrupt received. Exiting gracefully.")
        aquaNetManager.stop()

    # stop aquanet stack at the end
    recvThread.join()
    aquaNetManager.stop()
    return 0


if __name__ == '__main__':
    # Parse command line arguments
    if len(sys.argv) != 3:
        print("Usage: ./poisson_traffic <lambda_rate> <message_size_bytes>")
        sys.exit(1)
    try:
        lambda_rate = float(sys.argv[1])
        message_size_bytes = int(sys.argv[2])
    except ValueError:
        print("Invalid arguments. Lambda rate must be a float, and message size must be an integer.")
        sys.exit(1)
    if (lambda_rate < 0.0):
        print("Lambda rate must be bigger than zero.")
        sys.exit(1)
    if (message_size_bytes < 1 or message_size_bytes > AQUANET_MAX_PAYLOAD_SIZE_BYTES):
        print("Lambda rate must be bigger than zero.")
        sys.exit(1)
    # switch to listening mode only, if lambda is zero
    if (lambda_rate == 0.0):
        print("Lambda rate is set to zero. No traffic generation, only listening.")

    # run program
    main(lambda_rate, message_size_bytes)
