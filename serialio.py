# serial port object  Rob Chapman  Jan 26, 2011

# create a serial port object which can be opened to a serial port
# input and output are done through signals and slots
# a default rate can be set
# port can be opened and closed

from pyqtapi2 import *
import sys, traceback, serial
from message import warning, error, note, message
import listports
import etmLink

class serialPort(QThread):
    # define signals
    source = pyqtSignal(object)
    ioError = pyqtSignal(object)
    ioException = pyqtSignal(object)
    closed = pyqtSignal()
    opened = pyqtSignal()
    stopbits = serial.STOPBITS_ONE
    noparity, evenparity, oddparity = serial.PARITY_NONE, serial.PARITY_EVEN, serial.PARITY_ODD
    parity = noparity
    bytesize = serial.EIGHTBITS

    def __init__(self, rate=9600):
        QThread.__init__(self)  # needed for signals to work!!
        self.port = None
        self.rate = self.default = rate
        self.inputs = 0
        self.outputs = 0

    #		initSignalCatcher()

    # shutdown signal
    def shutdown(self):
        #		note('shutting down serial port\n\r')
        self.closePort()
        self.quit()

    def run(self):  # perhaps open read and close are all in this thread
        while self.port:
            try:
                c = self.port.read(1)  # figure out why it doesn't block!!!
                c += self.port.read(self.port.inWaiting())  # get rest of chars
                self.inputs += len(c)
                if c:
                    self.source.emit(c)
            except IOError:
                self.closePort()
                # note('Alert: device removed while open ')
            except Exception, e:
                self.closePort()
                # traceback.print_exc(file=sys.stderr)
                # error("run - serial port exception: %s" % e)
        self.closed.emit()

    def open(self, port, rate=None, thread=True, timeout=.01):
        if self.isOpen():
            error("Already opened!")

        elif listports.jlink in port:
            self.name = port
            self.port = etmLink.etmLink(port.replace(listports.jlink,''))
            if self.port.findEtm():
                note('opened %s ' % (port))
                if thread:
                    self.start()  # run serial in thread
                    self.opened.emit()
            else:
                error("Could't find etm link in memory")
                self.closePort()

        else:
            if rate == None:
                self.rate = self.default
            else:
                self.rate = rate
            self.name = port
            portname = port
            try:
                self.port = serial.Serial(portname,
                                          self.rate,
                                          timeout=timeout,
                                          # time to accumulate characters: 10 ms @ 115200, thats up to 115.2 chars
                                          parity=self.parity,
                                          stopbits=self.stopbits,
                                          xonxoff=0,
                                          rtscts=0,  # hw flow control
                                          bytesize=self.bytesize)
                note('opened %s at %d' % (port, self.rate))
                if thread:
                    self.start()  # run serial in thread
                    self.opened.emit()
            except Exception, e:
                if self.port:
                    self.port.close()
                self.port = None
                print >> sys.stderr, e
                traceback.print_exc(file=sys.stderr)
                #				error('open port failed for '+prefix+port)
                raise Exception('open port failed for ' + port)

    def closePort(self):
        try:
            self.source.disconnect()
            self.closed.disconnect()
            self.ioError.disconnect()
            self.ioException.disconnect()
        except:
            pass
        if self.isOpen():
            port = self.port
            self.port = None
            try:
                port.flush()
                port.close()
            except:
                pass
            note('closed %s' % self.name)
        else:
            self.port = None

    def close(self):
        self.closePort()
        self.wait(1000)

    def sink(self, s):
        if self.isOpen():
            try:
                self.port.write(s)
                self.outputs += len(s)
            except IOError:
                self.ioError.emit('Alert: device closed while writing ')
            except Exception, e:
                if self.port:
                    self.ioException.emit("Error: sink - serial port exception: %s" % e)

    def setRate(self, rate):
        if self.rate != rate:
            note('Baudrate changed to %d' % rate)
            self.rate = rate
        if self.isOpen():
            self.port.baudrate = rate

    def isOpen(self):
        if self.port:
            return self.port.isOpen()
        return False

    # support for blocking usage
    def openBlocking(self, port, rate=None):
        self.open(port, rate, thread=False, timeout=0)

    def getc(self, n, timeout=1):
        self.port.timeout = timeout
        return self.port.read(n)

    def putc(self, data, timeout=1):
        self.port.timeout = timeout
        self.port.write(data)
