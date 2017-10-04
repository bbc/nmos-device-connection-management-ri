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

import os
import time
import json
import copy

from nmoscommon import timestamp as ipptimestamp
from threading import Timer
from fieldException import FieldException
from jsonschema import validate
from constants import SCHEMA_LOCAL

__location__ = os.path.realpath(
    os.path.join(os.getcwd(), os.path.dirname(__file__)))


class Activator:

    def __init__(self, targets):
        self.targets = targets
        self.scheduled = False
        self.lastRequest = {"mode": None,
                            "requested_time": None,
                            "activation_time": None}
        self.activeRequest = {
            "mode": None,
            "requested_time": None,
            "activation_time": None
        }
        self.schemaPath = SCHEMA_LOCAL

    def parseActivationObject(self, obj):
        schema = self._getSchema()
        validate(obj, schema)
        mode = obj['mode']
        if mode == "activate_immediate":
            return self._scheduleImmediate()
        else:
            schedTime = obj['requested_time']
            if mode == "activate_scheduled_absolute":
                return self._scheduleAbsolute(schedTime)
            elif mode == "activate_scheduled_relative":
                return self._scheduleRelative(schedTime)
            elif mode is None:
                return self._scheduleNone()

    def getLastRequest(self):
        return self.lastRequest

    def getActiveRequest(self):
        return self.activeRequest

    def moveToActive(self):
        """Move the last request through to active on completion
        of an activation"""
        self.activeRequest['mode'] = self.lastRequest['mode']
        self.activeRequest['activation_time'] = self.lastRequest['activation_time']
        self.activeRequest['requested_time'] = self.lastRequest['requested_time']
        self.lastRequest['mode'] = None
        self.lastRequest['requested_time'] = None
        self.lastRequest['activation_time'] = None

    def _getSchema(self):
        path = self.schemaPath + "v1.0-activate-schema.json"
        try:
            with open(path) as json_data:
                obj = json_data.read()
                return json.loads(obj)
        except EnvironmentError as e:
            raise IOError('failed to load schema file' + str(e))

    def _parseTimeString(self, timeString):
        """Convert TAI time stirng into {'seconds', 'nanoseconds'} tuple"""
        timeString = str(timeString)
        splitString = timeString.split(":")
        try:
            secs = splitString[0]
            nanos = splitString[1]
        except IndexError:
            raise FieldException("Invalid time string", "requested_time")
        try:
            intSecs = int(secs)
            intNanos = int(nanos)
        except ValueError:
            raise FieldException("Invalid time string", "requested_time")
        return [intSecs, intNanos]

    def _getCurrentTime(self):
        """Get the current time as an NMOS timestamp"""
        now = time.time()
        secs = int(now)
        nanos = (now - secs) * 1e9
        return ipptimestamp.Timestamp.from_utc(secs, nanos)

    def _scheduleImmediate(self):
        """Schedule an activation ASAP"""
        utc = self._getCurrentTime()
        for target in self.targets:
            target.activateStaged()
        toReturn = (200, {"mode": "activate_immediate",
                          "requested_time": None,
                          "activation_time": str(utc)})
        self.lastRequest = copy.deepcopy(toReturn[1])
        self.moveToActive()
        return toReturn

    def _scheduleAbsolute(self, timeString):
        """Schedule an activation against an absolute TAI time"""
        # Re-format time
        target = self._parseTimeString(timeString)
        targetTimestamp = ipptimestamp.Timestamp(target[0], target[1])
        # Get offset from current time
        utc = self._getCurrentTime()
        diff = targetTimestamp - utc
        zero = ipptimestamp.TimeOffset()
        if diff < zero:
            diff = zero
        self._scheduleActivation(diff)
        actual = utc + diff
        toReturn = (202, {"mode": "activate_scheduled_absolute",
                          "requested_time": timeString,
                          "activation_time": str(actual)})
        self.lastRequest = toReturn[1]
        return toReturn

    def _scheduleRelative(self, timeString):
        """Schedule an activation as a relative time"""
        params = self._parseTimeString(timeString)
        offset = ipptimestamp.TimeOffset(params[0], params[1])
        absTime = offset + self._getCurrentTime()
        self._scheduleActivation(offset)
        toReturn = (202, {"mode": "activate_scheduled_relative",
                          "requested_time": str(timeString),
                          "activation_time": str(absTime)})
        self.lastRequest = toReturn[1]
        return toReturn

    def _scheduleNone(self):
        """Cancel the currently scheduled activation"""
        if self.scheduled:
            self.timer.cancel()
            for target in self.targets:
                target.unLock()
            self.scheduled = False
        ret = (200, {"mode": None,
                     "requested_time": None,
                     "activation_time": None})
        self.lastRequest = ret[1]
        return ret

    def _timerCallback(self):
        for target in self.targets:
            target.activateStaged()
            target.unLock()
        self.moveToActive()
        self.scheduled = False

    def _scheduleActivation(self, timeOffset):
        for target in self.targets:
            target.lock()
        offset = float(timeOffset.to_sec_frac())
        self.scheduled = True
        self.timer = Timer(offset,  self._timerCallback)
        self.timer.start()
