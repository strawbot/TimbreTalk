# generic port and portal classes for TT to connect to  Robert Chapman  Jul 24, 2018

from interface import *

class Port(Bottom):
    nodata = ''

    def __init__(self, address, name, portal):
        Bottom.__init__(self)
        self.address = address
        self.data = self.nodata
        self.name = name
        self.portal = portal
        self.__opened = False
        self.start()

    def is_open(self):
        return self.__opened

    def open(self):
        self.__opened = True

    def close(self):
        self.__opened = False

    def add_data(self, data):
        self.data += data

    def get_data(self):
        data = self.data
        self.data = self.nodata
        return data

    def send_data(self, data):
        self.portal.send_data(self.address, data)


class Portal(QThread):
    __ports = {}
    update = pyqtSignal(object)

    def __init__(self):
        QThread.__init__(self)
        self.__ports = {}
        self.start()

    def ports(self): # instance
        return self.__ports.values()

    def all_ports(self): # class
        return Portal.__ports.values()

    def add_port(self, port):
        Portal.__ports[port.name] = port
        self.__ports[port.name] = port
        self.update.emit(port)

    def remove_port(self, port):
        Portal.__ports.pop(port.name)
        self.__ports.pop(port.name)
        self.update.emit(port)

    def get_port(self, name):
        return self.__ports.get(name)
