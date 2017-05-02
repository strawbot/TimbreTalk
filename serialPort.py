# serial port object  Rob Chapman  Jan 26, 2011

# create a serial port object which can be opened to a serial port
# a default rate can be set
# port can be opened and closed

import serial
from inspect import currentframe, getframeinfo
import ntpath

class serialPort(object):
    stopbits = serial.STOPBITS_ONE
    noparity, evenparity, oddparity = serial.PARITY_NONE, serial.PARITY_EVEN, serial.PARITY_ODD
    parity = noparity
    bytesize = serial.EIGHTBITS

    def __init__(self, rate=9600):
        self.port = None
        self.rate = self.default = rate
        self.inputs = 0
        self.outputs = 0

    # hooks; redefine in subclass
    def rxBytes(self, bytes): # redefine to get the bytes
        print(bytes)

    def ioErrorCall(self, message):
        print(message)

    def ioExceptionCall(self, message):
        print(message)

    def closedPort(self):
        print('port closed')

    def openedPort(self):
        print('port opened')

    def note(self, message):
        print('Note: '+message)

    def error(self, message):
        print('Error: '+message)

    # shutdown signal
    def shutdown(self):
        self.closePort()
        self.quit()

    def run(self):  # perhaps open read and close are all in this thread
        while self.port:
            try:
                c = self.port.read(1)  # figure out why it doesn't block!!!
                c += self.port.read(self.port.inWaiting())  # get rest of chars
                self.inputs += len(c)
                if c:
                    self.rxBytes(list(map(ord, c)))
            except IOError:
                self.closePort()
                self.note('Alert: device removed while open ')
            except Exception as e:
                self.closePort()
        self.closedPort()

    def open(self, prefix, port, rate=None):
        if self.isOpen():
            self.error("Already opened!")
        else:
            if rate == None:
                self.rate = self.default
            else:
                self.rate = rate
            self.prefix = prefix
            self.name = port
            portname = prefix + port
            try:
                self.port = serial.Serial(portname,
                                          rate,
                                          timeout=.01,
                                          # time to accumulate characters: 10 ms @ 115200, thats up to 115.2 chars
                                          parity=self.parity,
                                          stopbits=self.stopbits,
                                          xonxoff=0,
                                          rtscts=0,  # hw flow control
                                          bytesize=self.bytesize)
                self.note('opened %s at %d' % (port, rate))
                self.openedPort()
            except Exception as e:
                if self.port:
                    self.port.close()
                self.port = None
                raise Exception('open port failed for ' + prefix + port)

    def closePort(self):
        if self.isOpen():
            port = self.port
            self.port = None
            try:
                port.flush()
                port.close()
            except:
                pass
            self.note('closed %s' % self.name)
        else:
            self.port = None

    def close(self):
        self.closePort()

    def txBytes(self, s):
        if self.isOpen():
            try:
                self.port.write(s)
                self.outputs += len(s)
            except IOError:
                self.ioErrorCall('Alert: device closed while writing ')
            except Exception as e:
                if self.port:
                    fi = getframeinfo(currentframe())
                    name = ntpath.basename(fi.filename)
                    line = fi.lineno
                    self.ioExceptionCall("Error[%s, %s]: sink - serial port exception: %s" % (name, line, e))

    def setRate(self, rate):
        if self.rate != rate:
            self.note('Baudrate changed to %d' % rate)
            self.rate = rate
        if self.isOpen():
            self.port.baudrate = rate

    def isOpen(self):
        if self.port:
            return self.port.isOpen()
        return False
