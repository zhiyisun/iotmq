###############################################################################
#
# The MIT License (MIT)
#
# Copyright (c) Crossbar.io Technologies GmbH
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
###############################################################################

from __future__ import print_function
from os import environ

from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks

from autobahn.twisted.wamp import ApplicationSession, ApplicationRunner

import socket
import fcntl
import struct
import subprocess
import json

USER_AND_HOST = 'zsun@120.55.171.66'

class Component(ApplicationSession):
    """
    An application component that subscribes and receives events, and
    stop after having received 5 events.
    """

    @inlineCallbacks
    def onJoin(self, details):
        print("session attached")
        self.received = 0
        sub = yield self.subscribe(self.on_event, u'com.myapp.topic1')
        print("Subscribed to com.myapp.topic1 with {}".format(sub.id))

    def getDeviceSn(self):
        # Extract serial from cpuinfo file
        device_sn = "0000000000000000"
        try:
            f = open('/proc/cpuinfo','r')
            for line in f:
                if line[0:6]=='Serial':
                    device_sn = line[10:26]
            f.close()
        except Exception as e:
            self._logger.exception(e.message)

        return device_sn


    def on_event(self, i):
        print("Got event: {}".format(i))

        # Parse data from i
        data = json.loads(i)
        if 'sn' in data and 'port' in data and data['sn'] == self.getDeviceSn():
            print("Create ssh")
            self.ssh_running(data['port'])
        else:
            print("Tear down")
            self.stop_ssh()
        # self.config.extra for configuration, etc. (see [A])
        if self.received > self.config.extra['max_events']:
            print("Received enough events; disconnecting.")
            self.leave()

    def onDisconnect(self):
        print("disconnected")
        if reactor.running:
            reactor.stop()

    def ssh_running(self, port):
        try:
            out = subprocess.check_output("pgrep -x autossh", shell=True)
            print(out)
        except subprocess.CalledProcessError as e:
            print("Running and activating autossh. Please wait for 1 minute...")
            self.run_ssh(port)

    def run_ssh(self, port):
        try:
            full_ssh_command = "autossh -f -N -R \*:{}:localhost:22 {} -oLogLevel=error  -oUserKnownHostsFile=/dev/null -oStrictHostKeyChecking=no".format(port, USER_AND_HOST)
            ssh_output = subprocess.check_output(full_ssh_command, shell=True)
            if not ssh_output:
                print("Successful")
        except subprocess.CalledProcessError as e:
            print("Failed. Please check your config file.")

    def stop_ssh(self):
        try:
            full_ssh_command = "killall autossh"
            ssh_output = subprocess.check_output(full_ssh_command, shell=True)
            if not ssh_output:
                print("Successful")
        except subprocess.CalledProcessError as e:
            print("Failed to killall autosh. Please kill it manually.")

if __name__ == '__main__':
    runner = ApplicationRunner(
        #environ.get("AUTOBAHN_DEMO_ROUTER", u"ws://127.0.0.1:8080/ws").decode('utf-8'),
        u"ws://120.55.171.66:5003/ws",
        u"iotmq",
        extra=dict(
            max_events=5,  # [A] pass in additional configuration
        ),
    )
    runner.run(Component)
