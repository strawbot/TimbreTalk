# update GUI from designer
from compileui import updateUi
updateUi('terminal')

from qt import QtGui, QtWidgets, QtCore
from terminal import Ui_Frame
from protocols.interface import interface, ipHub, serialHub, jlinkHub
from protocols.sfpLayer import SfpLayer
from protocols import pids
from threading import Thread
import bisect

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s

version = "V1"

def note(text):
    print >> sys.stdout, text

def error(text):
    print >> sys.stderr, text

class terminal(QtWidgets.QMainWindow):
    textSignal = QtCore.pyqtSignal(object)
    showPortSignal = QtCore.pyqtSignal()

    def __init__(self):
        super(terminal, self).__init__()
        self.Window = QtWidgets.QFrame()
        self.ui = Ui_Frame()
        self.ui.setupUi(self.Window)
        self.banner()
        self.Window.show()

        self.linebuffer = []

        self.top = interface.Interface('terminal')
        self.protocol = SfpLayer()

        self.top.input.connect(self.textInput)
        self.top.plugin(self.protocol)

        # isolate worker threads from GUI thread
        self.textSignal.connect(self.showText)
        self.showPortSignal.connect(self.showPorts)

        self.portlistMutex = QtCore.QMutex()
        self.textMutex = QtCore.QMutex()

        self.ui.PortSelect.activated.connect(self.selectPort)
        self.ui.SetSerial.clicked.connect(self.setSerial)
        self.ui.SetSfp.clicked.connect(self.setSfp)
        self.ui.SetSfp.click()
        self.ui.BaudRate.activated.connect(self.selectRate)
        self.ui.BaudRate.currentIndexChanged.connect(self.selectRate)
        self.ui.ConsoleColor.activated.connect(self.setColor)

        # self.ui.Console.setEnabled(True)
        self.ui.Console.installEventFilter(self)
        self.noTalkPort()
        self.ipHub = ipHub.UdpHub()
        self.ipHub.whofrom = pids.UDP_HOST
        self.jlinkHub = jlinkHub.JlinkHub()
        self.jlinkHub.whofrom = pids.ETM_HOST
        self.serialHub = serialHub.SerialHub()
        self.serialHub.whofrom = pids.MAIN_HOST

        self.serialHub.update.connect(self.showPortUpdate)
        self.jlinkHub.update.connect(self.showPortUpdate)
        self.ipHub.update.connect(self.showPortUpdate)

        self.rate = int(self.ui.BaudRate.currentText())
        self.colorMap = {"white":"white",
                         "cyan":"cyan",
                         "blue":"deepskyblue",
                         "green":"springgreen",
                         "yellow":"yellow",
                         "orange":"orange",
                         "magenta":"magenta",
                         "red":"tomato",
                         "note":"springgreen",
                         "warning":"orange",
                         "error":"tomato"}
        self.setColor()

        self.showPorts()

        if sys.platform == 'darwin':
            self.raise_()
        else:
            font = self.ui.Console.font()
            if sys.platform[:5] == 'linux':
                font.setFamily(_fromUtf8("Andale Mono"))
            font.setPointSize(font.pointSize() - 3)
            self.ui.Console.setFont(font)

    # gui
    def setSerial(self):
        self.protocol.passthru()

    def setSfp(self):
        self.protocol.connected()

    def selectRate(self):
        self.rate = int(self.ui.BaudRate.currentText())
        if self.talkPort:
            self.talkPort.setRate(self.rate)

    def setColor(self):
        self.color = self.colorMap[self.ui.ConsoleColor.currentText()]

    def useColor(self):
        tf = self.ui.Console.currentCharFormat()
        tf.setForeground(QtGui.QColor(self.color))
        self.ui.Console.setCurrentCharFormat(tf)

    def banner(self):
        self.Window.setWindowTitle('Tiny Timbre Talk '+version)

    def textInput(self, text):
        self.textSignal.emit(text)

    def showText(self, text):
        self.textMutex.lock()
        self.ui.Console.moveCursor(QtGui.QTextCursor.End)  # get cursor to end of text
        if text == chr(8):
            self.ui.Console.textCursor().deletePreviousChar()
            sb = self.ui.Console.verticalScrollBar()
            sb.setValue(sb.maximum())
        else:
            if type(text) == type(b''):
                text = text.decode(errors='ignore')
            self.useColor()
            self.ui.Console.insertPlainText(text)
        self.textMutex.unlock()

    def eventFilter(self, object, event):
        if event.type() == QtCore.QEvent.KeyPress:
            key = event.text()
            if key:
                self.keyin(key)
                return True # means stop event propagation
        return QtWidgets.QMainWindow.eventFilter(self, object, event)

    def keyin(self, key):  # input is a qstring
        for character in str(key):

            # detect and change delete key to backspace
            if character == chr(0x7F):
                character = chr(0x8)

            if character == '\x0d' or character == '\x0a':
                self.showText('\r')
                self.linebuffer.append('\x0d')
                command = ''.join(self.linebuffer[:])
                del self.linebuffer[:]
                self.top.output.emit(command)
            elif character == chr(8):
                if self.linebuffer:
                    self.linebuffer.pop()
                    self.showText(character)
            else:
                self.linebuffer.append(character)
                self.showText(character)

    # ports
    def noTalkPort(self):
        self.protocol.inner.unplug()
        self.talkPort = interface.Port(name='notalk')

    def ioError(self, message):
        error(message)
        self.talkPort.close()

    def showPortUpdate(self):
        self.showPortSignal.emit()

    def showPorts(self):
        self.portlistMutex.lock()
        # update port list in combobox
        uiPort = self.ui.PortSelect
        items = [uiPort.itemText(i) for i in range(1, uiPort.count())]
        ports = [port.name for port in self.serialHub.all_ports()]

        for r in list(set(items) - set(ports)):  # items to be removed
            uiPort.removeItem(uiPort.findText(r))
            if r in items:  items.remove(r)
        for a in list(set(ports) - set(items)):  # items to be added
            bisect.insort(items, a)
            uiPort.insertItem(1 + items.index(a), a)

        # check current port against list and select proper item
        if self.talkPort.name:
            if self.talkPort.name != uiPort.currentText():
                index = uiPort.findText(self.talkPort.name)
                if index == -1:
                    index = 0
                    self.noTalkPort()
                uiPort.setCurrentIndex(index)

        # set item zero
        text = '(Disconnect)' if uiPort.currentIndex() else '(Select a Port)'
        if uiPort.itemText(0) != text:
            uiPort.setItemText(0, text)
        self.portlistMutex.unlock()


    def selectPort(self):
        if self.talkPort.is_open():
            self.talkPort.close()

        if self.ui.PortSelect.currentIndex():
            name = str(self.ui.PortSelect.currentText())
            self.ui.PortSelect.setDisabled(True)
            self.talkPort = self.serialHub.get_port(name)
            def portOpen():
                self.talkPort.open()
                self.talkPort.setRate(self.rate)
                if self.talkPort.is_open():
                    self.talkPort.ioError.connect(self.ioError)
                    self.talkPort.ioException.connect(self.ioError)
                    self.connectPort()
                else:
                    self.ui.PortSelect.setCurrentIndex(0)
                    self.noTalkPort()
                self.ui.PortSelect.setDisabled(False)
                self.showPortUpdate()
            Thread(target=portOpen).start() # run in thread to keep GUI responsive
        else:
            self.noTalkPort()
        self.showPorts()

    def connectPort(self):
        self.protocol.plugin(self.talkPort)
        self.protocol.whofrom = self.talkPort.hub.whofrom


if __name__ == "__main__":
    import sys, traceback

    app = QtWidgets.QApplication(sys.argv)
    terminal = terminal()
    try:
        sys.exit(app.exec_())
    except Exception as e:
        error(e)
        traceback.print_exc(file=sys.stderr)

