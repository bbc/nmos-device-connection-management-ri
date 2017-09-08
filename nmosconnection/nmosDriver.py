# Copyright 2017 British Broadcasting Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and

# The driver is a vendor specific section of
# the software that acts an interface between
# the device being controlled and the connection
# management API. This example driver presents
# a web interface that allows mock senders and
# receivers to be presented on the API.

import os
import netifaces
import json
import random
from nmoscommon.httpserver import HttpServer
from nmoscommon.webapi import WebAPI, file_route, route, basic_route
from flask import send_from_directory, send_file, request, abort
from rtpSender import RtpSender
from rtpReceiver import RtpReceiver
from uuid import uuid4
from sdpParser import SdpManager

# Set this to change the port the API is presented on
WS_PORT = 8858


class NmosDriver:

    def __init__(self, manager, logger):
        # Start the web server used to show the interface
        self.logger = logger
        self.httpServer = HttpServer(
            NmosDriverWebApi,
            WS_PORT,
            '0.0.0.0',
            api_args=[logger, manager]
        )

        self.httpServer.start()

        while not self.httpServer.started.is_set():
            self.logger.writeDebug('Waiting for httpserver to start...')
            self.httpServer.started.wait()

        if self.httpServer.failed is not None:
            raise self.httpServer.failed

        self.logger.writeDebug("Mock driver interface running on port: {}"
                               .format(self.httpServer.port))


class NmosDriverWebApi(WebAPI):

    def __init__(self, logger, manager):
        super(NmosDriverWebApi, self).__init__()
        self.logger = logger
        self.manager = manager
        self.path = path = "/var/www/connectionManagementDriver"
        self.senders = {}
        self.receivers = {}

    @basic_route('/')
    def __index(self, path='static/index.html'):
        return send_file('{}/index.html'.format(self.path))

    @basic_route('/css/<path:path>')
    def __css(self, path):
        return send_from_directory(self.path + '/css/', path)

    @basic_route('/js/<path:path>')
    def __js(self, path):
        return send_from_directory(self.path + '/js/', path)

    @basic_route('/fonts/<path:path>')
    def __fonts(self, path):
        return send_from_directory(self.path + '/fonts/', path)

    @route('/api/')
    def _api_root(self):
        return ['senders/', 'receivers/']

    @route('/api/senders/', methods=['GET', 'POST'])
    def _api_senders(self):
        if request.method == 'GET':
            return self.manager.senders.keys()
        elif request.method == 'POST':
            try:
                data = request.get_json()
                legs = int(data['legs'])
                rtcp = data['rtcp']
                fec = data['fec']
            except KeyError:
                return abort(400)
            uuid = self.addSender(legs, rtcp, fec)
            self.senders[uuid] = data
            return {"uuid": uuid}

    @route('/api/senders/<uuid>/', methods=['GET', 'DELETE'])
    def _api_sender(self, uuid):
        if request.method == 'GET':
            try:
                return self.senders[uuid]
            except KeyError:
                abort(404)
        else:
            self.manager.removeSender(uuid)
            self.senders.pop(uuid)

    @route('/api/receivers/', methods=['GET', 'POST'])
    def _api_receivers(self):
        if request.method == 'GET':
            return self.manager.receivers.keys()
        elif request.method == 'POST':
            try:
                data = request.get_json()
                legs = int(data['legs'])
                rtcp = data['rtcp']
                fec = data['fec']
            except KeyError:
                return abort(400)
            uuid = self.addReceiver(legs, rtcp, fec)
            self.receivers[uuid] = data
            return {"uuid": uuid}
        elif request.method == 'DELETE':
            try:
                data = request.get_json()
                uuid = data['uuid']
            except KeyError:
                return abort(400)
            self.manager.removeReceiver(uuid)

    @route('/api/receivers/<uuid>/', methods=['GET', 'DELETE'])
    def _api_receiver(self, uuid):
        if request.method == 'GET':
            try:
                return self.receivers[uuid]
            except KeyError:
                abort(404)
        else:
            self.manager.removeReceiver(uuid)
            self.receivers.pop(uuid)

    def addSender(self, legs, rtcp, fec):
        sender = RtpSender(self.logger, legs)
        sender.supportRtcp(rtcp)
        sender.supportFec(fec)
        for leg in range(0,legs):
            sender.addInterface(self.generateRandomUnicast(), leg)
        sender.setDestinationSelector(self.destinationSelector)
        fileFactory = senderFileFactory(sender)
        sender.setActivateCallback(fileFactory.activateCallback)
        sender.activateStaged()
        uuid = str(uuid4())
        self.manager.addSender(sender, uuid)
        return uuid

    def addReceiver(self, legs, rtcp, fec):
        receiver = RtpReceiver(self.logger, SdpManager, legs)
        receiver.supportRtcp(rtcp)
        receiver.supportFec(fec)
        for leg in range(0,legs):
            receiver.addInterface(self.generateRandomUnicast(), leg)
        receiver.activateStaged()
        uuid = str(uuid4())
        self.manager.addReceiver(receiver, uuid)
        return uuid

    def getAvailableInterfaces(self):
        # Discover network interfaces available on the machine
        # uses the netifaces library to do heavy lifting...
        addressList = []
        interfaces = netifaces.interfaces()
        for interface in interfaces:
            addresses = netifaces.ifaddresses(interface)
            try:
                for address in addresses[netifaces.AF_INET]:
                    # Get all the IPV4 addresses presented on this interface
                    addressList.append(address['addr'])
                for address in addresses[netifaces.AF_INET6]:
                    # Get all the IPV6 addresses presented on this interface
                    addressList.append(address['addr'])
            except KeyError:
                # It's okay, you don't have to have both
                pass
        return addressList

    def destinationSelector(self, params, leg):
        return self.generateRandomMulticast()

    def generateRandomUnicast(self):
        """Generates a random unicast address. Please never ever use
        this in a production system... only for demo purposes"""
        toReturn = "192"
        for i in range(0,3):
            toReturn = toReturn + "."
            number = random.uniform(1,254)
            toReturn = toReturn + str(int(number))
        return toReturn

    def generateRandomMulticast(self):
        """Generate a random multicast address. Please don't use in a
        production system either. It would substantially increase the
        change of multicast address colission"""
        toReturn = "225"
        for i in range(0,3):
            toReturn = toReturn + "."
            number = random.uniform(1,254)
            toReturn = toReturn + str(int(number))
        return toReturn

class senderFileFactory:

    def __init__(self, interface):
        self.interface = interface
        self.groups = []

    def activateCallback(self):
        transportFile = self.generateSDP()
        self.interface.transportFile = transportFile

    def generateSDP(self):
        """Builds up an example SDP based on the stream type
        and transport parameters"""
        self.groups = []
        toReturn = ""
        toReturn = toReturn + self.generateBlockOne()
        toReturn = toReturn + self.generateRedundantGroups()
        toReturn = toReturn + self.generateFecGroups()
        toReturn = toReturn + self.generateMulticastBlock()
        toReturn = toReturn + self.generateUnicastBlock()
        toReturn = toReturn + self.generateRTCPBlock()
        toReturn = toReturn + self.generatePrimaryGroupLine()
        toReturn = toReturn + self.generate2022_5Block()
        toReturn = toReturn + self.generateRedundantBlock()
        return toReturn

    def generateBlockOne(self):
        sourceIP = self.interface.getActiveParameter("source_ip")
        return SDP_BLOCK_ONE.format(
            sourceIP
        )

    def generateMulticastBlock(self, leg=0):
        if self.checkMulticast():
            sourceIP = self.interface.getActiveParameter("source_ip", leg)
            sourcePort = self.interface.getActiveParameter("source_port", leg)
            destIP = self.interface.getActiveParameter("destination_ip", leg)
            return MULTICAST_SDP_TEMPLATE.format(
                sourcePort,
                destIP,
                destIP,
                sourceIP                
            ) + RTP_POST_ADDR
        else:
            return ""

    def generateUnicastBlock(self, leg=0):
        if not self.checkMulticast():
            sourcePort = self.interface.getActiveParameter("source_port", leg)
            destIP = self.interface.getActiveParameter("destination_ip", leg)
            return UNICAST_SDP_TEMPLATE.format(
                sourcePort,
                destIP
            ) + RTP_POST_ADDR
        else:
            return ""

    def generatePrimaryGroupLine(self):
        # If there are other groups we need to ID the primary block
        if self.checkRedundant() or self.check2022_5():
            return "\na=mid:DataStream"
        else:
            return ""

    def generateRTCPBlock(self, leg=0):
        if self.checkRtcp(leg):
            ip = self.interface.getActiveParameter("rtcp_destination_ip", leg)
            port = self.interface.getActiveParameter("rtcp_destination_port", leg)
            return "\na=rtcp:{} IN IP4 {}".format(
                port,
                ip
            )
        else:
            return ""

    def generate2022_5Block(self):
        # The behaviour of this function is based on VSF TR-04
        if self.check2022_5():
            ip = self.interface.getActiveParameter("fec_destination_ip")
            port = self.interface.getActiveParameter("fec1D_destination_port")
            return s2022_5_BLOCK.format(
                port,
                ip
            )
        else:
            return ""

    def generateRedundantBlock(self):
        if self.checkRedundant():
            toReturn = self.generateMulticastBlock(1)
            toReturn = toReturn + self.generateUnicastBlock(1)
            toReturn = toReturn + self.generateRTCPBlock(1)
            toReturn = toReturn + "\na=mid:RedundantStream"
            return toReturn
        else:
            return ""

    def generateFecGroups(self):
        if self.check2022_5():
            return "\na=group:FEC-FR DataStream FECStream"
        else:
            return ""

    def generateRedundantGroups(self):
        if self.checkRedundant():
            return "\na=group:DUP DataStream RedundantStream"
        else:
            return ""

    def checkMulticast(self):
        # This function assumes you aren't doing anything
        # odd like sending to a unicast IP on one leg and
        # a multicast leg on another...
        addr = self.interface.getActiveParameter("destination_ip")
        return 223 < int(addr.rsplit(".")[0]) < 240

    def checkRtcp(self, leg=0):
        return self.interface._enableRtcp and self.interface.getActiveParameter("rtp_enabled", leg)

    def checkRedundant(self):
        return self.interface.legs > 1 and self.interface.getActiveParameter("rtp_enabled", 1)
    
    def check2022_5(self):
        # Check to see if SMPTE2022-5 is in use. This is the only
        # FEC scheme we'll include in SDP files or it gets complicated
        # Get parameters form interface
        legs = self.interface.legs
        codeType = self.interface.getActiveParameter("fec_type")
        destPort1D = self.interface.getActiveParameter("fec1D_destination_port")
        destPort2D = self.interface.getActiveParameter("fec2D_destination_port")
        seperateStreams = destPort1D != destPort2D
        # Start to build up FEC block(s)
        if legs == 1 and seperateStreams and codeType == "XOR":
                # Looks like 2022-5 - special case which we know how to make SDPs for
                return self.interface.getActiveParameter("fec_enabled")
        return False
        # This script could be further extended to handle fec schemes that
        # aren't SMPTE2022-5. However there is little guidance as to the correct
        # formation of SDP files involving Reed Solomon, multiple FEC streams
        # or FEC for redundant media streams. This work would be outside
        # the scope of IS-05, and as such this implementation does not attempt
        # to create such SDP files.


SDP_BLOCK_ONE = """v=0
o=- 1504701982 1504701982 IN IP4 {}
s=NMOS Example Stream
t=0 0"""

MULTICAST_SDP_TEMPLATE = """
m=video {} RTP/AVP 103
c=IN IP4 {}/32
a=source-filter: incl IN IP4 {} {}"""

UNICAST_SDP_TEMPLATE = """
m=video {} RTP/AVP 103
c=IN IP4 {}"""

RTP_POST_ADDR = """
a=ts-refclk:ptp=IEEE1588-2008:08-00-11-ff-fe-21-e1-b0
a=rtpmap:103 raw/90000
a=fmtp:103 sampling=YCbCr-4:2:2; width=1920; height=1080; depth=10; colorimetry=BT709-2
a=mediaclk:direct=1595650436 rate=90000
a=framerate:25
a=extmap:1 urn:x-nmos:rtp-hdrext:origin-timestamp
a=extmap:2 urn:ietf:params:rtp-hdrext:smpte-tc 3.6e+03@90000/25
a=extmap:3 urn:x-nmos:rtp-hdrext:flow-id
a=extmap:4 urn:x-nmos:rtp-hdrext:source-id
a=extmap:5 urn:x-nmos:rtp-hdrext:grain-flags
a=extmap:7 urn:x-nmos:rtp-hdrext:sync-timestamp
a=extmap:9 urn:x-nmos:rtp-hdrext:grain-duration"""

DATA_STREAM_TAG = """
a=mid:DataStream"""

s2022_5_BLOCK = """
m=application {} RTP/AVP 99
c=IN IP4 {}/32
a=rtpmap:99 SMPTE2022-5-FEC/90000
a=fec-repair-flow: encoding-id=10
a=mid:FECStream"""
