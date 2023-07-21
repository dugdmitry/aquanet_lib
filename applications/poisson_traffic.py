#!/usr/bin/python3

"""
@package aquanet-lib
Created on Jul 17, 2023

@author: Dmitrii Dugaev


This application generates and sends random messages according to Poisson distribution to AquaNet.

The app also receives incmoing messages from AquaNet and gathers info about basic TX/RX events.
Each TX/RX event is written to a trace file for further processing.
"""


from threading import Thread
import struct
import string
import random
import datetime
import time
import sys

# Import aquanet_lib module
from __init__ import *

# Define AquaNet parameters. Note: change base folder according to your config.
AQUANET_BASE_FOLDER = "/home/dmitrii/aquanet_lib"
AQUANET_MAX_PAYLOAD_SIZE_BYTES = 500    # maximum user payload allowed by AquaNet app stack

# Maintain trace-file to process TX/RX stats
TRACE_NAME = datetime.datetime.now().strftime("%d-%m-%Y-%H:%M:%S") + ".tr"
TRACE_FILE = open(TRACE_NAME, "w")

# create, serialize/deserialize a message with the following format:
# |   TIMESTAMP   | SRC_ID  | SEQ_NO  |    PAYLOAD     |   CRC    |
# |   8 Bytes     | 1 Byte  | 4 Bytes |   1-N Bytes    |  1 Byte  |
class Message:
    def __init__(self, timestamp_ms, src_id, seq_no, payload, crc=0):
        self.timestamp_ms = timestamp_ms
        self.src_id = src_id
        self.seq_no = seq_no
        self.payload = payload
        self.crc = crc

    def toBytes(self):
        payload_length = len(self.payload)
        self.crc = calculate_crc(self.timestamp_ms, self.src_id, self.seq_no, self.payload)
        message_format = '>QBI{}sB'.format(payload_length)
        # print(message_format)
        message_data = struct.pack(message_format, self.timestamp_ms, self.src_id, self.seq_no, self.payload.encode(), self.crc)
        return bytearray(message_data)

    @classmethod
    def fromBytes(self, message_bytearray):
        message_format = '>QBI'
        timestamp_ms, src_id, seq_no = struct.unpack(message_format, message_bytearray[:13])
        payload_length = len(message_bytearray[13:-1])
        payload_format = '>{}sB'.format(payload_length)
        payload, crc = struct.unpack(payload_format, message_bytearray[13:])
        payload = payload.decode()
        return Message(timestamp_ms, src_id, seq_no, payload, crc)


# calculate 1-byte crc for given message fields
def calculate_crc(timestamp_ms, src_id, seq_no, payload):
    crc_value = (timestamp_ms + src_id + seq_no + sum(ord(char) for char in payload)) % 256
    return crc_value


# return random delay in milliseconds, according to Poisson/exponential distribution
def poisson_ms(rate):
    time_interval = random.expovariate(rate)
    return time_interval * 1000     # in milliseconds


# get current timestamp in milliseconds
def getTimeMs():
    return int(time.time()*1000)


# generate next random message
def generateMsg(src_id, seq_no, str_length):
    def generate_random_string(length):
        letters = string.ascii_letters + string.digits + string.punctuation
        return ''.join(random.choice(letters) for _ in range(length))

    # payload = "Hello, World!"
    payload = generate_random_string(str_length)

    # create a message object
    time_ms = getTimeMs()
    message = Message(time_ms, src_id, seq_no, payload)
    return message.toBytes()


# receive thread
def receive(aquaNet):
    def callback(msg):
        print("Processing incoming message:", msg)
        # Converting the bytearray back to a message object
        reconstructed_message = Message.fromBytes(msg)
        print(reconstructed_message.timestamp_ms)
        print(reconstructed_message.src_id)
        print(reconstructed_message.seq_no)
        print(reconstructed_message.payload)
        print(reconstructed_message.crc)
        print(calculate_crc(reconstructed_message.timestamp_ms, reconstructed_message.src_id, reconstructed_message.seq_no, reconstructed_message.payload))

    try:
        # Receive messages from AquaNet
        print("receiving messages from AquaNet")
        aquaNet.recv(callback)
    except KeyboardInterrupt:
        print("Keyboard interrupt received. Exiting gracefully.")
        aquaNet.stop()


# init AquaNet, init receive thread, keep sending in main thread
def main(src_addr, dst_addr, lambda_rate, msg_size):
    # initialize aquanet-stack
    aquaNetManager = AquaNetManager(src_addr, AQUANET_BASE_FOLDER)
    aquaNetManager.initAquaNet()

    # check if lambda is zero. If yes, do not generate any traffic, keep listening in main thread
    if (lambda_rate == 0.0):
        print("Lambda rate is set to zero. No traffic generation, only listening.")
        receive(aquaNetManager)
        aquaNetManager.stop()
        TRACE_FILE.close()
        return 0

    # start the receive thread
    recvThread = Thread(target=receive, args=(aquaNetManager,))
    recvThread.start()

    # keep sending messages to AquaNet
    print("start sending messages to AquaNet")
    try:
        i = 0
        while True:
            msg = generateMsg(src_addr, i, msg_size)
            aquaNetManager.send(msg, dst_addr)
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
    TRACE_FILE.close()
    return 0


if __name__ == '__main__':
    # Parse command line arguments
    if len(sys.argv) != 5:
        print("Usage: ./poisson_traffic <src_addr> <dst_addr> <lambda_rate> <message_size_bytes>")
        sys.exit(1)
    try:
        src_addr = int(sys.argv[1])
        dst_addr = int(sys.argv[2])
        lambda_rate = float(sys.argv[3])
        message_size_bytes = int(sys.argv[4])
    except ValueError:
        print("Invalid arguments. Lambda rate must be a float, and message size must be an integer.")
        sys.exit(1)
    if (lambda_rate < 0.0):
        print("Lambda rate must be bigger than zero.")
        sys.exit(1)
    if (message_size_bytes < 1 or message_size_bytes > AQUANET_MAX_PAYLOAD_SIZE_BYTES):
        print("Message size must be between 1 and {} bytes.".format(AQUANET_MAX_PAYLOAD_SIZE_BYTES))
        sys.exit(1)
    if (src_addr < 1 or src_addr > 254):
        print("Source address must be in 1-254 range.")
        sys.exit(1)
    if (dst_addr < 1 or dst_addr > 255):
        print("Destination address must be in 1-255 range.")
        sys.exit(1)

    # put the command name to the first line of the trace-file
    TRACE_FILE.write(str(sys.argv) + "\n")
    TRACE_FILE.flush()

    # put the trace format to the second line
    TRACE_FILE.write("Trace format: TIMESTAMP : NODE_ID : TX-RX : SOURCE_ID : DEST_ID : SEQ_NO : PAYLOAD_SIZE : DELAY : CRC_FAILED\n")
    TRACE_FILE.flush()

    # run program
    main(src_addr, dst_addr, lambda_rate, message_size_bytes)
