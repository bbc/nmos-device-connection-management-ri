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
