# serial access to device through J-Link (ETM macro cell)  Robert Chapman  Jul 27, 2018

# serial IO supported through memory interfaced to by J-Link device using ETM
# memory in RAM has a data structure of:
# etm id: 0xFACEDEAF
#  ->txq: points to micros byte transmit queue; must read from here
#  ->rxq: points to mciros byte receive queue; must write to here

from portal import *
import traceback
from message import warning, error, note, message
from threading import Thread
import sys

def module_exists(module_name):
    try:
        __import__(module_name)
    except ImportError:
        return False
    else:
        return True

RAM_START, RAM_END = 0x20000000, 0x20020000

# check for ETM ports

class byteq(): #IRE
    def __init__(self, etm, a):
        if a not in range(RAM_START,RAM_END):
            raise Exception('address 0x%x is outside of RAM'%a)
        self.q = a
        self.etm = etm
        self.e = self.etm.memory_read32(a+8,1)[0]

    def ir(self):
        self.i, self.r = self.etm.memory_read32(self.q, 2)

    def push(self,n):
        self.ir()
        self.etm.memory_write8(self.q + 12 + self.i, [n])
        if self.i:
            self.i -= 1
        else:
            self.i = self.e
        self.etm.memory_write32(self.q,[self.i])

    def pull(self):
        self.ir()
        n = self.etm.memory_read8(self.q + 12 + self.r, 1)[0]
        if self.r:
            self.r -= 1
        else:
            self.r = self.e
        self.etm.memory_write32(self.q + 4,[self.r])
        return n

    def notEmpty(self):
        self.ir()
        return self.i != self.r

    def query(self):
        self.ir()
        n = self.r - self.i
        if n < 0:
            n += self.e + 1
        return n


class JlinkPort(Port):
    micro = 'EFM32GG380F1024' # make this selectable from GUI
    etmid = 0xFACEF00D

    def __init__(self, address, name, portal):
        Port.__init__(self, address, name, portal)
        self.link = portal.link
        self.etmlink = 0

    def run(self):
        while self.is_open():
            try:
                if self.inq.notEmpty():
                    text = ''
                    for i in range(20):
                        if not self.inq.notEmpty():
                            break
                        text += chr(self.inq.pull())
                    self.output.emit(text)
                else:
                    self.wait(10)
            except Exception, e:
                self.close()
                error("run - JLink port exception: %s" % e)
                traceback.print_exc(file=sys.stderr)

    def addQueues(self):
        self.inq, self.outq = [byteq(self.link, q) for q in self.link.memory_read32(self.etmlink + 4, 2)]

    def findEtm(self):
        if self.link.memory_read32(self.etmlink, 1)[0] == self.etmid:
            self.addQueues()
            return True

        n = 256
        for a in range(RAM_START, RAM_END, n):
            for b in self.link.memory_read32(a,n):
                if b == self.etmid:
                    self.etmlink = a
                    self.addQueues()
                    return True
                a += 4
        return False

    def open(self):
        self.link.open(self.address)
        try:
            self.link.set_tif(self.portal.pylink.JLinkInterfaces.SWD)
            self.link.connect(self.micro)
            self.link.restart()
            if self.link.connected():
                if self.findEtm():
                    Port.open(self)
                    t = Thread(name=self.name, target=self.run)
                    t.setDaemon(True)
                    t.start()  # run serial port in thread
                    note('opened %s' % (self.name))
        except Exception, e:
            self.link.close()
            print >> sys.stderr, e

    def send_data(self, s):
        for c in s:
            self.outq.push(ord(c))

    def close(self):
        if self.is_open():
            Port.close(self)
            self.wait(100)
            self.link.close()
            note('closed %s' % self.name)


class JlinkPortal(Portal):
    def __init__(self):
        Portal.__init__(self, "JlinkPortal")
        if module_exists('pylink'):
            import pylink
            self.link = pylink.JLink()
            self.pylink = pylink
            emulators = self.link.connected_emulators()
            portlist = [str(d.SerialNumber) for d in emulators]
            for serialno in portlist:
                if not self.get_port(serialno):
                    port = JlinkPort(serialno, 'jlink-'+serialno, self)
                    self.add_port(port)


if __name__ == '__main__':
    from PyQt4.QtCore import QCoreApplication, QTimer
    import sys
    class app(QCoreApplication):
        def __init__(self):
            QCoreApplication.__init__(self, [])
            self.timer = QTimer()
            self.timer.timeout.connect(self.test)
            self.timer.start(0)

        def didopen(self):
            print("port '{}' at address '{}' is open".format(self.port.name, self.port.address))

        def didclose(self):
            print("port '{}' closed".format(self.port.name))

        def test(self):
            try:
                jp = JlinkPortal()
                self.port = j = jp.get_port(jp.ports()[0].name)
                j.opened.connect(self.didopen)
                j.closed.connect(self.didclose)
                j.open()
                if j.is_open():
                    print("link found at 0x{:0X}".format(j.etmlink))
                else:
                    print("link not found")

                jp.close()
            finally:
                self.quit()

    sys.exit(app().exec_())

