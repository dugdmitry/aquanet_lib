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


# Import aquanet_lib module
from __init__ import *

# Define AquaNet parameters. Note: change them according to your config
AQUANET_NODE_ID = 1     # address of local/source node
AQUANET_DEST_ID = 2     # destination address of generated messages
AQUANET_BASE_FOLDER = "/home/dmitrii/aquanet_lib"

# Define Poisson parameters
LAMBDA = 0.01       # pkts/sec


# return random delay in milliseconds, according to Poisson/exponential distribution
def poisson_ms(l):
    return 1


# generate next random message with pre-defined message format:
# | SRC_ID | SEQ_NO | RANDOM_PAYLOAD |   CRC    |
# |  1Byte | 4Bytes |   X Bytes      |  4Bytes  |
def generateMsg():
    return 0


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
