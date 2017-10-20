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

from nmoscommon.facade import Facade
from nmoscommon import ptptime

class SimpleFacadeWrapper:

    def __init__(self, facade, deviceId):
        self.facade = facade
        self.deviceData = ""
        self.receivers = {}
        self.senders = {}
        self.flows = {}
        self.sources = {}
        self.registerDevice(deviceId)

    def registerDevice(self, deviceId):
        # Register device
        self.deviceId = deviceId
        self.deviceData = {"id": self.deviceId, "label":"example mock device", "description": "A pretend device used as part of the NMOS IS-04/05 reference implementation.", "tags": {}, "type": "urn:x-nmos:device:generic", "senders":[], "receivers":[], "\
controls": [], "max_api_version" : "v1.2" }
        self.facade.addResource("device",self.deviceId,self.deviceData)
        self.updateDevice()

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
        receiverData = {"id": receiverId, "label":"example mock receiver", "description": "A pretend receiver used as part of the NMOS IS-04/05 reference implementation.", "tags": {}, "format": "urn:x-nmos:format:video", "caps": { "media_types": ["video/raw"]}, "subscription": {"sender_id": None, "active": False}, "transport": "urn:x-nmos:transport:rtp", "interface_bindings": [ "eth0" ], "device_id": self.deviceId, "max_api_version": "v1.2"}
        self.receivers[receiverId] = receiverData
        self.facade.addResource("receiver",receiverId,receiverData)
        self.deviceData['receivers'].append(receiverId)
        self.updateReceiver(receiverId)
        self.updateDevice()

    def updateReceiver(self, receiverId):
        # Push our local copy of receiver data up, and increment version number
        timeNow = ptptime.ptp_detail()
        self.receivers[receiverId]['version'] = "{}:{}".format(repr(timeNow[0]), repr(timeNow[1]))
        self.facade.updateResource("receiver", receiverId, self.receivers[receiverId])

    def delReceiver(self, key):
        # Delete receiver
        self.facade.delResource("receiver", key)
        self.deviceData['receivers'].remove(key)
        self.receivers.pop(key)
        self.updateDevice()

    def registerSource(self, sourceId):
        # Register source
        sourceData = {"id": sourceId, "label":"example mock source", "description": "A pretend source used as part of the NMOS IS-04/05 reference implementation.", "tags": {}, "format": "urn:x-nmos:format:video", "caps": {}, "parents": [], "device_id": self.deviceId, "clock_name": "clk1", "max_api_version": "v1.2"}
        self.sources[sourceId] = sourceData
        self.facade.addResource("source",sourceId,sourceData)
        self.updateSource(sourceId)
        self.updateDevice()

    def updateSource(self, sourceId):
        # Push our local copy of receiver data up, and increment version number
        timeNow = ptptime.ptp_detail()
        self.sources[sourceId]['version'] = "{}:{}".format(repr(timeNow[0]), repr(timeNow[1]))
        self.facade.updateResource("source", sourceId, self.sources[sourceId])

    def delSource(self, key):
        # Delete source
        self.facade.delResource("source", key)
        self.sources.pop(key)
        self.updateDevice()

    def registerFlow(self, flowId, sourceId):
        # Register flow
        flowData = {"id": flowId, "label": "example mock flow", "description": "A pretend flow used as part of the NMOS IS-04/05 reference implementation.", "tags": {}, "source_id": sourceId, "device_id": self.deviceId, "parents": [], "format": "urn:x-nmos:format:video", "frame_width": 1920, "frame_height": 1080,  "colorspace" : "BT709", "max_api_version": "v1.2"}
        self.flows[flowId] = flowData
        self.facade.addResource("flow",flowId,flowData)
        self.updateFlow(flowId)
        self.updateDevice()

    def updateFlow(self, flowId):
        # Push our local copy of receiver data up, and increment version number
        timeNow = ptptime.ptp_detail()
        self.flows[flowId]['version'] = "{}:{}".format(repr(timeNow[0]), repr(timeNow[1]))
        self.facade.updateResource("flow", flowId, self.flows[flowId])

    def delFlow(self, key):
        # Delete flow
        self.facade.delResource("flow", key)
        self.flows.pop(key)
        self.updateDevice()

    def registerSender(self, senderId, flowId):
        # Register sender
        self.deviceData['senders'].append(senderId)
        senderData = {"id": senderId, "label": "example mock sender", "description": "A pretend sender used as part of the NMOS IS-04/05 reference implementation.", "tags": {}, "flow_id": flowId, "transport": "urn:x-nmos:transport:rtp", "device_id": self.deviceId, "manifest_href": "", "max_api_version": "v1.2"}
        self.senders[senderId] = senderData
        self.facade.addResource("sender",senderId,senderData)
        self.updateSender(senderId)
        self.updateDevice()

    def updateSender(self, senderId):
        # Push our local copy of receiver data up, and increment version number
        timeNow = ptptime.ptp_detail()
        self.senders[senderId]['version'] = "{}:{}".format(repr(timeNow[0]), repr(timeNow[1]))
        self.facade.updateResource("sender", senderId, self.senders[senderId])

    def delSender(self, key):
        self.facade.delResource("sender", key)
        self.senders.pop(key)
        self.deviceData['senders'].pop(key)
        self.updateDevice()
