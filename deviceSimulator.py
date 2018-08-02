import socket
from sfpLayer import SfpLayer, pids
from portal import Port
from interface import Interface
import traceback, sys
from threading import Thread
import time

sfp_udp_port = 1337
ip = '216.123.208.82'
udp_check = 2

class IpPort(Port):
    def __init__(self, address, name):
        Port.__init__(self, address, name)

    def open(self):
        Port.open(self)
        try:
            t = Thread(name=self.name, target=self.receiver)
            t.setDaemon(True)
            t.start()  # run port in thread
            self.wait(100)
        except Exception, e:
            print >> sys.stderr, e
            traceback.print_exc(file=sys.stderr)
            print('Unknown exception, not opening socket')
            Port.close(self)

    def close(self):
        Port.close(self)

    def receiver(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.sendto('', self.address) # initial send will bind to a socket and notify host
        self.sock.settimeout(udp_check)
        while self.is_open():
            try:
                data, address = self.sock.recvfrom(256)  # buffer size is 256 bytes
                self.output.emit(data)
            except socket.timeout:
                pass
            except Exception, e:
                print >> sys.stderr, e
                traceback.print_exc(file=sys.stderr)
                print('Unknown exception, quitting IpPort')
        self.sock.close()

    def send_data(self, data):
        if self.is_open():
            self.sock.sendto(data, self.address)
        else:
            print >> sys.stderr, "Error: can't send - socket is not open"

class DeviceSimulator(object):
    def __init__(self):
        self.top = Interface('DeviceSimulator')
        self.sfp = SfpLayer()
        self.bottom = IpPort((ip, sfp_udp_port), 'SfpLayer')

        self.top.plugin(self.sfp.upper)
        self.sfp.lower.plugin(self.bottom)
        self.top.input.connect(self.cli)

        self.sfp.setHandler(pids.TALK_IN, self.talkInHandler)

        self.bottom.open()

        # run keep aliver in thread
        Thread(name='DeviceSimulator', target=self.keepalive).start()

    def talkInHandler(self, packet):
        self.sfp.upper.output.emit(packet[2:])

    def sendHelo(self):
        self.bottom.send_data('helo')

    def keepalive(self):
        while self.bottom.is_open():
            self.bottom.send_data('')
            time.sleep(5)

    def cli(self, data):
        text = ''.join(map(chr, data))
        if 'exit' in text:
            self.bottom.close()
        else:
            print(text)
            self.sfp.sendNPS(pids.TALK_OUT, [self.sfp.whoto, self.sfp.whofrom]+map(ord,'\ndevsim: '))


d = DeviceSimulator()
