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

# import some ros-python module for serialization/deserialization
from uuv_control_msgs.msg import Waypoint


# Global parameters
VMDS_ADDR = "127.0.0.1"
VMDS_PORT = "2021"


## Class for handling send/recv communication with underlying AquaNet stack
class AquaNetManager:
    ## Constructor
    def __init__(self, nodeId, destId, baseFolder):
        self.nodeId = nodeId
        self.destId = destId
        self.baseFolder = baseFolder
        self.workingDir = baseFolder + "/tmp" + "/node" + str(self.nodeId)
        self.socketSendPath = self.workingDir + "/socket_send"
        self.socketRecvPath = self.workingDir + "/socket_recv"
        self.send_socket = 0
        self.recv_socket = 0

        # refresh working directory from previous sessions
        subprocess.Popen("rm -r " + self.workingDir, shell=True)
        subprocess.Popen("mkdir -p " + self.workingDir, shell=True)
        # create aquanet config files
        subprocess.Popen("touch " + self.workingDir + "/config_add.cfg", shell=True)
        subprocess.Popen("echo " + str(self.nodeId) + " : " + str(self.nodeId) + " > " + self.workingDir + "/config_add.cfg", shell=True)
        # copy arp, conn and route configurations
        subprocess.Popen("cp " + baseFolder + "/configs/" + "config_arp.cfg" + " " + self.workingDir, shell=True)
        subprocess.Popen("cp " + baseFolder + "/configs/" + "config_conn.cfg" + " " + self.workingDir, shell=True)
        subprocess.Popen("cp " + baseFolder + "/configs/" + "config_net.cfg" + " " + self.workingDir, shell=True)
        # copy bc-mac configuration file
        subprocess.Popen("cp " + baseFolder + "/configs/" + "aquanet-bcmac.cfg" + " " + self.workingDir, shell=True)

    ## Initialize AquaNet processes
    def initAquaNet(self):
        # create a recv_socket for receiving incoming connections from AquaNet
        self.recv_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.recv_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            # Bind the socket to the specified path
            self.recv_socket.bind(self.socketRecvPath)
            print("Socket file created and bound to the Unix domain socket.")
        except socket.error as e:
            print("Error binding the socket:", e)
            self.recv_socket.close()
            return
        self.recv_socket.listen(5)

        # start AquaNet stack
        if not self.isPortTaken(VMDS_PORT):
            print("starting local VMDS server")
            subprocess.Popen(["../../bin/aquanet-vmds", VMDS_PORT], cwd=self.workingDir)
            time.sleep(0.5)

        print("starting protocol stack...")
        subprocess.Popen(["../../bin/aquanet-stack"], cwd=self.workingDir)
        time.sleep(0.5)

        print("starting VMDM client...")
        subprocess.Popen(["../../bin/aquanet-vmdc", VMDS_ADDR, VMDS_PORT, str(self.nodeId), "0", "0", "0"], cwd=self.workingDir)
        time.sleep(0.5)

        print("starting MAC protocol...")
        subprocess.Popen(["../../bin/aquanet-bcmac"], cwd=self.workingDir)
        time.sleep(0.5)

        print("starting routing protocol...")
        subprocess.Popen(["../../bin/aquanet-sroute"], cwd=self.workingDir)
        time.sleep(0.5)

        print("starting transport layer...")
        subprocess.Popen(["../../bin/aquanet-tra"], cwd=self.workingDir)
        time.sleep(0.5)

        print("starting application layer...")
        subprocess.Popen(["../../bin/aquanet-socket-interface " + str(self.nodeId) + " " + str(self.destId) + " " + self.socketSendPath + " " + self.socketRecvPath], cwd=self.workingDir, shell=True)
        time.sleep(0.5)

        # Connect to unix socket for sending data
        self.send_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.send_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.send_socket.connect(self.socketSendPath)
        except socket.error as e:
            print("Error connecting to the socket:", e)


    ## Send to AquaNet
    def send(self, message):
        try:
            self.send_socket.sendall(message)
            print("Message sent:", message)
        except socket.error as e:
            print("Error sending data:", e)


    ## Publish ROS message to AquaNet stack, do serialization
    def publish(self, rosMsg):
        print("Publishing ROS message...")
        buff = BytesIO()
        rosMsg.serialize(buff)
        bytestring = buff.getvalue()
        serialized_msg = bytearray(bytestring)
        print("Serialized msg:", serialized_msg)
        print(type(serialized_msg))
        self.send(serialized_msg)

        # # deserialize msg
        # recvRosMsg = Waypoint()
        # recvRosMsg.deserialize(serialized_msg)
        # print("Deserialized msg:", recvRosMsg)


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
