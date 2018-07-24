# support for TT over ip using UDP  Robert Chapman  Jul 24, 2018
#  inputs periodically send frames to let TT know they can be connected to

import portal
import socket
import sys, traceback
import time

sfp_udp_port = 1337
udp_poll = 5
udp_stale = 10

class udpPortal(portal.portal):
    def run(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('', sfp_udp_port))
        self.sock.settimeout(udp_poll)
        while True:
            try:
                data, address = self.sock.recvfrom(256)  # buffer size is 256 bytes
                print "address:", address, "received message:", data
                self.receive_data(data, address)
            except socket.timeout:
                self.update_port_list()
            except Exception, e:
                print >> sys.stderr, e
                traceback.print_exc(file=sys.stderr)
                print('Unknown exception, quitting udpPort')
                self.sock.close()
                break

    def receive_data(self, data, address):
        name = 'UDP port: {}'.format(address[1])
        device = self.get_device(name)
        if not device:
            device = portal.device(address, name, self)
            self.add_device(device)
        device.hold_data(data)

    def update_port_list(self):
        for device in self.devices():
            if time.time() - device.last_timestamp() > udp_stale:
                self.remove_device(device)

    def send_data(self, address, data):
        self.sock.sendto(data, address)
