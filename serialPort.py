# pluggable serial port  Robert Chapman  Jul 26, 2018

from portal import *
import listports
import traceback
import serial
import time
from message import warning, error, note, message

class SerialPort(Port):
    # define signals
    stopbits = serial.STOPBITS_ONE
    noparity, evenparity, oddparity = serial.PARITY_NONE, serial.PARITY_EVEN, serial.PARITY_ODD
    parity = noparity
    bytesize = serial.EIGHTBITS

    def __init__(self, name, portal):
        Port.__init__(self, name, name, portal)
        self.port = None
        self.rate = self.default = 115200

    def run(self):
        while self.is_open():
            try:
                c = self.port.read(self.port.in_waiting)
                if c:
                    self.output.emit(c)
            except IOError:
                self.closePort()
                note('Alert: device removed while open ')
            except Exception, e:
                self.closePort()
                error("run - serial port exception: %s" % e)
                traceback.print_exc(file=sys.stderr)

    def open(self, rate=None, thread=True, timeout=.01):
        if self.is_open():
            error("Already opened!")
        else:
            self.rate = rate
            if not self.rate:
                self.rate = self.default

            try:
                self.port = serial.Serial(self.name,
                                          self.rate,
                                          timeout=timeout,
                                          # time to accumulate characters: 10 ms @ 115200, thats up to 115.2 chars
                                          parity=self.parity,
                                          stopbits=self.stopbits,
                                          xonxoff=0,
                                          rtscts=0,  # hw flow control
                                          bytesize=self.bytesize)
                note('opened %s at %d' % (self.name, self.rate))
                Port.open(self)
                if thread:
                    self.start()  # run serial port in thread
            except Exception, e:
                if self.port:
                    self.port.close()
                self.port = None
                print >> sys.stderr, e
                traceback.print_exc(file=sys.stderr)
                raise Exception('open port failed for ' + self.name)

    def closePort(self):
        Port.close(self)
        self.wait(100) # let thread finish
        self.disconnect_output()
        for signal in [self.closed, self.ioError, self.ioException]:
            try:
                signal.disconnect()
            except:
                pass

        if self.isOpen():
            try:
                self.port.flush()
                self.port.close()
            except:
                pass
            note('closed %s' % self.name)
        self.port = None

    def close(self):
        self.closePort()
        self.wait(1000)

    def send_data(self, s):
        if self.isOpen():
            try:
                self.port.write(s)
            except IOError:
                self.ioError.emit('Alert: device closed while writing ')
            except Exception, e:
                if self.port:
                    self.ioException.emit("Error: send_data - serial port exception: %s" % e)

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


class SerialPortal(Portal):
    def __init__(self, interval=5):
        self.update_interval = interval
        Portal.__init__(self)
        self.wait(100)

    def run(self):
        while True:
            ports = listports.listports()
            for name in ports:
                if not self.get_port(name):
                    port = SerialPort(name, self)
                    self.add_port(port)
            time.sleep(self.update_interval)


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
                jp = SerialPortal()
                self.port = j = jp.get_port(jp.ports()[0].name)
                j.opened.connect(self.didopen)
                j.closed.connect(self.didclose)
                j.open()
                if j.is_open():
                    print("yes its open")
                else:
                    print("port not found")

                jp.close()
            finally:
                self.quit()

    sys.exit(app().exec_())
