# interfaces for data  Robert Chapman  Jul 26, 2018
#  input_data is defined by children
#  output is emitted by children
#  routing and coupling is provided by interface
# Define 2 layers:
#  layer1, layer2 = Layer(), Layer()
# To connect layer 1 to layer 2:
#   layer1.upper.connect(layer2.lower)
#  or
#   layer2.lower.connect(layer1.upper)
# For bottom of a stack:
#  endpoint = Bottom()
#  layer1.lower.connect(endpoint)

from pyqtapi2 import *

class Interface(QThread):
    output = Signal(object)
    input = Signal(object)

    def __init__(self):
        QThread.__init__(self)  # needed for signals to work!!
        self.normal()

    def send_data(self, data):
        pass

    def disconnect_input(self):
        try:
            self.input.disconnect()
        except:
            pass

    def loopback(self):
        self.disconnect_input()
        self.input.connect(self.output)

    def normal(self):
        self.disconnect_input()
        self.input.connect(self.send_data)

    def plugin(self, interface):
        self.unplug()
        interface.unplug()
        interface.output.connect(self.input)
        self.output.connect(interface.input)

    def unplug(self):
        try:
            self.output.disconnect()
        except:
            pass
        self.normal()

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
    def hi():
        print('hi')
    i.output.connect(hi)
    i.loopback()
    i.input.emit('')
    i.input.disconnect()

    l = Layer()
    t = Top()
    b = Bottom()
    t.plugin(l.upper)
    b.plugin(l.lower)
    l.passThrough()
    b.loopback()
    t.input.connect(hi)
    t.output.emit('')