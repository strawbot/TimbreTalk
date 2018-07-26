# interfaces for data  Robert Chapman  Jul 26, 2018

from pyqtapi2 import *

class Interface(QThread):
    output = Signal(object)
    input = Signal(object)

    def __init__(self):
        QThread.__init__(self)  # needed for signals to work!!
        self.normal()

    def loopback(self):
        try:
            self.input.disconnect()
        except:
            pass
        self.input.connect(self.output)

    def normal(self):
        try:
            self.input.disconnect()
        except:
            pass
        self.input.connect(self.input_data)

    def input_data(self, data):
        pass


class Bottom(Interface):
    pass


class Top(Interface):
    pass


class Layer(QObject):
    def __init__(self):
        QObject.__init__(self)  # needed for signals to work!!
        self.upper = Interface()
        self.lower = Interface()

    def passThrough(self):
        self.normal()
        self.upper.input.connect(self.lower.output)
        self.lower.input.connect(self.upper.output)

    def normal(self):
        self.upper.normal()
        self.lower.normal()


if __name__ == "__main__":
    i = Interface()
    l = Layer()
    t = Top()
    b = Bottom()
    def hi():
        print('hi')
    i.output.connect(hi)
    i.loopback()
    i.input.emit('')
    i.input.disconnect()