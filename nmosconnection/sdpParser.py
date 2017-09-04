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

import re
import time
from urllib2 import urlopen, URLError
from abstractDevice import StagedLockedException


class SdpManager():

    def __init__(self, logger, receiver):
        self.stagedSdp = ""
        self.activeSdp = ""
        self.stagedSources = []
        self.activeSources = []
        self.logger = logger
        self.lastUpdated = 0
        self.stageLocked = False
        self.receiver = receiver
        self.senderId = None

        self.stagedRequest = {
            "type": "application/sdp",
            "data": ""
        }
        self.activeRequest = self.stagedRequest

    def getStagedSdp(self):
        return self.stagedSdp

    def getActiveSdp(self):
        return self.activeSdp

    def getStagedRequest(self):
        return self.stagedRequest

    def getActiveRequest(self):
        return self.activeRequest

    def lock(self):
        """Prevents any updates to staged parameters"""
        self.stageLocked = True

    def unLock(self):
        """Allows updates to staged parameters"""
        self.stageLocked = False

    def update(self, updateObject):
        """Update staged SDP if not locked"""
        if not self.stageLocked:
            try:
                data = updateObject['data']
                type = updateObject['type']
            except KeyError as err:
                # Something wrong with the request JSON
                errMessage = "Missing field in \
                PUT request to transport file:".format(str(err))
                self.logger.writeError(errMessage)
                raise KeyError(errMessage)
            if type != 'application/sdp':
                # Asked to process a transport file other than SDP
                errMessage = "This implementation of the CM API \
                cannot handle transport files of type {}:".format(type)
                self.logger.writeError(errMessage)
                raise ValueError(errMessage)
            self.stagedRequest = updateObject
            self.addSdpByAssignment(data)
            self.applyParamsToInterface()
        else:
            errMessage = "Attempted to updated parameters \
            while staged is locked"
            self.logger.writeError(errMessage)
            raise StagedLockedException(errMessage)

    def activateStaged(self):
        self.activeSdp = self.stagedSdp
        self.activeRequest = self.stagedRequest
        self.activeSources = self.stagedSources
        self.unLock()

    def applyParamsToInterface(self):
        """Apply the parameters from the
        sdp onto the interface class"""
        self.receiver._setTp(
            self.stagedSources[0]['dest'],
            'multicast_ip',
            0
        )
        self.receiver._setTp(
            self.stagedSources[0]['port'],
            'destination_port',
            0
        )
        self.receiver._setTp(
            True,
            'rtp_enabled',
            0
        )
        if 'source' in self.stagedSources[0]:
            # May not be present if not using source specific multicast
            self.receiver._setTp(
                self.stagedSources[0]['source'],
                'source_ip',
                0
            )

    def addSdpByAssignment(self, sdp):
        # Add an SDP directly
        sources = self.parseFile(sdp)
        if sources:
            self.stagedSources = sources
            self.lastUpdated = time.time()
            self.stagedSdp = sdp
            return True
        errMessage = "Could not extract sources form SDP file"
        self.logger.writeError(errMessage)
        raise SdpParseError(errMessage)

    def parseFile(self, sdpFile):
        sources = []
        lines = sdpFile.splitlines()
        for line in lines:
            result = self._parseline(line)
            type = result[0]
            if type == "c":
                if result[1] == "connection":
                    sources[-1]['dest'] = result[2][2]
                else:
                    # Failure to parse
                    self.logger.writeError("Could not parse SDP file")
                    raise(SdpParseError("Could not parse SDP line: {}")
                          .format(line))
            elif type == "m":
                source = {}
                sources.append(source)
                result = self._parseline(line)
                if result[1] == "media":
                    source['port'] = result[2][1]
                else:
                    # Failure to parse
                    self.logger.writeError("Could not parse SDP file")
                    raise(SdpParseError("Could not parse SDP line: {}")
                          .format(line))
            elif type == "a":
                if result[1] == "source-filter":
                    sources[-1]['source'] = result[2][3]
        return sources

    def _parseline(self, line):

        match = re.match("^(.)=(.*)", line)

        type, value = match.group(1), match.group(2)

        if type == "c":
            # Look for connection information - sadly sdp connection field
            # doesn't accomodate SSMC so we have to find the destination IP
            # from an source filter attribute instead
            if re.match("^ *IN +IP4 +.*$", value):
                # IPV4 Connection
                match = re.match("^ *IN +IP4 +([^/]+)(?:/(\d+)(?:/(\d+))?)? *$", value)
                ntype, atype = "IN", "IP4"
                addr, ttl, groupsize = match.groups()
                if ttl is None:
                    ttl = 127
                if groupsize is None:
                    groupsize = 1
            elif re.match("^ *IN +IP6 +.*$", value):
                # IPV6 Connection
                ntype, atype = "IN", "IP6"
                addr, groupsize = match.groups()
            else:
                # Something else?!
                return False

            return type, "connection", (ntype, atype, addr, ttl, groupsize)

        elif type == "a":
            # Looks for media attributes - I'm only interested in finding
            # source filters (RFC4570) to work out the SSMC destination address
            if re.match("^.*source-filter:incl +IN +IP4 +.*", value):
                # IPV4 Source filter
                ntype, atype = "IN", "IP4"
                match = re.match("^.*IN +IP4+ (?:((?:\d+\.?)+)) (?:((?:\d+\.?)+))", value)
                dest, source = match.groups(match)
                return type, 'source-filter', (ntype, atype, dest, source)
            elif re.match("^.*source-filter:incl +IN +IP6 +.*", value):
                # IPV6 Source filter
                ntype, atype = "IN", "IP6"
                match = re.match("^.*source-filter:incl +IN +IP6 +((?:[\dabcdefABCDEF]{1,4}:?)+) +((?:[\dabcdefABCDEF]{1,4}:?)+)", value)
                dest, source = match.groups(match)
                return type, 'source-filter', (ntype, atype, dest, source)
            else:
                return type, 'un-known', value

        elif type == "m":
            # We need to look at the media tag to get the port number to use...
            media, port, numports, protocol, fmt = re.match("^(audio|video|text|application|message) +(\d+)(?:[/](\d+))? +([^ ]+) +(.+)$",value).groups()
            port = int(port)
            if numports is None:
                numports = 1
            else:
                numports = int(numports)
            return type, 'media', (media, port, numports, protocol, fmt)

        else:
            return type, 'unknown', value


class SdpParseError(Exception):
    pass
