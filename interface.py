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

class signal(object):
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
        self.input = signal(object)
        self.output = signal(object)
        self.name = name
        self.input.connect(self.no_input)
        self.output.connect(self.no_output)

    def no_input(self, data):
        raise Exception("Error, {}.input not defined".format(self.name))

    def no_output(self, data):
        raise Exception("Error, {}.output unplugged".format(self.name))

    def unplug(self):
        self.output.connect(self.no_output)

    def plugin(self, inner):
        inner.output.connect(self.input.emit)
        self.output.connect(inner.input.emit)

    def loopback(self):
        def in2out(data):
            self.output.emit(data)
        self.input.connect(in2out)


class Layer(Interface):
    def __init__(self, name='Layer'):
        Interface.__init__(self, name)
        self.inner = Interface(name + '.inner')

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


if __name__ == "__main__":
    s = signal()
    def lo(): print('lo')
    s.connect(lo)
    s.emit()

    s = signal(object)
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
