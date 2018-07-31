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
import traceback, sys

class Interface(QThread):
    output = Signal(object)
    input = Signal(object)
    verbose = False

    def __init__(self, name):
        QThread.__init__(self)  # needed for signals to work!!
        self.name = name
        self.normal()

    def send_data(self, data):
        try:
            message = "Error: '{}' unassigned send_data".format(self.name)
            raise Exception(message)
        except Exception, e:
            traceback.print_exc(file=sys.stderr)

    def disconnect_input(self):
        try:
            self.input.disconnect()
            if self.verbose: print("{}.input disconnected".format(self.name))
        except:
            pass

    def loopback(self):
        self.disconnect_input()
        self.input.connect(self.output)
        if self.verbose: print("{} input output looped".format(self.name))

    def normal(self):
        self.disconnect_input()
        self.input.connect(self.send_data, Qt.DirectConnection)
        if self.verbose: print("{} input connected to send data".format(self.name))

    def plugin(self, interface):
        self.unplug()
        interface.unplug()
        interface.output.connect(self.input, Qt.DirectConnection)
        if self.verbose: print("{} output connected to {} input".format(interface.name, self.name))
        self.output.connect(interface.input, Qt.DirectConnection)
        if self.verbose: print("{} output connected to {} input".format(self.name, interface.name))

    def unplug(self):
        try:
            self.output.disconnect()
            if self.verbose: print("{}.output disconnected".format(self.name))
        except:
            pass
        self.normal()


# perhaps bottom and top should be upper and lower or bottom and top
# should be used in Layer
class Bottom(Interface):
    pass


class Top(Interface):
    pass


class Layer(QObject):
    def __init__(self, name):
        QObject.__init__(self)  # needed for signals to work!!
        self.upper = Interface(name+'.upper')
        self.lower = Interface(name+'.lower')

    def passThrough(self):
        self.normal()
        self.upper.input.connect(self.lower.output)
        self.lower.input.connect(self.upper.output)

    def normal(self):
        self.upper.normal()
        self.lower.normal()

    def unplug(self):
        self.upper.unplug()
        self.lower.unplug()


if __name__ == "__main__":
    i = Interface('inter')
    def hi():
        print('hi')
    i.output.connect(hi)
    i.loopback()
    i.input.emit('')
    i.input.disconnect()

    l = Layer('lay')
    t = Top('top')
    b = Bottom('bot')
    t.plugin(l.upper)
    b.plugin(l.lower)
    l.passThrough()
    b.loopback()
    t.input.connect(hi)
    t.output.emit('')
    t.unplug()
    l.unplug()
    b.unplug()