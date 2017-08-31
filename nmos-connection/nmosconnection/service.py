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

"""@package service

Top level for the connection management API when running in stand-alone mode.
Starts an instance of the HTTP server and loads the API into it.
Manages a graceful shutdown on SIGINT, SIGTERM
"""

import signal
import gevent

from nmoscommon.httpserver import HttpServer
from nmoscommon.logger import Logger as IppLogger
from api import ConnectionManagementAPI
from nmosDriver import NmosDriver
from constants import WS_PORT


class ConnectionManagementService:

    def __init__(self, logger=None):
        self.running = False
        if logger is None:
            self.logger = IppLogger("conmanage")
        self.logger.writeDebug("Running Connection Management Service")
        self.httpServer = HttpServer(ConnectionManagementAPI, WS_PORT,
                                     '0.0.0.0', api_args=[self.logger])

    def start(self):
        '''Call this to run the API without blocking'''
        if self.running:
            gevent.signal(signal.SIGINT, self.sig_handler)
            gevent.signal(signal.SIGTERM, self.sig_handler)

        self.running = True

        self.httpServer.start()

        while not self.httpServer.started.is_set():
            self.logger.writeDebug('Waiting for httpserver to start...')
            self.httpServer.started.wait()

        if self.httpServer.failed is not None:
            raise self.httpServer.failed

        self.logger.writeDebug("Running on port: {}"
                               .format(self.httpServer.port))

        # Start the mock driver
        self.driver = NmosDriver(
            self.httpServer.api,
            self.logger
        )

    def run(self):
        '''Call this to run the API in keep-alive (blocking) mode'''
        self.running = True
        self.start()
        while self.running:
            gevent.sleep(1)
        self._cleanup()

    def _cleanup(self):
        self.httpServer.stop()

    def sig_handler(self):
        self.stop()

    def stop(self):
        '''Gracefully shut down the API'''
        self._cleanup()
        self.running = False


if __name__ == '__main__':
    Service = ConnectionManagementService()
    Service.run()
