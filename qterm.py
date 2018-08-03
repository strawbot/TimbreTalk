#!/usr/bin/env python

# GUI for serial port using QT	Robert Chapman III	Sep 28, 2012

from pyqtapi2 import *
import sys
import etmLink
import interface, hub, ipPort, serialPort, jlinkPort

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s

# update GUI from designer
from compileui import updateUi
updateUi('mainWindow')

from mainWindow import Ui_MainWindow
import traceback

import listports, serialio
from message import *

class terminal(QMainWindow):
    def __init__(self, app, parent=None, source=None):
        super(terminal, self).__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.banner()
        self.ui.fontSize.valueChanged.connect(self.setFontSize)
        self.UiAdjust()
        self.show()
        self.app = app

        # talk ports
        self.portlistMutex = QMutex()
        self.lower = interface.Interface('qterm')
        self.lower.input.connect(self.send_data)
        self.noTalkPort()
        # self.ipHub = ipPort.UdpHub()
        # self.jlinkHub = jlinkPort.JlinkHub()
        self.serialHub = serialPort.SerialHub()
        self.serialHub.update.connect(self.showPorts)
        # self.jlinkHub.update.connect(self.showPorts)
        # self.ipHub.update.connect(self.showPorts)
        self.showPorts()

        # font size adjustment
        if sys.platform == 'darwin':
            self.show()
            self.raise_()
        else:
            font = self.ui.textEdit.font()
            if sys.platform[:5] == 'linux':
                font.setFamily(_fromUtf8("Andale Mono"))
            font.setPointSize(font.pointSize() - 3)
            self.ui.textEdit.setFont(font)
            self.ui.fontSize.setValue(font.pointSize())
        self.charwidth = self.ui.textEdit.fontMetrics().width(' ')*1.1

        # widget connections
        self.ui.PortSelect.activated.connect(self.selectPort)
        self.ui.BaudRate.activated.connect(self.selectRate)
        self.ui.BaudRate.currentIndexChanged.connect(self.selectRate)
        self.ui.LoopBack.stateChanged.connect(self.connectPort)

        # text window
        self.mutex = QMutex()
        self.ui.textEdit.setCursorWidth(8)
        self.ui.textEdit.installEventFilter(self)
        self.messages(messageQueue())
        self.ui.Find.clicked.connect(self.findText)
        self.ui.ClearText.clicked.connect(self.clearText)
        self.ui.saveText.clicked.connect(self.saveText)
        self.textcount = 0

        # capture all qt errors to terminal window
        def log_uncaught_exceptions(ex_cls, ex, tb):
            error(''.join(traceback.format_tb(tb)))
            error('{0}: {1}'.format(ex_cls, ex))
        sys.excepthook = log_uncaught_exceptions

        # setup input/output
        self.ui.InBuffered.clicked.connect(self.buffered)
        self.ui.InRaw.clicked.connect(self.rawMinusEcho)
        self.ui.InRawEcho.clicked.connect(self.rawPlusEcho)
        self.ui.InHex.clicked.connect(self.rawPlusEcho)
        self.ui.InBuffered.click()
        self.echo = False
        self.linebuffer = []
        self.ui.inputIgnore.activated.connect(self.selectIgnores)
        self.ui.inputIgnore.setCurrentIndex(1) # ignore cr as default
        self.selectIgnores()

        self.ui.CrOut.setId(self.ui.CRnada, 0)
        self.ui.LfOut.setId(self.ui.LFnada, 0)
        self.ui.CrOut.setId(self.ui.CRCR, 13)
        self.ui.LfOut.setId(self.ui.LFCR, 13)
        self.ui.CrOut.setId(self.ui.CRLF, 10)
        self.ui.LfOut.setId(self.ui.LFLF, 10)
        self.ui.CrOut.buttonClicked.connect(self.setCr)
        self.ui.LfOut.buttonClicked.connect(self.setLf)
        self.ui.CRCR.click()
        self.ui.LFnada.click()
        self.ui.linewrap.stateChanged.connect(self.selectLinewrap)

        # phrases
        self.ui.send1.clicked.connect(self.ui.phrase1.returnPressed)
        self.ui.send2.clicked.connect(self.ui.phrase2.returnPressed)
        self.ui.send3.clicked.connect(self.ui.phrase3.returnPressed)
        self.ui.send4.clicked.connect(self.ui.phrase4.returnPressed)
        self.ui.send5.clicked.connect(self.ui.phrase5.returnPressed)
        self.ui.send6.clicked.connect(self.ui.phrase6.returnPressed)
        self.ui.send7.clicked.connect(self.ui.phrase7.returnPressed)
        self.ui.send8.clicked.connect(self.ui.phrase8.returnPressed)

        self.ui.phrase1.returnPressed.connect(self.sendPhrase1)
        self.ui.phrase2.returnPressed.connect(self.sendPhrase2)
        self.ui.phrase3.returnPressed.connect(self.sendPhrase3)
        self.ui.phrase4.returnPressed.connect(self.sendPhrase4)
        self.ui.phrase5.returnPressed.connect(self.sendPhrase5)
        self.ui.phrase6.returnPressed.connect(self.sendPhrase6)
        self.ui.phrase7.returnPressed.connect(self.sendPhrase7)
        self.ui.phrase8.returnPressed.connect(self.sendPhrase8)

    def setFontSize(self, size):
        font = self.ui.textEdit.font()
        font.setPointSize(size)
        self.ui.textEdit.setFont(font)

    def sendPhrase(self, s): # TODO: use line send and echo text to window; also allow for long text
        s = s+'\r'
        for c in s:
            self.keyin(c)

    def sendPhrase1(self):
        self.sendPhrase(self.ui.phrase1.text())

    def sendPhrase2(self):
        self.sendPhrase(self.ui.phrase2.text())

    def sendPhrase3(self):
        self.sendPhrase(self.ui.phrase3.text())

    def sendPhrase4(self):
        self.sendPhrase(self.ui.phrase4.text())

    def sendPhrase5(self):
        self.sendPhrase(self.ui.phrase5.text())

    def sendPhrase6(self):
        self.sendPhrase(self.ui.phrase6.text())

    def sendPhrase7(self):
        self.sendPhrase(self.ui.phrase7.text())

    def sendPhrase8(self):
        self.sendPhrase(self.ui.phrase8.text())

    def banner(self):
        self.setWindowTitle('Qterm 1.1')

    def messages(self, q): # handle messages piped in from other threads
        class messageThread(QThread):
            def __init__(self, parent, q):
                QThread.__init__(self)
                self.q = q
                self.parent = parent
                self.setObjectName("MessageThread")

            def run(self):
                while True:
                    try:
                        s = self.q.get()
                        if s:
                            self.parent.send_data(s)
                    except Queue.Empty:
                        print 'Empty exception'
                        pass
                    except Exception, e:
                        print >>sys.stderr, e
                        traceback.print_exc(file=sys.stderr)

        self.mthread = messageThread(self, q)
        self.mthread.start()

    def newCrLf(self, t):
        s = ''
        for c in t:
            if c == '\x0a':
                c = self.lfNew
            elif c == '\x0d':
                c = self.crNew
            s += c
        return s

    def setLf(self, button):
        id = self.ui.LfOut.id(button)
        if id:
            self.lfNew = chr(id)
        else:
            self.lfNew = ''

    def setCr(self, button):
        id = self.ui.CrOut.id(button)
        if id:
            self.crNew = chr(id)
        else:
            self.crNew = ''

    def eventFilter(self, object, event):
        if event.type() == QEvent.KeyPress:
            if (event.matches(QKeySequence.Paste)):
                for c in QApplication.clipboard().text():
                    self.keyin(c)
                return True
            else:
                key = event.text()
                if key:
                    self.keyin(key)
                    return True # means stop event propagation
        return QMainWindow.eventFilter(self, object, event)

    # input selection
    def multipleKeys(self):
        self.single = False

    def singleKey(self):
        self.single = True

    def buffered(self, event):
        self.multipleKeys()

    def rawMinusEcho(self, event):
        self.echo = False
        self.singleKey()

    def rawPlusEcho(self, event):
        self.echo = True
        self.singleKey()

    def selectIgnores(self):
        ignore = self.ui.inputIgnore.currentIndex() # nada, cr, lf, crlf
        self.ignore = [[],[13],[10],[10,13]][ignore]

    # serial port
    def noTalkPort(self):
        self.talkPort = hub.Port(name='notalk')

    def showPorts(self):
        self.portlistMutex.lock()
        # update port list in combobox
        uiPort = self.ui.PortSelect
        items = [uiPort.itemText(i) for i in range(1, uiPort.count())]
        ports = [port.name for port in self.serialHub.all_ports()]

        for r in list(set(items)-set(ports)): # items to be removed
            uiPort.removeItem(uiPort.findText(r))
        for a in list(set(ports)-set(items)): # items to be added
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
            self.talkPort = self.serialHub.get_port(self.ui.PortSelect.currentText())
            self.talkPort.open()
            if self.talkPort.is_open():
                self.talkPort.closed.connect(self.serialDone)
                self.talkPort.ioError.connect(self.ioError)
                self.talkPort.ioException.connect(self.ioError)
                self.connectPort()
            else:
                self.ui.PortSelect.setCurrentIndex(0)
                self.noTalkPort()
        else:
            self.noTalkPort()
        self.showPorts()

    def selectRate(self):
        self.talkPort.setRate(int(self.ui.BaudRate.currentText()))

    def ioError(self, message):
        error(message)
        self.talkPort.close()

    def serialDone(self):
        note('Serial thread finished')

    def connectPort(self):
        self.lower.plugin(self.talkPort)
        if self.ui.LoopBack.isChecked():
            self.talkPort.loopback()
        else:
            self.talkPort.normal()

    # terminal only
    def UiAdjust(self):
        # tab defines
        SerialTab, \
        SrecordTab, \
        GuidTab, \
        TestTab = range(4)
        # adjustments for terminal app
        self.ui.Controls.setCurrentIndex(SerialTab)
        self.ui.Controls.removeTab(GuidTab)
        self.ui.Controls.removeTab(SrecordTab)
        self.ui.Controls.removeTab(TestTab)
        self.ui.SFP.setVisible(0)
        self.ui.Serial1.setVisible(0)
        self.ui.ProtocolDump.setVisible(0)
        self.ui.Ping.setVisible(0)
        self.ui.groupBox_3.setVisible(0)
        self.ui.ResetRcvr.setVisible(0)

    def selectLinewrap(self, flag):
        self.ui.textEdit.LineWrapMode = QPlainTextEdit.WidgetWidth if flag else QPlainTextEdit.NoWrap

    def keyin(self, key): # input is a qstring
#		self.ui.textEdit.ensureCursorVisible()
        character = str(key)[0]

        character = self.newCrLf(character)
        if not character: return

        # detect and change delete key to backspace
        if  character == chr(0x7F):
            character = chr(0x8)

        if self.single:
            self.lower.output.emit(character)
            if self.linebuffer:
                del self.linebuffer[:]
            if self.echo:
                self.write(character)
        else:
            if character == '\x0d' or character == '\x0a':
                self.write('\x0a')
                self.lower.output.emit(''.join(self.linebuffer[:]))
                del self.linebuffer[:]
            elif character == chr(8):
                if self.linebuffer:
                    self.linebuffer.pop()
                    self.write(character)
            else:
                self.linebuffer.append(character)
                self.write(character)

    def write(self, s, style=''):
        if style:
            s = '\n'+s
        self.sink(s)
        print ("fix this")

    def sink(self, s):
        message(s)
        print ("fix this")

    def isCursorVisible(self):
        vbar = self.ui.textEdit.verticalScrollBar()
        return ((vbar.maximum() - vbar.value()) < vbar.singleStep())

    def send_data(self, data):
        if type(data) == type(('',)):
            self.writeStyled(data)
        else:
            self.writeStyled((data, ''))

    def writeStyled(self, t):
        s, style = t[0], t[1]
        if s:
            width = self.ui.textEdit.width()/self.charwidth
            if type(s[0]) == type(0):
                s = ''.join(map(chr, s))
            self.mutex.lock()
            self.ui.textEdit.moveCursor(QTextCursor.End) # get cursor to end of text
            visible = self.isCursorVisible()
            f = self.ui.textEdit.currentCharFormat()
            if style: # Note: QColor.colorNames() for a list of named colors
                if style == 'note':
                    f.setForeground(QColor("springgreen"))
                elif style == 'warning':
                    f.setForeground(QColor("orange"))
                elif style == 'error':
                    f.setForeground(QColor("tomato"))
                else:
                    f.setForeground(QColor(style))
                self.ui.textEdit.setCurrentCharFormat(f)
                if s[0] in ['\r','\n']:
                    self.textcount = 0
                self.ui.textEdit.insertPlainText(s)
            else:
                f.setForeground(QColor(self.ui.textColor.currentText()))
                self.ui.textEdit.setCurrentCharFormat(f)
                for c in s:
                    if self.ui.InHex.isChecked():
                        text = ' ' + format(ord(c), '02X')
                        self.ui.textEdit.insertPlainText(text)
                        self.textcount += len(text)
                    else:
                        if ord(c) == 8:
                            self.ui.textEdit.textCursor().deletePreviousChar()
                            self.textcount = max(0, self.textcount-1)
                        else:
                            if c in ['\r','\n']:
                                self.textcount = 0
                            else:
                                self.textcount += 1
                            if ord(c) not in self.ignore:
                                self.ui.textEdit.insertPlainText(c) # Cannot queue arguments of type 'QTextCursor'
                    if self.textcount > width:
                        self.ui.textEdit.insertPlainText('\r\n')
                        self.textcount = 0
            if visible:
                sb = self.ui.textEdit.verticalScrollBar()
                sb.setValue(sb.maximum())
            self.mutex.unlock()
            self.ui.textEdit.viewport().update()

    def close(self):
        if self.talkPort.port:
            self.talkPort.port.close()
        self.ip.close()
        self.mthread.quit()
        self.mthread.wait()

    def findText(self): # find text in terminal window
        try:
            self.ui.textEdit.setFocus()
            text = self.ui.FindText.text()
            if self.ui.FindBackwards.checkState():
                self.ui.textEdit.find(text, QTextDocument().FindBackward)
            else:
                self.ui.textEdit.find(text)
        except Exception, e:
            print >>sys.stderr, e
            traceback.print_exc(file=sys.stderr)

    def clearText(self):
        self.textcount = 0

    def saveText(self):
        filename = QFileDialog.getSaveFileName(self, "Save file", "", ".txt")
        if filename:
            try:
                text = self.ui.textEdit.toPlainText()
                open(filename, "w").write(text.encode("utf-8"))
            except Exception, e:
                print >>sys.stderr, e
                traceback.print_exc(file=sys.stderr)

    def pasteText(self):
        self.sendPhrase(QApplication.clipboard().text())

if __name__ == "__main__":
    import sys
    app = QApplication([])
    terminal = terminal(app)
    sys.exit(app.exec_())
    terminal.close()
