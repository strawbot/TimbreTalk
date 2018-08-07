# pluggable serial port  Robert Chapman  Jul 26, 2018

from interface import *
import listports
import traceback
import serial
from message import warning, error, note, message
from threading import Thread
import sys

class SerialPort(Port):
    # define signals
    stopbits = serial.STOPBITS_ONE
    noparity, evenparity, oddparity = serial.PARITY_NONE, serial.PARITY_EVEN, serial.PARITY_ODD
    parity = noparity
    bytesize = serial.EIGHTBITS

    def __init__(self, name, hub='Serial Hub'):
        Port.__init__(self, name, name, hub)
        self.port = None
        self.rate = 115200

    def run(self):
        while self.is_open():
            try:
                c = self.port.read(1)
                if len(c):
                    c += self.port.read(self.port.in_waiting)
                    self.output.emit(c)
            # except IOError:
            #     self.closePort()
            #     note('Alert: device removed while open ')
            except Exception, e:
                self.closePort()
                error("run - serial port exception: %s" % e)
                traceback.print_exc(file=sys.stderr)

    def open(self, rate=None, thread=True, timeout=.01):
        if self.is_open():
            error("Already opened!")
        else:
            if rate:
                self.rate = rate

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
                Port.open(self)
                note('opened %s at %d' % (self.name, self.rate))
                if thread:
                    t = Thread(name=self.name, target=self.run)
                    t.setDaemon(True)
                    t.start()  # run serial port in thread
                sleep(1)
            except Exception, e:
                if self.port:
                    self.port.close()
                print >> sys.stderr, e
                traceback.print_exc(file=sys.stderr)
                raise Exception('open port failed for ' + self.name)

    def closePort(self):
        Port.close(self)
        self.wait(100) # let thread finish
        self.unplug()
        for sig in self.signals:
            sig.disconnect()

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
        self.wait(100)

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


class SerialHub(Hub):
    def __init__(self, interval=2):
        self.update_interval = interval*1000 # change to ms
        Hub.__init__(self, "SerialHub")
        self.running = True
        t = Thread(name=self.name, target=self.run)
        t.setDaemon(True)
        t.start()  # run serial hub in thread
        self.wait(100)

    def run(self):
        try:
            while self.running:
                ports = listports.listports()
                portlist = [port.name for port in self.ports()]
                for r in list(set(portlist) - set(ports)):  # items to be removed
                    self.remove_port(self.get_port(r))
                for a in list(set(ports) - set(portlist)):  # items to be added
                    port = SerialPort(a, self)
                    self.add_port(port)
                self.wait(self.update_interval)
        except Exception, e:
            print >> sys.stderr, e
            traceback.print_exc(file=sys.stderr)

    def exit(self):
        self.running = False
        self.wait(self.update_interval*1.1)
        self.close()


if __name__ == '__main__':
    from time import sleep

    class Test(object):
        def didopen(self):
            print("port '{}' at address '{}' is open".format(self.port.name, self.port.address))

        def didclose(self):
            print("port '{}' closed".format(self.port.name))

        def seeInput(self, data):
            print("Rx'd:[{}]".format(data))

        def test(self):
            try:
                jp = SerialHub()
                self.port = j = jp.get_port(jp.ports()[0].name)
                j.opened.connect(self.didopen)
                j.closed.connect(self.didclose)
                j.output.connect(self.seeInput)
                j.open()
                if j.is_open():
                    print("yes its open")
                else:
                    print("port not found")

                for i in range(20):
                    j.send_data("test string {}\n".format(i))
                sleep(.1)
                j.close()
                # jp.exit()
            except Exception, e:
                print >> sys.stderr, e
                traceback.print_exc(file=sys.stderr)
            finally:
                sys.exit(0)
    t = Test()
    t.test()