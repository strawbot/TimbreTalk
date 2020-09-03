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
    settings = QtCore.QSettings("TWE", "Tiny Timbre Talk")

    @classmethod
    def updatePortList(cls, portlist):
        if listsDiffer(cls.portlist, portlist):
            for self in cls.ports:
                updatePortCombo(self.uiport, portlist)
                self.out('port list updated')
            cls.portlist = portlist

    @classmethod
    def save(cls):
        for self in cls.ports:
            cls.settings.setValue(self.uiport.objectName(),self.port())
            cls.settings.setValue(self.uibaud.objectName(),self.baud())
            cls.settings.setValue(self.uitag.objectName(),self.tag())
            cls.settings.setValue(self.uiprotocol.objectName(),self.translator())
            cls.settings.setValue(self.uicolor.objectName(),self.color())

    @classmethod
    def load(cls):
        for self in cls.ports:
            self.setTag(cls.settings.value(self.uitag.objectName()))
            self.setTranslator(cls.settings.value(self.uiprotocol.objectName()))
            self.setColor(cls.settings.value(self.uicolor.objectName()))
            self.setBaud(cls.settings.value(self.uibaud.objectName()))
            portname = cls.settings.value(self.uiport.objectName())
            self.setPort(portname)
            self.uiport.activated.emit(self.uiport.currentIndex())

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

    # settings
    def port(self):
        return self.uiport.currentText()

    def setPort(self,text):
        self.uiport.setCurrentText(text)

    def rate(self):
        return int(self.uibaud.currentText())

    def baud(self):
        return self.uibaud.currentText()

    def setBaud(self, text):
        self.uibaud.setCurrentText(text)

    def tag(self):
        return self.uitag.text()

    def setTag(self, text):
        self.uitag.setText(text)

    def translator(self):
        return self.uiprotocol.currentText()

    def setTranslator(self, text):
        self.uiprotocol.setCurrentText(text)

    def color(self):
        return self.uicolor.currentText()

    def setColor(self, text):
        self.uicolor.setCurrentText(text)

    # output
    def out(self, text, start=current_milli_time()):
        report = '\n{} {:.3f}: {}'.format(self.uitag.text(), start/1000, text)
        self.monitorOut.emit(report, self.uicolor.currentText())

    def send_data(self, text):
        text_type = type(text)
        if text_type == type((0,)):
            print('type tuple of type',type(text[0]))
            self.monitorOut.emit(*text)
        else:
            print('type ',type(text), text)
            char_time = 1 / (self.rate() / 10)
            start = int(current_milli_time() - len(text) * char_time)
            self.out(asciify(text), start=start)

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

    def noTalkPort(self):
        self.talkPort = interface.Port(name='notalk')
