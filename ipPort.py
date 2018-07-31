# support for TT over ip using UDP  Robert Chapman  Jul 24, 2018
#  inputs periodically send frames to let TT know they can be connected to

from portal import *
import socket
import sys, traceback
import time

sfp_udp_port = 1337
udp_poll = 2
udp_stale = 10

class UdpPort(Port):
    def __init__(self, address, name, portal):
        Port.__init__(self, address, name, portal)
        self.timestamp = time.time()

    def last_timestamp(self):
        return self.timestamp

    def send_data(self, data):
        super(UdpPort, self).send_data(data)
        self.timestamp = time.time()


class UdpPortal(Portal):
    def __init__(self):
        Portal.__init__(self, name="UdpPortal")
        self.start()

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
        port = self.get_port(name)
        if not port:
            port = UdpPort(address, name, self)
            self.add_port(port)
        port.send_data(data)

    def update_port_list(self):
        for port in self.ports():
            if time.time() - port.last_timestamp() > udp_stale:
                self.remove_port(port)

    def send_data(self, address, data):
        self.sock.sendto(data, address)


if __name__ == '__main__':
    import sys
    class app(QApplication):
        def __init__(self):
            QApplication.__init__(self, [])
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
                jp = UdpPortal()
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
