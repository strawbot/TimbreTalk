# interfaces for data  Robert Chapman  Jul 26, 2018
#  input is defined
#  output is called
#   inter layer connecting is done by defining an output as the others input
#  routing and coupling is provided by interface
# Define 2 layers:
#  layer1, layer2 = Layer(), Layer()
# To connect layer 1 to layer 2:
#   layer1.upper.plugin(layer2.lower)
#  or
#   layer2.lower.plugin(layer1.upper)
# For bottom of a stack:
#  endpoint = Bottom()
#  layer1.lower.plugin(endpoint)

class signal(object):
    def __init__(self, *args):
        self.disconnect()

        def emit0():  self.__signal()
        def emit1(arg):  self.__signal(arg)

        if len(args):
            self.emit = emit1
        else:
            self.emit = emit0

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
        self.unplug()
        self.name = name

    def input(self, data):
        print ("error, {}.input not defined".format(self.name))

    def output(self, data):
        pass

    def no_output(self, data):
        print ("error, {}.output unplugged".format(self.name))

    def unplug(self):
        self.output.connect(self.no_output)

    def plugin(self, plug):
        plug.output.connect(self.input.emit)
        self.output.connect(plug.input.emit)

    def loopback(self):
        def in2out(data):
            self.output.emit(data)
        self.input.connect(in2out)


class Layer(object):
    def __init__(self, name='Layer'):
        self.upper = Interface(name+'.upper')
        self.lower = Interface(name+'.lower')

    def unplug(self):
        self.upper.unplug()
        self.lower.unplug()

    def passthru(self):
        def downthru(data):
            self.lower.output.emit(data)
        self.upper.input.connect(downthru)
        def upthru(data):
            self.upper.output.emit(data)
        self.lower.input.connect(upthru)


if __name__ == "__main__":
    s = signal()
    def hi(): print('hi')
    s.connect(hi)
    s.emit()

    s = signal(object)
    def hi(data):
        print('input: {}'.format(data))
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

    t.input.emit('testt')
    b.output.connect(hi)
    b.loopback()
    b.input.emit('testl')

    t.plugin(b)
    t.output.emit('testtbl')

    l.passthru()
    b.loopback()
    t.plugin(l.upper)
    b.plugin(l.lower)

    t.output.emit('testlayer')

    t.unplug()
    l.unplug()
    b.unplug()
