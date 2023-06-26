# aquanet_lib

Python library to interface with AquaNet stack of protocols.

## Usage

Clone `aquanet_lib` repository to your working directory:

    git clone https://github.com/dugdmitry/aquanet_lib.git

Import `aquanet_lib` module to your python program:

    import aquanet_lib

To initialize AquaNet stack and start sending/receiving messages, use the following code:

    ## Initialize aquanet-manager
	nodeAddr = 1    # your local node address
	destAddr = 2    # destination node address
	baseFolder = "/home/user/ros_catkin_ws/src/multi_auv_sim/scripts/backup/aquanet_lib"    # base folder of your scripting program
    # create the manager object
	aquaNetManager = aquanet_lib.AquaNetManager(nodeAddr, destAddr, baseFolder)
    # initialize aquanet stack
    aquaNetManager.initAquaNet()

    # to send messages
    aquaNetManager.send(("hello".encode())

    # to receive messages
    aquaNetManager.recv(recv_callback)

Now, you can send/receive messages over aquanet-stack using `send()`, `publish()` and `recv()` methods. The basic send and receive examples can be found under `examples` folder.

## Example 1: run basic send-receive operation

    cd examples/

The following scripts will instantiate 2 AquaNet nodes with `1` and `2` network addresses. `Node 1` will be periodically sending `hello` messages to `Node 2`.

Run receive-example script:

    ./receiver_example.py

You should see the following lines at the end of the output:

```
----------------------------------------------------------
		AQUANET-SOCKET-INTERFACE 
The socket-interface application for Aqua-Net
Developed by Dmitrii Dugaev
All rights reserved
----------------------------------------------------------

X:2:2-24210126>[socket-interface]	Starting AQUANET-SOCKET-INTERFACE.
X:2:2-24210126>[     stack]	Application Module Connected.
X:2:2-24210126>[socket-interface]	unix-domain socket created and listening for incoming connections
receiving messages from AquaNet
```

In another terminal, run sender-example script:

    ./sender_example.py

The script will start sending `hello` messages periodically:

```
X:1:1-24210132>[socket-interface]	Starting AQUANET-SOCKET-INTERFACE.
X:1:1-24210132>[socket-interface]	unix-domain socket created and listening for incoming connections
X:1:1-24210132>[     stack]	Application Module Connected.
sending messages to AquaNet
X:1:1-24210133>[socket-interface]	Client connected. Receiving data...
Message sent: b'hello: 0'
X:1:1-24210133>[socket-interface]	received from unix-socket: hello: 0
X:1:1-24210133>[socket-interface]	sending 8 bytes from 1 to 2
X:1:1-24210133>[     stack]	Got 1 connection.
X:1:1-24210133>[     stack]	Received 8 bytes from app layer
X:1:1-24210133>[       tra]	received 8 bytes
X:1:1-24210133>[     stack]	Got 1 connection.
X:1:1-24210133>[     stack]	Received 12 bytes from tra layer
X:1:1-24210133>[    sroute]	Received 12 bytes
X:1:1-24210133>[    sroute]	Next Hop for 2: Node 2
X:1:1-24210133>[     stack]	Got 1 connection.
X:1:1-24210133>[     stack]	Received 22 bytes from net layer
X:1:1-24210133>[     bcmac]	Node 1 : Get Packet from upper layer & cache it
X:1:1-24210133>Node 1 : Send Packet in 0 seconds 13400 microseconds
X:1:1-24210133>[     stack]	Got 1 connection.
X:1:1-24210133>[     stack]	Received 32 bytes from mac layer
X:1:1-24210133>[      vmdc]	Got 1 connection
X:1:1-24210133>[      vmdc]	Got packets from the protocol stack
X:1:1-24210133>[      vmdc]	received 664 bytes from protocol stack:hello: 0
X:1:1-24210133>[      vmdc]	modem_send: sent 664 bytes
```

At the receiver-end, the messages should start appearing in the console output:

```
X:2:2-24210127>[socket-interface]	Client connected. Receiving data...
X:2:2-24210130>[      vmds]	New connection from 127.0.0.1 on socket 5
X:2:2-24210133>[      vmds]	received 664 bytes from socket 5
X:2:2-24210133>[      vmds]	sent 664 bytes to socket 4
X:2:2-24210133>[      vmdc]	Got 1 connection
X:2:2-24210133>[      vmdc]	Got packets from the virtual modem
X:2:2-24210133>[      vmdc]	modem_recv: received 664 bytes: hello: 0
X:2:2-24210133>[      vmdc]	received 664 bytes from serial port:hello: 0
X:2:2-24210133>[     stack]	Got 1 connection.
X:2:2-24210133>[     stack]	Received 664 bytes from phy layer
X:2:2-24210133>Node 2 : Get Packet from node 1 & send it to upper layer
X:2:2-24210133>[     stack]	Got 1 connection.
X:2:2-24210133>[     stack]	Received 22 bytes from mac layer
X:2:2-24210133>[    sroute]	Received 22 bytes
X:2:2-24210133>[    sroute]	It's for me, receive it
X:2:2-24210133>[     stack]	Got 1 connection.
X:2:2-24210133>[     stack]	Received 22 bytes from net layer
X:2:2-24210133>[       tra]	received 12 bytes
X:2:2-24210133>[     stack]	Got 1 connection.
X:2:2-24210133>[     stack]	Received 12 bytes from tra layer

X:2:2-24210133>[socket-interface]	received from 1 to 2: hello: 0
Callback on received msg: b'hello: 0'
```

## Example 2: run swarm-tracing algoithm in Gazebo+UUV simulator

To run this example, Gazebo and ROS+UUV simulator should be installed. Also, make sure that `uuv_plume_simulator` and `multi_auv_sim` packages are installed in ROS environment. See more details here:

ROS installation:

http://wiki.ros.org/noetic/Installation/Ubuntu

UUV+Gazebo instllation:

https://uuvsimulator.github.io/installation/

`uuv_plume_simulator` package info:

https://uuvsimulator.github.io/packages/uuv_plume_simulator/intro/

In `examples/uuv` folder, you can find examples of the modified `leader.py` and `node2.py` scripts alongisde with necessary launch files to run a plume-tracing scenario. The communication between `leader` and `node2` is conducted over AquaNet stack using `aquanet_lib` library.

Step 1: Run ROV simulation:

    roslaunch multi_auv_sim multi_rov_test.launch

RViz window should appear, visualizing 5 ROVs. The communication over AquaNet is established in 1-way unicast way from `leader` to `node2`.

Step 2: Run plume-tracing script:

    roslaunch multi_auv_sim start_mbplume.launch

You should see the following output in the terminal, indicating that `aquanet_lib` has published a ROS message from `leader` towards `node2`:

```
Publishing ROS message:
header: 
  seq: 0
  stamp: 
    secs: 80
    nsecs: 990000000
  frame_id: "world"
point: 
  x: 20
  y: 25
  z: -3.34947309796
max_forward_speed: 0.75
heading_offset: 0.0
use_fixed_heading: False
radius_of_acceptance: 0.0
```    

and successfully received/deserialized the ROS-message at `node2`:

```
user-gazebo:2:2-26085825>[socket-interface]	received from 1 to 2: 
('Received msg:', '\x00\x00\x00\x00\x99\x00\x00\x00\x00\xab\x87\x04\x05\x00\x00\x00world\x1c2\xf5w\x1c\x90Q\xc0\xfa\xb0\x8e\xfb\xd5pP\xc0I`%_\x1d\xd1\t\xc0\x00\x00\x00\x00\x00\x00\xe8?\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
('Deserialized msg:', header: 
  seq: 0
  stamp: 
    secs: 153
    nsecs:  76000000
  frame_id: "world"
point: 
  x: -70.2517375845
  y: -65.7630604642
  z: -3.22710680325
max_forward_speed: 0.75
heading_offset: 0.0
use_fixed_heading: False
radius_of_acceptance: 0.0)
Algorithm state: Find
```

## Current limitations

### Limitation 1:

Only one-way unicast communication is currently supported. When intializing AquaNet stack via `AquanetManager`, a user must specify the sender address and the destination address. So, the communication is established in 1-way direction from single sender to single receiver.

The support for 2-way unicast and broadcast (1 to many) communication is currently a work in progress.

### Limitation 2:

No underwater channel emulation implemented yet. When packets are sent from one node to another, they pass through the `AquaNet-VMDS` process that interconnects multiple aquanet instances together. Currently, this process just forwards packets to the receivers without introducing channel `delay`, `jitter` or `packet loss`.

This chanel emulation feature is to be implemented in the upcoming versions.

## Troubleshooting

The software is still very experimental and in the early stage of development. There might be significant changes done to both the program design and user interfaces in the future.

Thus, please be aware that the software may crash or become unresponsive. When this happens, please follow the following general algorithm:

1) Stop all the sender/receiver scripts that you're running. E.g., `sender_example.py` script, `leader.py`, `node2.py`, `start_mbplume.launch` and `multi_rov_test.launch` files, etc.

2) In a separate terminal, kill all the AquaNet-related processes by executing `scripts/stack-stop.sh` script.

3) Wait at least 30 seconds before launching the programs a second time. This is needed to give time to a Linux system to unlink the unix- and tcp- sockets used by the previous AquaNet processes. Otherwise, a socket connection to AquaNet VMDS server might fail.

4) Restart your experiments. Repeat.

In the event of a crash or non-functional behavior, please save all the console outputs and send a bug-report to the developer.
