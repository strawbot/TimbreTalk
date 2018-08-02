# update GUI from designer
from compileui import updateUi
updateUi('terminal')

from PyQt4 import QtGui, QtCore
from terminal import Ui_Frame
import interface, portal, ipPort, serialPort, jlinkPort
from sfpLayer import SfpLayer, pids
from threading import Thread

version = "V1"

def note(text):
    print >> sys.stdout, text

def error(text):
    print >> sys.stderr, text


class terminal(QtGui.QMainWindow):
    textSignal = QtCore.pyqtSignal(object)
    showPortSignal = QtCore.pyqtSignal()

    def __init__(self):
        super(terminal, self).__init__()
        self.Window = QtGui.QFrame()
        self.ui = Ui_Frame()
        self.ui.setupUi(self.Window)
        self.banner()
        self.Window.show()

        self.ui.textEdit.setCursorWidth(8)
        self.ui.textEdit.installEventFilter(self)
        self.linebuffer = []

        self.top = interface.Interface('terminal')
        self.protocol = SfpLayer()

        self.top.input.connect(self.textInput)
        self.top.plugin(self.protocol.upper)

        # isolate worker threads from GUI thread
        self.textSignal.connect(self.showText)
        self.showPortSignal.connect(self.showPorts)

        self.portlistMutex = QtCore.QMutex()
        self.textMutex = QtCore.QMutex()

        self.ui.PortSelect.activated.connect(self.selectPort)
        self.noTalkPort()
        self.ipPortal = ipPort.UdpPortal()
        self.ipPortal.whofrom = pids.IP_HOST
        self.jlinkPortal = jlinkPort.JlinkPortal()
        self.jlinkPortal.whofrom = pids.ETM_HOST
        self.serialPortal = serialPort.SerialPortal()
        self.serialPortal.whofrom = pids.MAIN_HOST

        self.serialPortal.update.connect(self.showPortUpdate)
        self.jlinkPortal.update.connect(self.showPortUpdate)
        self.ipPortal.update.connect(self.showPortUpdate)

        self.showPorts()

    # gui
    def banner(self):
        self.Window.setWindowTitle('Tiny Timbre Talk '+version)

    def textInput(self, text):
        self.textSignal.emit(text)

    def showText(self, text):
        self.textMutex.lock()
        self.ui.textEdit.moveCursor(QtGui.QTextCursor.End)  # get cursor to end of text
        self.ui.textEdit.insertPlainText(text)
        sb = self.ui.textEdit.verticalScrollBar()
        sb.setValue(sb.maximum())
        self.textMutex.unlock()

    def eventFilter(self, object, event):
        if event.type() == QtCore.QEvent.KeyPress:
            if (event.matches(QtGui.QKeySequence.Paste)):
                for c in QtGui.QApplication.clipboard().text():
                    self.keyin(c)
                return True
            else:
                key = event.text()
                if key:
                    self.keyin(key)
                    return True # means stop event propagation
        return QtGui.QMainWindow.eventFilter(self, object, event)

    def keyin(self, key):  # input is a qstring
        character = str(key)[0]

        # detect and change delete key to backspace
        if character == chr(0x7F):
            character = chr(0x8)

        if character == '\x0d' or character == '\x0a':
            self.showText(' ')
            self.linebuffer.append('\x0d')
            self.top.output.emit(''.join(self.linebuffer[:]))
            del self.linebuffer[:]
        elif character == chr(8):
            if self.linebuffer:
                self.linebuffer.pop()
                self.showText(character)
        else:
            self.linebuffer.append(character)
            self.showText(character)

    # ports
    def noTalkPort(self):
        self.protocol.lower.unplug()
        self.talkPort = portal.Port(name='notalk')

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
        ports = [port.name for port in self.serialPortal.all_ports()]

        for r in list(set(items) - set(ports)):  # items to be removed
            uiPort.removeItem(uiPort.findText(r))
        for a in list(set(ports) - set(items)):  # items to be added
            uiPort.addItem(a)

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
            self.talkPort = self.serialPortal.get_port(name)
            def portSelect():
                self.talkPort.open()
                if self.talkPort.is_open():
                    self.talkPort.ioError.connect(self.ioError)
                    self.talkPort.ioException.connect(self.ioError)
                    self.connectPort()
                else:
                    self.ui.PortSelect.setCurrentIndex(0)
                    self.noTalkPort()
                self.showPortUpdate()
            t = Thread(target=portSelect)
            t.setDaemon(True)
            t.start()  # run opening in thread
        else:
            self.noTalkPort()
        self.showPorts()

    def connectPort(self):
        self.protocol.lower.plugin(self.talkPort)
        self.protocol.whofrom = self.talkPort.portal.whofrom


if __name__ == "__main__":
    import sys, traceback

    app = QtGui.QApplication(sys.argv)
    terminal = terminal()
    try:
        sys.exit(app.exec_())
    except Exception, e:
        error("Handler {} exception: {}".format(pids.pids[pid], e))
        traceback.print_exc(file=sys.stderr)

