#!/usr/bin/python3

"""
@package aquanet-lib
Created on Jun 17, 2023

@author: Dmitrii Dugaev


This is an example how to initialize and send user messages over aquanet-lib and AquaNet stack
"""

# Import aquanet_lib module
from __init__ import *


def main():
    # Initialize aquanet-stack
    nodeAddr = 2
    destAddr = 1
    baseFolder = "/home/dmitrii/aquanet_lib"
    aquaNetManager = AquaNetManager(nodeAddr, destAddr, baseFolder)
    aquaNetManager.initAquaNet()

    try:
        # Receive messages from AquaNet
        print("receiving messages from AquaNet")
        aquaNetManager.recv()

    except KeyboardInterrupt:
        print("Keyboard interrupt received. Exiting gracefully.")
        aquaNetManager.stop()


if __name__ == '__main__':
    main()
