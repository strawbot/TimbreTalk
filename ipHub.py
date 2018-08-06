# support for TT over ip using UDP  Robert Chapman  Jul 24, 2018
#  inputs periodically send frames to let TT know they can be connected to

from hub import *
import socket
import sys, traceback, errno
import time
from threading import Thread

sfp_udp_port = 1337
udp_poll = 2
udp_stale = 10

class UdpPort(Port):
    def __init__(self, address, name, hub):
        Port.__init__(self, address, name, hub)
        self.timestamp = time.time()

    def last_timestamp(self):
        return self.timestamp

    def send_data(self, data):
        self.hub.send_data(self.address, data)
        self.timestamp = time.time()


class UdpHub(Hub):
    def __init__(self):
        Hub.__init__(self, name="UdpHub")
        t = Thread(name=self.name, target=self.run)
        t.setDaemon(True)
        t.start()  # run hub in thread

    def run(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            self.sock.bind(('192.168.0.9', sfp_udp_port))
        except socket.error as e:
            if e.errno != errno.EADDRINUSE:
                print(e)
            self.sock.close()
            return

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
                break
        self.sock.close()

    def receive_data(self, data, address):
        name = 'UDP port: {}'.format(address[1])
        port = self.get_port(name)
        if port:
            if port.is_open() and len(data):
                port.output.emit(data)
        else:
            port = UdpPort(address, name, self)
            self.add_port(port)

    def update_port_list(self):
        for port in self.ports():
            if not port.is_open():
                if time.time() - port.last_timestamp() > udp_stale:
                    self.remove_port(port)

    def send_data(self, address, data):
        self.sock.sendto(data, address)


if __name__ == '__main__':
    from PyQt4.QtCore import QCoreApplication, QTimer
    import sys
    class app(QCoreApplication):
        def __init__(self):
            QCoreApplication.__init__(self, [])
            self.timer = QTimer()
            self.timer.timeout.connect(self.test)
            self.timer.start(0)

        def didopen(self):
            print("port '{}' at address '{}' is open".format(self.port.name, self.port.address))

        def didclose(self):
            print("port '{}' closed".format(self.port.name))

        def remoteDevice(self):
            ip = '192.168.0.9'
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.sendto('helo', (ip, sfp_udp_port))
            sock.close()

        def test(self):
            try:
                jp = UdpHub()
                self.remoteDevice()
                time.sleep(udp_poll+1)
                self.port = j = jp.get_port(jp.ports()[0].name)
                j.opened.connect(self.didopen)
                j.closed.connect(self.didclose)
                j.open()
                if j.is_open():
                    print("yes its open")
                else:
                    print("port not found")

                jp.close()
            finally:
                self.quit()

    sys.exit(app().exec_())
