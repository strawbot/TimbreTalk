# generic port and hub classes for TT to connect to  Robert Chapman  Jul 24, 2018

from interface import *
from time import sleep

class Port(Interface):
    nodata = ''

    def __init__(self, address=0, name=None, hub=None):
        Interface.__init__(self)
        self.address = address
        self.data = self.nodata
        self.name = name
        self.hub = hub
        self.__opened = False
        self.input.connect(self.send_data)
        self.ioError = signal()
        self.ioException = signal()
        self.closed = signal()
        self.opened = signal()
        self.signals = [self.ioError, self.ioException, self.closed, self.opened]

    def is_open(self):
        return self.__opened

    def open(self):
        self.__opened = True
        self.opened.emit()

    def close(self):
        if self.is_open():
            self.__opened = False
            self.closed.emit()

    def send_data(self, data):
        self.data += data

    def get_data(self):
        data = self.data
        self.data = self.nodata
        return data

    def wait(self, milliseconds):
        sleep(milliseconds/1000.)


class Hub(object):
    __allports = {}
    update = signal()

    def __init__(self, name='Hub'):
        self.name = name
        self.__myports = {}

    def ports(self): # some instance
        return self.__myports.values()

    def all_ports(self): # class of all hubs
        return Hub.__allports.values()

    def add_port(self, port):
        if not self.get_port(port.name):
            Hub.__allports[port.name] = port
            self.__myports[port.name] = port
            self.update.emit()

    def remove_port(self, port):
        if Hub.__allports.get(port.name):
            x = Hub.__allports.pop(port.name)
            x = self.__myports.pop(port.name)
            self.update.emit()

    def get_port(self, name):
        return Hub.__allports.get(name)

    def close(self):
        for port in self.ports():
            self.remove_port(port)
            port.close()

    def wait(self, milliseconds):
        sleep(milliseconds/1000.)


if __name__ == '__main__':
    class test(object):
        def didopen(self):
            print("port '{}' at address '{}' is open".format(self.port.name, self.port.address))

        def didclose(self):
            print("port '{}' closed".format(self.port.name))

        def test(self):
            try:
                jp = Hub()
                jp.add_port(Port(12345, 'test port', jp))
                self.port = j = jp.get_port(jp.ports()[0].name)
                j.opened.connect(self.didopen)
                j.closed.connect(self.didclose)
                j.open()
                if j.is_open():
                    print("yes its open")
                else:
                    print("port not found")
                if set(jp.all_ports()) - set(jp.ports()):
                    print("ERROR: all ports not the same as ports")
                jp.remove_port(jp.get_port(j.name))
                if len(set(jp.all_ports()).union(set(jp.ports()))) != 0:
                    print("ERROR: all ports not removed. All{}, ports {}".format(jp.all_ports(), jp.ports()))
                jp.close()
            finally:
                pass

    t = test()
    t.test()