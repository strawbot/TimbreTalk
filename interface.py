# interfaces for data  Robert Chapman  Jul 26, 2018
#  input is defined
#  output is called
#   inter layer connecting is done by defining your output as the others input
#  routing and coupling is provided by interface
# Define 2 layers:
#  layer1, layer2 = Layer(), Layer()
# To connect layer 1 to layer 2:
#   layer2.inner.plugin(layer1)
# For bottom of a stack:
#  endpoint = Interface()
#  layer1.inner.plugin(endpoint)

class Signal(object):
    def __init__(self, *args):
        self.disconnect()

        def emit0():     self.__signal()
        def emit1(arg):  self.__signal(arg)

        n = len(args)
        if n == 0:
            self.emit = emit0
        elif n == 1:
            self.emit = emit1
        else:
            raise Exception("Error: No method for more than 1 argument!")

    def nothing(*args):
        pass

    def disconnect(self):
        self.__signal = self.nothing

    def connect(self, action=nothing):
        self.__signal = action


class Interface(object):
    def __init__(self, name='interface'):
        self.input = Signal(object)
        self.output = Signal(object)
        self.name = name
        self.input.connect(self.no_input)
        self.output.connect(self.no_output)
        self.signals = [self.input, self.output]

    def no_input(self, data):
        print("Error, {}.input not defined".format(self.name))

    def no_output(self, data):
        print("Error, {}.output unplugged".format(self.name))

    def unplug(self):
        self.output.connect(self.no_output)

    def plugin(self, inner):
        inner.output.connect(self.input.emit)
        self.output.connect(inner.input.emit)

    def loopback(self):
        def in2out(data):
            self.output.emit(data)
        self.input.connect(in2out)

    def disconnect(self):
        for signal in self.signals:
            signal.disconnect()


class Layer(Interface):
    def __init__(self, name='Layer'):
        Interface.__init__(self, name)
        self.inner = Interface(name + '.inner')
        self.signals += [self.inner.input, self.inner.output]

    def unplug(self):
        super(Layer, self).unplug()
        self.inner.unplug()

    def passthru(self):
        def downthru(data):  self.inner.output.emit(data)
        self.input.connect(downthru)
        def upthru(data):    self.output.emit(data)
        self.inner.input.connect(upthru)

    def plugin(self, inner):
        self.inner.plugin(inner)


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
        self.ioError = Signal()
        self.ioException = Signal()
        self.closed = Signal()
        self.opened = Signal()
        self.signals += [self.ioError, self.ioException, self.closed, self.opened]

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
    update = Signal()

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
            Hub.__allports.pop(port.name)
            self.__myports.pop(port.name)
            self.update.emit()

    def get_port(self, name):
        return Hub.__allports.get(name)

    def close(self):
        for port in self.ports():
            self.remove_port(port)
            port.close()

    def wait(self, milliseconds):
        sleep(milliseconds/1000.)


if __name__ == "__main__":
    s = Signal()
    def lo(): print('lo')
    s.connect(lo)
    s.emit()

    s = Signal(object)
    def hi(data):  print('input: {}'.format(data))
    s.connect(hi)
    s.emit('data')

    i = Interface('inter')
    i.output.connect(hi)
    i.loopback()
    i.input.emit('test1')


    t = Interface('top')
    l = Layer('lay')
    b = Interface('bot')

    t.input.connect(hi)
    t.plugin(b)
    b.loopback()
    t.output.emit('testtbl')

    t.plugin(l)
    l.plugin(b)

    l.passthru()

    t.output.emit('testlayer')

    t.unplug()
    l.unplug()
    b.unplug()

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