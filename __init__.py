#!/usr/bin/python3

"""
@package aquanet-lib
Created on Jun 17, 2023

@author: Dmitrii Dugaev


This module provides methods to interact with AquaNet communication stack via Unix Domain Socket interface.
"""

# Import necessary python modules from the standard library
import subprocess
import socket
import time
from io import BytesIO
import struct

# import some ros-python module for serialization/deserialization
try:
    from uuv_control_msgs.msg import Waypoint
except ImportError:
    print("Warning: ros_uuv plugin not found")

# channel emulation parameters
from emulation_config import *


# Global parameters
VMDS_ADDR = "127.0.0.1"
VMDS_PORT = "2021"
LOG_NAME = "aquanet.log"


## Class for handling send/recv communication with underlying AquaNet stack
class AquaNetManager:
    ## Constructor
    def __init__(self, nodeId, baseFolder, arm=False, gatech=False, macProto="BCMAC", trumacMaxNode=2, trumacContentionTimeoutMs=60000, trumacGuardTimeMs=100):
        self.nodeId = nodeId
        self.baseFolder = baseFolder
        self.workingDir = baseFolder + "/tmp" + "/node" + str(self.nodeId)
        self.logFilePath = self.workingDir + "/" + LOG_NAME
        self.logFile = 0
        self.socketSendPath = self.workingDir + "/socket_send"
        self.socketRecvPath = self.workingDir + "/socket_recv"
        self.send_socket = 0
        self.recv_socket = 0
        self.publishAddr = 0    # store default publishing address when using publish() method
        self.macProto = macProto  # BCMAC by default
        # default TRUMAC params
        self.trumacMaxNode = trumacMaxNode
        self.trumacContentionTimeoutMs = trumacContentionTimeoutMs
        self.trumacGuardTimeMs = trumacGuardTimeMs
        # check if ARM platform or not
        self.armFolder = ""
        if arm:
            self.armFolder = "arm/"
        # decide whether to use VMDS emulation or GATECH driver
        self.gatech = gatech

        # refresh working directory from previous sessions
        subprocess.Popen("rm -r " + self.workingDir, shell=True).wait()
        subprocess.Popen("mkdir -p " + self.workingDir, shell=True).wait()
        # create aquanet config files
        subprocess.Popen("touch " + self.workingDir + "/config_add.cfg", shell=True).wait()
        subprocess.Popen("echo " + str(self.nodeId) + " : " + str(self.nodeId) + " > " + self.workingDir + "/config_add.cfg", shell=True).wait()
        # copy arp, conn and route configurations
        subprocess.Popen("cp " + baseFolder + "/configs/" + "config_arp.cfg" + " " + self.workingDir, shell=True).wait()
        subprocess.Popen("cp " + baseFolder + "/configs/" + "config_conn.cfg" + " " + self.workingDir, shell=True).wait()
        subprocess.Popen("cp " + baseFolder + "/configs/" + "config_net.cfg" + " " + self.workingDir, shell=True).wait()
        if (self.macProto == "BCMAC"):
            # copy bc-mac configuration file
            subprocess.Popen("cp " + baseFolder + "/configs/" + "aquanet-bcmac.cfg" + " " + self.workingDir, shell=True).wait()
        elif (self.macProto == "ALOHA"):
            # aloha has no configuration file
            pass
        elif (self.macProto == "TRUMAC"):
            subprocess.Popen("touch " + self.workingDir + "/aquanet-trumac.cfg", shell=True).wait()
            # put max node_id : contention_timeout_ms : guard_time_ms parameters
            subprocess.Popen("echo " + str(self.trumacMaxNode) + " : " + str(self.trumacContentionTimeoutMs) + " : " + str(self.trumacGuardTimeMs) + " > " + self.workingDir + "/aquanet-trumac.cfg", shell=True).wait()
        else:
            print("ERROR! Unkown MAC protocol provided. Using BCMAC instead.")
            # copy bc-mac configuration file
            subprocess.Popen("cp " + baseFolder + "/configs/" + "aquanet-bcmac.cfg" + " " + self.workingDir, shell=True).wait()
            self.macProto = "BCMAC"

        # copy GATech serial interface configuration
        if self.gatech:
            subprocess.Popen("cp " + baseFolder + "/configs/" + "config_ser.cfg" + " " + self.workingDir, shell=True).wait()

    ## Initialize AquaNet processes
    def initAquaNet(self):
        # create a recv_socket for receiving incoming connections from AquaNet
        self.recv_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.recv_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            # Bind the socket to the specified path
            self.recv_socket.bind(self.socketRecvPath)
            print("socket file created and bound to the Unix domain socket.")
        except socket.error as e:
            print("error binding the socket:", e)
            self.recv_socket.close()
            return
        self.recv_socket.listen(5)

        # create log-file descriptor
        self.logFile = open(self.logFilePath, "w")

        # start AquaNet stack
        if not self.isPortTaken(VMDS_PORT) and not self.gatech:
            print("starting local VMDS server")
            subprocess.Popen(["../../bin/" + self.armFolder + "aquanet-vmds", VMDS_PORT], cwd=self.workingDir, stdout=self.logFile, stderr=self.logFile)
            time.sleep(0.5)

        print("starting protocol stack...")
        subprocess.Popen(["../../bin/" + self.armFolder + "aquanet-stack"], cwd=self.workingDir, stdout=self.logFile, stderr=self.logFile)
        time.sleep(0.5)

        if not self.gatech:
            print("starting VMDM client...")
            subprocess.Popen(["../../bin/" + self.armFolder + "aquanet-vmdc", VMDS_ADDR, VMDS_PORT, str(self.nodeId), "0", "0", "0", str(PLR), str(CHANNEL_DELAY_MS), str(CHANNEL_JITTER)], cwd=self.workingDir, stdout=self.logFile, stderr=self.logFile)
            time.sleep(0.5)
        else:
            # start interface to real modem
            print("starting GATech driver...")
            subprocess.Popen(["../../bin/" + self.armFolder + "aquanet-gatech"], cwd=self.workingDir, stdout=self.logFile, stderr=self.logFile)
            time.sleep(0.5)

        if (self.macProto == "BCMAC"):
            print("starting BCMAC MAC protocol...")
            subprocess.Popen(["../../bin/" + self.armFolder + "aquanet-bcmac"], cwd=self.workingDir, stdout=self.logFile, stderr=self.logFile)
            time.sleep(0.5)
        if (self.macProto == "ALOHA"):
            print("starting ALOHA MAC protocol...")
            subprocess.Popen(["../../bin/" + self.armFolder + "aquanet-aloha"], cwd=self.workingDir, stdout=self.logFile, stderr=self.logFile)
            time.sleep(0.5)
        if (self.macProto == "TRUMAC"):
            print("starting TRUMAC MAC protocol...")
            subprocess.Popen(["../../bin/" + self.armFolder + "aquanet-trumac"], cwd=self.workingDir, stdout=self.logFile, stderr=self.logFile)
            time.sleep(0.5)

        print("starting routing protocol...")
        subprocess.Popen(["../../bin/" + self.armFolder + "aquanet-sroute"], cwd=self.workingDir, stdout=self.logFile, stderr=self.logFile)
        time.sleep(0.5)

        print("starting transport layer...")
        subprocess.Popen(["../../bin/" + self.armFolder + "aquanet-tra"], cwd=self.workingDir, stdout=self.logFile, stderr=self.logFile)
        time.sleep(0.5)

        print("starting application layer...")
        subprocess.Popen(["../../bin/" + self.armFolder + "aquanet-socket-interface " + str(self.nodeId) + " " + self.socketSendPath + " " + self.socketRecvPath], cwd=self.workingDir, stdout=self.logFile, stderr=self.logFile, shell=True)
        time.sleep(0.5)

        # Connect to unix socket for sending data
        self.send_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.send_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.send_socket.connect(self.socketSendPath)
        except socket.error as e:
            print("Error connecting to the socket:", e)


    ## Send to AquaNet
    def send(self, message, destAddr):
        try:
            # set the destAddr first
            self.send_socket.sendall(struct.pack("<h", destAddr))
            # send the message right after
            self.send_socket.sendall(message)
            # print("Message sent:", message)
        except socket.error as e:
            print("Error sending data:", e)


    ## Publish ROS message to AquaNet stack, do serialization
    def publish(self, rosMsg):
        # print("Publishing ROS message:")
        # print(rosMsg)
        buff = BytesIO()
        rosMsg.serialize(buff)
        bytestring = buff.getvalue()
        serialized_msg = bytearray(bytestring)
        self.send(serialized_msg, self.publishAddr)

        # # deserialize msg
        # recvRosMsg = Waypoint()
        # recvRosMsg.deserialize(serialized_msg)
        # print("Deserialized msg:", recvRosMsg)

    ## Set the publishing address when using publish() method to send ros-messages
    def setPublishAddr(self, publishAddr):
        self.publishAddr = publishAddr

    ## Receive from AquaNet
    def recv(self, callback, deserialize=False):
        # Accept a client connection
        client_sock, client_addr = self.recv_socket.accept()

        # Receive data from the client
        while True:
            data = client_sock.recv(1024)
            if not data:  # If empty bytes object is received, the sender has closed the connection
                print("Sender has closed the connection.")
                break
            # Process the received data
            if deserialize:
                # print("Received msg:", data)
                # deserialize ros msg
                recvRosMsg = Waypoint()
                recvRosMsg.deserialize(data)
                print("Deserialized msg:", recvRosMsg)
                callback(recvRosMsg)
            else:
                callback(data)

        # Close the client socket
        client_sock.close()

    ## Check if specific TCP port taken, to ensure that VMDS is already running
    def isPortTaken(self, port):
        # Create a socket object
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            # Try to bind the socket to the given port
            sock.bind(('localhost', int(port)))
            return False  # Port is available
        except socket.error as e:
            if e.errno == socket.errno.EADDRINUSE:
                return True  # Port is already in use
            else:
                raise e
        finally:
            sock.close()

    ## Stop the AquaNet stack
    def stop(self):
        print("stopping aquanet...")
        subprocess.Popen(self.baseFolder + "/scripts/stack-stop.sh", shell=True)
        self.logFile.close()
