# monitor ports

from qt import QtCore
import bisect

def listsDiffer(a, b):
    if len(a) == len(b):
        for x, y in zip(a, b):
            if x != y:
                return True
        return False
    return True


def updatePortCombo(uiPort, ports):
    initial = items = [uiPort.itemText(i) for i in range(1, uiPort.count())]

    for r in list(set(items) - set(ports)):  # items to be removed
        uiPort.removeItem(uiPort.findText(r))
        if r in items:  items.remove(r)
    for a in list(set(ports) - set(items)):  # items to be added
        bisect.insort(items, a)
        uiPort.insertItem(1 + items.index(a), a)

    # set item zero
    text = '(Disconnect)' if uiPort.currentIndex() else '(Select a Port)'
    if uiPort.itemText(0) != text:
        uiPort.setItemText(0, text)


class portMonitor(QtCore.QObject):
    ports = []
    portlist = []
    monitorOut = QtCore.pyqtSignal(object,object)

    def __init__(self, port, baud, name, protocol, color):
        QtCore.QObject.__init__(self)
        print(port.objectName())
        portMonitor.ports.append(self)
        self.port = port
        self.baud = baud
        self.tag = name
        self.protocol = protocol
        self.color = color

    def out(self, text):
        full = '\n123.456ms ' + self.tag.text() + ': ' + text
        self.monitorOut.emit(full, self.color.currentText())

    @classmethod
    def updatePortList(cls, portlist):
        if listsDiffer(cls.portlist, portlist):
            for self in cls.ports:
                updatePortCombo(self.port, portlist)
                self.out('port list updated')
            cls.portlist = portlist






        # self.ui.PortSelect.activated.connect(self.selectPort)
        # self.ui.SetSerial.clicked.connect(self.setSerial)
        # self.ui.SetSfp.clicked.connect(self.setSfp)
        # self.ui.SetSfp.click()
        # self.ui.BaudRate.activated.connect(self.selectRate)
        # self.ui.BaudRate.currentIndexChanged.connect(self.selectRate)
        # self.ui.ConsoleColor.activated.connect(self.setColor)
        #

    #     # self.sfp = sfp.sfpProtocol()
    #     #
    #     # self.useColor = dict(zip(["white", "cyan", "blue", "green", "yellow", "orange", "magenta", "red"],
    #     #                          ["white", "cyan", "deepskyblue", "springgreen", "yellow", "orange", "magenta",
    #     #                           "tomato"]))
    #     # self.port = port
    #     # self.baud = baud
    #     # self.color = color.currentText
    #     # self.format = format
    #     #
    #     # self.port.activated.connect(self.selectPort)
    #     # self.baud.activated.connect(self.selectRate)
    #     #
    #     # self.sfp.newPacket = self.distributer
    #     # self.serial = serialio.serialPort(int(self.baud.currentText()))
    #     # self.portname = None
    #     # self.whoami = whoami
    #
    # def distributer(self):  # distribute packets from queue
    #     if not self.sfp.receivedPool.empty():
    #         packet = self.sfp.receivedPool.get()
    #         pid = packet[0]
    #         if pids.pids.get(pid):
    #             self.text("Packet: {} {}".format(pids.pids[pid], asciify(map(chr, packet[1:]))))
    #         else:
    #             error("Unknown PID: (0x{:02x})".format(pid))
    #
    # def selectRate(self):
    #     self.port.setRate(int(self.baud.currentText()))
    #
    # def selectPort(self):
    #     if self.serial.isOpen():
    #         self.serial.close()
    #     if self.port.currentIndex():
    #         self.portname = self.port.currentText()
    #         self.serial.open(self.portname, self.serial.rate)
    #         if self.serial.isOpen():
    #             self.serial.closed.connect(self.serialDone)
    #             self.serial.ioError.connect(self.ioError)
    #             self.serial.ioException.connect(self.ioError)
    #             self.connectPort()
    #         else:
    #             self.port.setCurrentIndex(0)
    #             self.portname = None
    #     else:
    #         self.portname = None
    #
    # def serialDone(self):
    #     note('{}: serial thread finished'.format(self.portname))
    #
    # def ioError(self, message):
    #     error(message)
    #
    # def connectPort(self):  # override in children
    #     self.serial.source.connect(self.sink)
    #
    # def text(self, text):
    #     color = self.useColor[self.color()]
    #     message('\n{} '.format(self.whoami) + self.timestamp() + text, color)
    #
    # def sink(self, s):
    #     format = self.format.currentText()
    #     if format == 'ASCII':
    #         self.text(asciify(s))
    #     elif format == 'SFP':
    #         self.sfp.rxBytes(map(ord, s))
    #     else:
    #         self.text(hexify(s))
    #
    # def timestamp(self):
    #     ms = current_milli_time()
    #     return "%d.%03d: " % (ms / 1000, ms % 1000)
