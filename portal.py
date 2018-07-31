# generic port and portal classes for TT to connect to  Robert Chapman  Jul 24, 2018

from interface import *

class Port(Bottom):
    nodata = ''
    ioError = pyqtSignal(object)
    ioException = pyqtSignal(object)
    closed = pyqtSignal()
    opened = pyqtSignal()

    def __init__(self, address=0, name=None, portal=None):
        Bottom.__init__(self, name)
        self.address = address
        self.data = self.nodata
        self.name = name
        self.portal = portal
        self.__opened = False
        self.setObjectName(name)

    def is_open(self):
        return self.__opened

    def open(self):
        self.__opened = True
        self.opened.emit()

    def close(self):
        if self.is_open():
            self.__opened = False
            self.quit()
            self.closed.emit()

    def send_data(self, data):
        self.data += data

    def get_data(self):
        data = self.data
        self.data = self.nodata
        return data


class Portal(QThread):
    __ports = {}
    update = pyqtSignal(object)

    def __init__(self, name='Portal'):
        QThread.__init__(self)
        self.__ports = {}
        self.setObjectName(name)

    def ports(self): # instance
        return self.__ports.values()

    def all_ports(self): # class
        return Portal.__ports.values()

    def add_port(self, port):
        if not self.get_port(port.name):
            Portal.__ports[port.name] = port
            self.__ports[port.name] = port
            self.update.emit(port)

    def remove_port(self, port):
        if Portal.__ports.get(port.name):
            Portal.__ports.pop(port.name)
            self.__ports.pop(port.name)
            self.update.emit(port)

    def get_port(self, name):
        return Portal.__ports.get(name)

    def close(self):
        for port in self.ports():
            self.remove_port(port)
            port.close()
        self.quit()


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

        def test(self):
            try:
                jp = Portal()
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
                if set(jp.all_ports()).union(set(jp.ports())) == set():
                    print("ERROR: all ports not removed")

                jp.close()
            finally:
                self.quit()

    sys.exit(app().exec_())
