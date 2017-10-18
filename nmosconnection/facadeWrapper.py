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
# limitations under the License.

# This class is a very simple wrapper around the full node facade interface
# used by the nmos driver to add and remove entities from the registry
# It only supports single device operation

import gevent
from gevent import Greenlet
from nmoscommon.facade import Facade
from nmoscommon import ptptime

class SimpleFacadeWrapper:

    def __init__(self, facade, deviceId):
        self.facade = facade
        self.facade.register_service("http://127.0.0.1","x-nmos/connection/")
        self.deviceData = ""
        self.receivers = []
        self.senders = []
        self.flows = []
        self.sources = []
        self.registerDevice()
        self.hearbeater = gevent.spawn(self.run)

    def registerDevice(self, deviceId):
        # Register device
        self.deviceId = deviceId
        self.deviceData = {"id": self.deviceId, "label":"example mock device", "description": "A pretend device used as part of the NMOS IS-04/05 reference implementation.", "tags": {}, "type": "urn:x-nmos:device:generic", "senders":[], "receivers":[], "\
controls": [], "max_api_version" : "v1.2" }
        self.facade.addResource("device",self.deviceId,self.deviceData)

    def updateDevice(self):
        # Push our local copy of device data up, and increment version number
        timeNow = ptptime.ptp_detail()
        self.deviceData['version'] = "{}:{}".format(repr(timeNow[0]), repr(timeNow[1]))
        self.facade.updateResource("device", self.deviceId,self.deviceData)

    def delDevice(self):
        # Remove device from registry
        self.facade.delResource("device", self.deviceId)

    def registerReceiver(self, receiverId):
        # Register receiver
        self.receivers.append(receiverId)
        receiverData = {"id": receiverId, "label":"example mock receiver", "description": "A pretend receiver used as part of the NMOS IS-04/05 reference implementation.", "tags": {}, "format": "urn:x-nmos:format:video", "caps": { "media_types": ["video/raw"]}, "subscription": {"sender_id": None, "active": False}, "transport": "urn:x-nmos:transport:rtp", "interface_bindings": [ "eth0" ], "device_id": self.deviceId, "max_api_version": "v1.2"}
        self.facade.addResource("receiver",receiverId,receiverData)
        self.deviceData['receivers'].append(receiverId)
        self.updateDevice()

    def delReceiver(self, key):
        # Delete receiver
        self.facade.delResource("receiver", key)
        self.deviceData['receivers'].remove(key)
        self.receivers.remove(key)
        self.updateDevice()

    def registerSource(self, sourceId):
        # Register source
        self.sources.append(sourceId)
        sourceData = {"id": sourceId, "label":"example mock source", "description": "A pretend source used as part of the NMOS IS-04/05 reference implementation.", "tags": {}, "format": "urn:x-nmos:format:video", "caps": {}, "parents": [], "device_id": self.deviceId, "clock_name": "clk1", "max_api_version": "v1.2"}
        self.facade.addResource("source",sourceId,sourceData)
        self.updateDevice()

    def delSource(self, key):
        # Delete source
        self.facade.delResource("source", key)
        self.sources.remove(key)
        self.updateDevice()

    def registerFlow(self, flowId, sourceId):
        # Register flow
        self.flows.append(flowId)
        flowData = {"id": flowId, "label": "example mock flow", "description": "A pretend flow used as part of the NMOS IS-04/05 reference implementation.", "tags": {}, "source_id": sourceId, "device_id": self.deviceId, "parents": [], "format": "urn:x-nmos:format:video", "frame_width": 1920, "frame_height": 1080,  "colorspace" : "BT709", "max_api_version": "v1.2"}
        self.facade.addResource("flow",flowId,flowData)
        self.updateDevice()

    def delFlow(self, key):
        # Delete flow
        self.facade.delResource("flow", key)
        self.flows.remove(key)
        self.updateDevice()

    def registerSender(self, senderId, flowId):
        # Register sender
        self.senders.append(senderId)
        self.deviceData['senders'].append(senderId)
        senderData = {"id": senderId, "label": "example mock sender", "description": "A pretend sender used as part of the NMOS IS-04/05 reference implementation.", "tags": {}, "flow_id": flowId, "transport": "urn:x-nmos:transport:rtp", "device_id": self.deviceId, "manifest_href": "", "max_api_version": "v1.2"}
        self.facade.addResource("sender",senderId,senderData)
        self.updateDevice()

    def delSender(self, key):
        self.facade.delResource("sender", key)
        self.senders.remove(key)
        self.deviceData['senders'].remove(key)
        self.updateDevice()

    def run(self):
        while True:
            self.facade.heartbeat_service()
            gevent.sleep(4)
