# monitor ports

from qt import QtCore
import bisect
import time
import traceback

from protocols.interface import interface, serialHub
from protocols.sfpLayer import SfpLayer
from protocols import pids
from threading import Thread
from protocols.interface.message import *

# tools
def current_milli_time():
    return int(round(time.time() * 1000))

def timestamp():
    return "%.3f: " % (current_milli_time()/1000)

from datetime import datetime, timezone
datetime.now(timezone.utc).strftime("%Y%m%d")

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


# utilities
def isAscii(c):
    if type(c) == type('0'):
        c = ord(c)
    return ord(' ') <= c <= ord('~')

def toHex(c):
    if type(c) == type('0'):
        c = ord(c)
    return '<{:02X}>'.format(c)

def asciify(s):
    text = [chr(c) if isAscii(c) else toHex(c) for c in s]
    return ''.join(text)

def hexify(s):
    return ''.join(map(lambda x: ' ' + hex(x)[2:], s))


# common class for all port monitors; class keeps list of instances
class portMonitor(QtCore.QObject):
    ports = []
    portlist = []
    monitorOut = QtCore.pyqtSignal(object,object)

    @classmethod
    def updatePortList(cls, portlist):
        if listsDiffer(cls.portlist, portlist):
            for self in cls.ports:
                updatePortCombo(self.uiport, portlist)
                self.out('port list updated')
            cls.portlist = portlist

    def __init__(self, port, baud, name, protocol, color):
        QtCore.QObject.__init__(self)
        print(port.objectName())
        portMonitor.ports.append(self)

        self.uiport = port
        self.uibaud = baud
        self.uitag = name
        self.uiprotocol = protocol
        self.uicolor = color

        self.serialHub = serialHub.SerialHub()
        self.top = interface.Interface('terminal')
        self.protocol = SfpLayer()
        self.top.plugin(self.protocol)
        self.noMoniPort()
        self.inner = interface.Interface('ttt')
        self.inner.input.connect(self.send_data)

        self.uiport.activated.connect(self.selectPort)
        self.uibaud.activated.connect(self.selectRate)

        self.messages(messageQueue())

    def out(self, text):
        full = '\n%s' % timestamp() + self.uitag.text() + ': ' + text
        self.monitorOut.emit(full, self.uicolor.currentText())

    def send_data(self, text):
        text_type = type(text)
        if text_type == type((0,)):
            print('type tuple of type',type(text[0]))
            self.monitorOut.emit(*text)
        else:
            print('type ',type(text), text)
            self.out(asciify(text))

    def messages(self, q): # handle messages piped in from other threads
        class messageThread(QtCore.QThread):
            def __init__(self, parent, q):
                QtCore.QThread.__init__(self)
                self.q = q
                self.parent = parent
                self.setObjectName("MessageThread")

            def run(self):
                while True:
                    try:
                        s = self.q.get()
                        if s:
                            self.parent.send_data(s)
                    except Exception as e:
                        eprint(e)
                        traceback.print_exc(file=sys.stderr)

        self.mthread = messageThread(self, q)
        self.mthread.start()

    # ports
    def noMoniPort(self):
        self.protocol.inner.unplug()
        self.moniPort = interface.Port(name='notalk')

    def ioError(self, message):
        error(message)
        self.moniPort.close()

    def rate(self):
        return int(self.uibaud.currentText())

    def selectRate(self):
        if self.moniPort.is_open():
            self.moniPort.setRate(self.rate())

    def selectPort(self):
        print('select port')
        if self.moniPort.is_open():
            self.moniPort.close()

        if self.uiport.currentIndex():
            name = str(self.uiport.currentText())
            self.uiport.setDisabled(True)
            self.moniPort = self.serialHub.get_port(name)
            def portOpen():
                self.moniPort.open(rate=self.rate())
                if self.moniPort.is_open():
                    self.moniPort.ioError.connect(self.ioError)
                    self.moniPort.ioException.connect(self.ioError)
                    self.connectPort()
                else:
                    self.uiport.setCurrentIndex(0)
                    self.noTalkPort()
                self.uiport.setDisabled(False)
            Thread(target=portOpen).start() # run in thread to keep GUI responsive
        else:
            self.noTalkPort()

    def connectPort(self):
        self.inner.plugin(self.moniPort)

        # self.uiport.activated.connect(self.selectPort)
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
