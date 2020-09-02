# update GUI from designer
from compileui import updateUi
updateUi('terminal')

from qt import QtGui, QtWidgets, QtCore
from terminal import Ui_Frame
from protocols.interface import interface, ipHub, serialHub, jlinkHub
from protocols.sfpLayer import SfpLayer
from protocols import pids
from threading import Thread
from protocols.interface.message import note, warning, error, setTextOutput, eprint

from monitor import portMonitor, updatePortCombo
from portcombo import PortCombo
from baudcombo import BaudCombo
from colorcombo import ColorCombo
from formatcombo import FormatCombo
from monitorframe import MonitorFrame

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s

version = "V2"

class terminal(QtWidgets.QMainWindow):
    textSignal = QtCore.pyqtSignal(object)
    showPortSignal = QtCore.pyqtSignal()
    serialPortUpdate = QtCore.pyqtSignal(object)

    def __init__(self):
        super(terminal, self).__init__()
        self.Window = QtWidgets.QFrame()
        self.ui = Ui_Frame()
        self.ui.setupUi(self.Window)
        self.banner()
        self.Window.show()

        setTextOutput(self.messageOut)

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

        # self.ui.PortSelect.activated.connect(self.selectPort)
        # self.ui.SetSerial.clicked.connect(self.setSerial)
        # self.ui.SetSfp.clicked.connect(self.setSfp)
        # self.ui.SetSfp.click()
        # self.ui.BaudRate.activated.connect(self.selectRate)
        self.ui.BaudRate.currentIndexChanged.connect(self.selectRate)
        self.ui.ConsoleColor.activated.connect(self.setColor)

        # self.ui.Console.setEnabled(True)
        self.ui.Console.installEventFilter(self)
        self.noTalkPort()
        self.jlinkHub = jlinkHub.JlinkHub()
        self.jlinkHub.whofrom = pids.ETM_HOST
        self.serialHub = serialHub.SerialHub()
        self.serialHub.whofrom = pids.MAIN_HOST

        self.serialHub.update.connect(self.showPortUpdate)
        self.jlinkHub.update.connect(self.showPortUpdate)

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

        # monitor tab
        for widget in self.ui.PortMonitors.findChildren(MonitorFrame):
            print(widget.objectName())
            port = widget.findChildren(PortCombo)[0]
            baud = widget.findChildren(BaudCombo)[0]
            color = widget.findChildren(ColorCombo)[0]
            protocol = widget.findChildren(FormatCombo)[0]
            print('Mon groups:', baud.currentText(), color.currentText(), protocol.currentText(), port.currentText())
            mname = widget.findChildren(QtWidgets.QLineEdit)[0]
            pm = portMonitor(port, baud, mname, protocol, color)
            pm.monitorOut.connect(self.messageOut)
            pm.monitorOut.emit(mname.text(), 'white')

        self.serialPortUpdate.connect(portMonitor.updatePortList)
        self.showPorts()

        if sys.platform == 'darwin':
            self.raise_()
        else:
            font = self.ui.Console.font()
            if sys.platform[:5] == 'linux':
                font.setFamily(_fromUtf8("Andale Mono"))
            font.setPointSize(font.pointSize() - 3)
            self.ui.Console.setFont(font)

        self.portParametersMenu()

    # gui
    def setSerial(self):
        self.protocol.passthru()

    def setSfp(self):
        self.protocol.connected()

    def selectRate(self):
        self.rate = int(self.ui.BaudRate.currentText())
        if self.talkPort.is_open():
            self.talkPort.setRate(self.rate)

    def setColor(self):
        self.color = QtGui.QColor(self.colorMap[self.ui.ConsoleColor.currentText()])

    def useColor(self, color):
        tf = self.ui.Console.currentCharFormat()
        tf.setForeground(color)
        self.ui.Console.setCurrentCharFormat(tf)

    def banner(self):
        self.Window.setWindowTitle('Tiny Timbre Talk '+version)

    def textInput(self, text):
        self.textSignal.emit(text)

    def messageOut(self, text, style=''):
        if style:
            self.showText(text, QtGui.QColor(self.colorMap[style]))
        else:
            self.showText(text)

    def showText(self, text, color=None):
        print(type(text),text)
        if color == None:
            color = self.color
        self.textMutex.lock()
        self.ui.Console.moveCursor(QtGui.QTextCursor.End)  # get cursor to end of text
        if text == chr(8):
            self.ui.Console.textCursor().deletePreviousChar()
        else:
            if type(text) == type(b''):
                text = text.decode(errors='ignore') # todo: shift to asciihex
            self.useColor(color)
            self.ui.Console.insertPlainText(text)
        # self.ui.Console.moveCursor(QtGui.QTextCursor.End)  # get cursor to end of text
        sb = self.ui.Console.verticalScrollBar()
        sb.setValue(sb.maximum())
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

    # parity n' stuff
    def portParametersMenu(self):
        # menu for serial port parameters
        paramenu = QtWidgets.QMenu(self)
        paramenu.addAction("N 8 1", lambda: self.setParam('N', 8, 1))
        paramenu.addAction("E 8 1", lambda: self.setParam('E', 8, 1))

        paritymenu = paramenu.addMenu('Parity')
        paritymenu.addAction('None', lambda: self.setParam('N',0,0))
        paritymenu.addAction('Even', lambda: self.setParam('E',0,0))
        paritymenu.addAction('Odd', lambda: self.setParam('O',0,0))

        bytesizemenu = paramenu.addMenu('Byte size')
        bytesizemenu.addAction('8', lambda: self.setParam(0,8,0))
        bytesizemenu.addAction('7', lambda: self.setParam(0,7,0))
        bytesizemenu.addAction('6', lambda: self.setParam(0,6,0))
        bytesizemenu.addAction('5', lambda: self.setParam(0,5,0))

        stopmenu = paramenu.addMenu('Stopbits')
        stopmenu.addAction('1', lambda: self.setParam(0,0,1))
        stopmenu.addAction('1.5', lambda: self.setParam(0,0,1.5))
        stopmenu.addAction('2', lambda: self.setParam(0,0,2))

        self.ui.toolButton.setMenu(paramenu)

        # self.setParamButtonText()
    def setParam(self, parity, bytesize, stopbits):
        try:
            sp = self.talkPort
            if parity: sp.parity = parity
            if bytesize: sp.bytesize = bytesize
            if stopbits: sp.stopbits = stopbits
            self.setParamButtonText()

            if sp:
                note('Changed port settings to %s%d%d'%(sp.parity,sp.bytesize,sp.stopbits))
        except Exception as e:
            eprint(e)
            traceback.print_exc(file=sys.stderr)
            error("can't set Params")

    def setParamButtonText(self):
        sp = self.talkPort
        if sp.stopbits == 1.5:
            self.ui.toolButton.setText("%s %i %0.1f" % (sp.parity, sp.bytesize, sp.stopbits))
        else:
            self.ui.toolButton.setText("%s %i %i" % (sp.parity, sp.bytesize, sp.stopbits))

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
        uiPort = self.ui.PortSelect
        self.portlistMutex.lock()
        ports = [port.name for port in self.serialHub.all_ports()]
        updatePortCombo(uiPort, ports)
        # check current port against list and select proper item
        if self.talkPort.name:
            if self.talkPort.name != uiPort.currentText():
                index = uiPort.findText(self.talkPort.name)
                if index == -1:
                    index = 0
                    self.noTalkPort()
                uiPort.setCurrentIndex(index)

        final = [uiPort.itemText(i) for i in range(1, uiPort.count())]
        self.portlistMutex.unlock()
        self.serialPortUpdate.emit(final)

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

