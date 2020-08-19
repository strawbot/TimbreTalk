# test panel for qtran  Robert Chapman III  Oct 24, 2012

import protocols.interface.listports
from protocols.interface.message import *
from protocols import sfp, pids

class Monitor(QObject):
    def __init__(self, port, baud, color, format):
        QObject.__init__(self)
        self.port = port
        self.baud = baud
        self.color = color
        self.format = format

        self.listPorts()

    # get list of current ports
    # go through combobox and add and remove items for each monitor
    # check each monitor selection and if item no longer applicable, change portname to None
    def listPorts(self):
        select, disc = '(Select a Port)', '(Disconnect)'

        ports = listports.listports()
        port = self.monitors[0].port
        items = [port.itemText(i) for i in range(1, port.count())]

        for monitor in self.monitors:
            uiPort = monitor.port
            for r in list(set(items) - set(ports)):  # items to be removed
                uiPort.removeItem(uiPort.findText(r))
            for a in list(set(ports) - set(items)):  # items to be added
                uiPort.addItem(a)

            if monitor.portname:
                if monitor.portname != uiPort.currentText():
                    index = uiPort.findText(monitor.portname)
                    if index == -1:
                        index = 0
                        monitor.portname = None
                    uiPort.setCurrentIndex(index)

            text = disc if uiPort.currentIndex() else select
            if uiPort.itemText(0) != text:
                uiPort.setItemText(0, text)

        self.sptimer.singleShot(1000, self.listPorts)


# utilities
def isAscii(c):
    return c >= ' ' and c <= '~'


def toHex(c):
    return '<' + hex(ord(c))[2:] + '>'


def asciify(s):
    return ''.join([c if isAscii(c) else toHex(c) for c in s])


def hexify(s):
    return ''.join(map(lambda x: ' ' + hex(ord(x))[2:], s))


class portMonitor(QObject):

    def __init__(self, whoami, port, baud, color, format):
        QObject.__init__(self)
        self.sfp = sfp.sfpProtocol()

        self.useColor = dict(zip(["white", "cyan", "blue", "green", "yellow", "orange", "magenta", "red"],
                                 ["white", "cyan", "deepskyblue", "springgreen", "yellow", "orange", "magenta",
                                  "tomato"]))
        self.port = port
        self.baud = baud
        self.color = color.currentText
        self.format = format

        self.port.activated.connect(self.selectPort)
        self.baud.activated.connect(self.selectRate)

        self.sfp.newPacket = self.distributer
        self.serial = serialio.serialPort(int(self.baud.currentText()))
        self.portname = None
        self.whoami = whoami

    def distributer(self):  # distribute packets from queue
        if not self.sfp.receivedPool.empty():
            packet = self.sfp.receivedPool.get()
            pid = packet[0]
            if pids.pids.get(pid):
                self.text("Packet: {} {}".format(pids.pids[pid], asciify(map(chr, packet[1:]))))
            else:
                error("Unknown PID: (0x{:02x})".format(pid))

    def selectRate(self):
        self.port.setRate(int(self.baud.currentText()))

    def selectPort(self):
        if self.serial.isOpen():
            self.serial.close()
        if self.port.currentIndex():
            self.portname = self.port.currentText()
            self.serial.open(self.portname, self.serial.rate)
            if self.serial.isOpen():
                self.serial.closed.connect(self.serialDone)
                self.serial.ioError.connect(self.ioError)
                self.serial.ioException.connect(self.ioError)
                self.connectPort()
            else:
                self.port.setCurrentIndex(0)
                self.portname = None
        else:
            self.portname = None

    def serialDone(self):
        note('{}: serial thread finished'.format(self.portname))

    def ioError(self, message):
        error(message)

    def connectPort(self):  # override in children
        self.serial.source.connect(self.sink)

    def text(self, text):
        color = self.useColor[self.color()]
        message('\n{} '.format(self.whoami) + self.timestamp() + text, color)

    def sink(self, s):
        format = self.format.currentText()
        if format == 'ASCII':
            self.text(asciify(s))
        elif format == 'SFP':
            self.sfp.rxBytes(map(ord, s))
        else:
            self.text(hexify(s))

    def timestamp(self):
        return "{:.3f}: ".format(time.time())


        # monitor ports
        self.portMonitor1 = portMonitor(1,
                                        self.ui.MonitorPort1,
                                        self.ui.MonitorBaud1,
                                        self.ui.MonitorColor1,
                                        self.ui.MonitorFormat1)
        self.portMonitor2 = portMonitor(2,
                                        self.ui.MonitorPort2,
                                        self.ui.MonitorBaud2,
                                        self.ui.MonitorColor2,
                                        self.ui.MonitorFormat2)
        self.portMonitor3 = portMonitor(3,
                                        self.ui.MonitorPort3,
                                        self.ui.MonitorBaud3,
                                        self.ui.MonitorColor3,
                                        self.ui.MonitorFormat3)
        self.portMonitor4 = portMonitor(4,
                                        self.ui.MonitorPort4,
                                        self.ui.MonitorBaud4,
                                        self.ui.MonitorColor4,
                                        self.ui.MonitorFormat4)

