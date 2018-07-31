class Interface(object):
    def __init__(self):
        self.unplug()

    def input(self, data):
        pass

    def output(self, data):
        pass

    def no_input(self, data):
        print ("error, input unplugged")

    def no_output(self, data):
        print ("error, output unplugged")

    def unplug(self):
        self.input = self.no_input
        self.output = self.no_output

    def plugin(self, plug):
        plug.input = self.output
        self.input = plug.output

    def loopback(self):
        self.output = self.input


class Layer(object):
    upper = Interface()
    lower = Interface()

    def passthru(self):
        self.upper.output = self.lower.input
        self.lower.output = self.upper.input


layer1 = Layer()
layer1.upper.input = lambda (x: print(x))
