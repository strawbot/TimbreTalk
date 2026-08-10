# porttab.py — per-port terminal tab widget
import collections
import sys
import time
import traceback
from threading import Thread

from PyQt5 import QtCore, QtGui, QtWidgets

from protocols.interface.interface import Interface, Port
from protocols.interface import serialHub as serialHubModule
from protocols.sfpLayer import SfpLayer
from protocols.interface.message import note, warning, error, eprint

from baudcombo import BaudCombo
from colorcombo import ColorCombo
from monitor import updatePortCombo


COLOR_MAP = {
    "white":   "white",
    "cyan":    "cyan",
    "blue":    "deepskyblue",
    "green":   "springgreen",
    "yellow":  "yellow",
    "orange":  "orange",
    "magenta": "magenta",
    "red":     "tomato",
    "note":    "springgreen",
    "warning": "orange",
    "error":   "tomato",
}

BAUD_RATES = [
    "1200", "9600", "19200", "28800", "38400", "57600",
    "115200", "230400", "460800", "500000", "921600", "1000000",
]
PROTOCOLS = ["Serial", "SFP", "Alert2 IND"]
DEFAULT_BAUD = "57600"
DEFAULT_COLOR = "cyan"
DEFAULT_PROTOCOL = "Serial"


class PortTab(QtWidgets.QWidget):
    """A self-contained terminal tab: port controls + console text area."""

    # Emitted whenever this tab opens/closes a port so the parent can refresh.
    portChanged = QtCore.pyqtSignal()

    def __init__(self, serial_hub, parent=None):
        super().__init__(parent)
        self.serialHub = serial_hub
        self.linebuffer = []
        self.linedelay = 0.1
        self.textMutex = QtCore.QMutex()
        self.color = QtGui.QColor(COLOR_MAP[DEFAULT_COLOR])

        # Lock-free text buffer: serial threads append (text, color) tuples;
        # the GUI-thread timer drains and renders them in batches.
        # collections.deque append/popleft are atomic in CPython (GIL).
        self._textBuffer = collections.deque()

        self._build_ui()
        self._setup_protocol()
        self._setup_params_menu()
        self._connect_signals()
        self.noConsole()
        # Initialise the SfpLayer to the default protocol so data flows
        # immediately without requiring a Save+Load cycle.
        self.selectProtocol()

        # 30 ms timer drains _textBuffer on the GUI thread.
        # Keeps serial threads and the GUI fully independent.
        self._flushTimer = QtCore.QTimer(self)
        self._flushTimer.timeout.connect(self._flushBuffer)
        self._flushTimer.start(30)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)

        # --- Compact single-row port bar ---
        self._portRow = QtWidgets.QWidget(self)
        row = QtWidgets.QHBoxLayout(self._portRow)
        row.setContentsMargins(2, 1, 2, 1)
        row.setSpacing(4)

        # Collapse / expand toggle
        self._collapseBtn = QtWidgets.QToolButton(self._portRow)
        self._collapseBtn.setArrowType(QtCore.Qt.DownArrow)
        self._collapseBtn.setFixedSize(14, 14)
        self._collapseBtn.setAutoRaise(True)
        self._collapseBtn.setToolTip("Show/hide port settings")
        self._collapseBtn.clicked.connect(self._togglePortSettings)
        row.addWidget(self._collapseBtn)

        self.PortSelect = QtWidgets.QComboBox(self._portRow)
        self.PortSelect.addItem("(Select a Port)")
        self.PortSelect.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
        self.PortSelect.setInsertPolicy(QtWidgets.QComboBox.InsertAlphabetically)
        row.addWidget(self.PortSelect, 1)   # stretch to fill spare space

        self.ConsoleColor = ColorCombo(self._portRow)
        for c in ["white", "cyan", "blue", "green", "yellow", "orange", "magenta", "red"]:
            self.ConsoleColor.addItem(c)
        self.ConsoleColor.setCurrentText(DEFAULT_COLOR)
        row.addWidget(self.ConsoleColor)

        self.ConsoleProtocol = QtWidgets.QComboBox(self._portRow)
        self.ConsoleProtocol.addItems(PROTOCOLS)
        row.addWidget(self.ConsoleProtocol)

        self.BaudRate = BaudCombo(self._portRow)
        for b in BAUD_RATES:
            self.BaudRate.addItem(b)
        self.BaudRate.setCurrentText(DEFAULT_BAUD)
        row.addWidget(self.BaudRate)

        self.toolButton = QtWidgets.QToolButton(self._portRow)
        self.toolButton.setText("N 8 1")
        self.toolButton.setPopupMode(QtWidgets.QToolButton.MenuButtonPopup)
        self.toolButton.setToolButtonStyle(QtCore.Qt.ToolButtonTextOnly)
        row.addWidget(self.toolButton)
        row.addStretch()          # pins collapse button to the left when controls hidden

        # Collect the "collapsible" widgets (everything except the toggle btn)
        self._portControls = [
            self.PortSelect, self.ConsoleColor,
            self.ConsoleProtocol, self.BaudRate, self.toolButton,
        ]
        self._portSettingsVisible = True

        layout.addWidget(self._portRow)

        # --- Console text area ---
        tab_self = self  # capture for inner class

        class _Console(QtWidgets.QPlainTextEdit):
            def insertFromMimeData(self2, source):
                # Intercept paste/drop: send as typed input
                tab_self.keyin(source.text() + '\n')

        self.Console = _Console(self)
        font = QtGui.QFont("Courier", 12)
        font.setKerning(False)
        self.Console.setFont(font)

        palette = QtGui.QPalette()
        cyan = QtGui.QBrush(QtGui.QColor(0, 255, 255))
        black = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        for state in (QtGui.QPalette.Active, QtGui.QPalette.Inactive, QtGui.QPalette.Disabled):
            palette.setBrush(state, QtGui.QPalette.Base, black)
            palette.setBrush(state, QtGui.QPalette.Text, cyan)
            palette.setBrush(state, QtGui.QPalette.WindowText, cyan)
        self.Console.setPalette(palette)
        self.Console.setMinimumSize(200, 100)
        self.Console.setUndoRedoEnabled(False)
        self.Console.setLineWrapMode(QtWidgets.QPlainTextEdit.WidgetWidth)
        self.Console.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.Console.setUndoRedoEnabled(False)
        layout.addWidget(self.Console)

    def _setup_protocol(self):
        self.top = Interface('terminal')
        self.protocol = SfpLayer()
        self.top.input.connect(self._textInputFromThread)
        self.top.plugin(self.protocol)

    def _setup_params_menu(self):
        menu = QtWidgets.QMenu(self)
        menu.addAction("N 8 1", lambda: self.setParam('N', 8, 1))
        menu.addAction("E 8 1", lambda: self.setParam('E', 8, 1))

        parity = menu.addMenu('Parity')
        parity.addAction('None', lambda: self.setParam('N', 0, 0))
        parity.addAction('Even', lambda: self.setParam('E', 0, 0))
        parity.addAction('Odd',  lambda: self.setParam('O', 0, 0))

        bytesize = menu.addMenu('Byte size')
        for s in [8, 7, 6, 5]:
            bytesize.addAction(str(s), lambda v=s: self.setParam(0, v, 0))

        stopbits = menu.addMenu('Stopbits')
        stopbits.addAction('1',   lambda: self.setParam(0, 0, 1))
        stopbits.addAction('1.5', lambda: self.setParam(0, 0, 1.5))
        stopbits.addAction('2',   lambda: self.setParam(0, 0, 2))

        self.toolButton.setMenu(menu)

    def _connect_signals(self):
        self.PortSelect.activated.connect(self.selectPort)
        self.ConsoleProtocol.activated.connect(self.selectProtocol)
        self.BaudRate.activated.connect(self.selectRate)
        self.BaudRate.currentIndexChanged.connect(self.selectRate)
        self.ConsoleColor.activated.connect(self.setColor)

    def _togglePortSettings(self):
        """Show/hide the port control widgets (arrow button stays visible)."""
        self._portSettingsVisible = not self._portSettingsVisible
        for w in self._portControls:
            w.setVisible(self._portSettingsVisible)
        self._collapseBtn.setArrowType(
            QtCore.Qt.DownArrow if self._portSettingsVisible
            else QtCore.Qt.RightArrow)

    # ------------------------------------------------------------------
    # Port management
    # ------------------------------------------------------------------

    def noConsole(self):
        self.protocol.inner.unplug()
        self.console = Port(name='notalk')

    def _ioError(self, message):
        error(message)
        self.console.close()

    def selectPort(self):
        if self.console.is_open():
            self.console.close()

        if self.PortSelect.currentIndex():
            name = str(self.PortSelect.currentText())
            self.PortSelect.setDisabled(True)
            self.console = self.serialHub.get_port(name)

            def portOpen():
                self.console.open(rate=self.rate())
                if self.console.is_open():
                    self.console.ioError.connect(self._ioError)
                    self.console.ioException.connect(self._ioError)
                    self.connectPort()
                else:
                    self.PortSelect.setCurrentIndex(0)
                    self.noConsole()
                self.PortSelect.setDisabled(False)
                self.portChanged.emit()

            Thread(target=portOpen, daemon=True).start()
        else:
            self.noConsole()
        self.portChanged.emit()

    def connectPort(self):
        self.protocol.plugin(self.console)

    def selectRate(self):
        if self.console.is_open():
            self.console.setRate(self.rate())

    def rate(self):
        return int(self.BaudRate.currentText())

    def selectProtocol(self):
        prot = self.ConsoleProtocol.currentText()
        if prot == 'Serial':
            self.protocol.passthru()
        elif prot == 'SFP':
            self.protocol.connected()
        elif prot == 'Alert2 IND':
            warning('Under Construction')
        else:
            error(prot + ' is not accounted for')

    def setColor(self):
        self.color = QtGui.QColor(COLOR_MAP[self.ConsoleColor.currentText()])

    def setParam(self, parity, bytesize, stopbits):
        try:
            sp = self.console
            if parity:   sp.parity   = parity
            if bytesize: sp.bytesize = bytesize
            if stopbits: sp.stopbits = stopbits
            self._setParamButtonText()
            if sp:
                note('Changed port settings to %s%d%d' % (sp.parity, sp.bytesize, sp.stopbits))
        except Exception as e:
            eprint(e)
            traceback.print_exc(file=sys.stderr)
            error("can't set Params")

    def _setParamButtonText(self):
        sp = self.console
        if sp.stopbits == 1.5:
            self.toolButton.setText("%s %i %0.1f" % (sp.parity, sp.bytesize, sp.stopbits))
        else:
            self.toolButton.setText("%s %i %i" % (sp.parity, sp.bytesize, sp.stopbits))

    def updatePortList(self, ports):
        """Refresh PortSelect combo; called when USB ports appear/disappear."""
        updatePortCombo(self.PortSelect, ports)
        if self.console.name:
            if self.console.name != self.PortSelect.currentText():
                idx = self.PortSelect.findText(self.console.name)
                if idx == -1:
                    idx = 0
                    self.noConsole()
                self.PortSelect.setCurrentIndex(idx)

    # ------------------------------------------------------------------
    # Text I/O  (thread-safe via Qt signal)
    # ------------------------------------------------------------------

    def _textInputFromThread(self, text):
        """Called from serial-reader thread — push into lock-free buffer."""
        self._textBuffer.append((text, None))

    def _showText(self, text, color):
        """GUI-thread slot: append text to the Console widget."""
        if color is None:
            color = self.color
        visible = self._isCursorVisible()
        self.textMutex.lock()
        self.Console.moveCursor(QtGui.QTextCursor.End)
        if text == chr(8):
            self.Console.textCursor().deletePreviousChar()
        else:
            if isinstance(text, bytes):
                text = text.decode(errors='ignore')
            tf = self.Console.currentCharFormat()
            tf.setForeground(color)
            self.Console.setCurrentCharFormat(tf)
            self.Console.insertPlainText(text)
        if visible:
            sb = self.Console.verticalScrollBar()
            sb.setValue(sb.maximum())
        self.textMutex.unlock()

    def _flushBuffer(self):
        """GUI-thread timer slot: drain _textBuffer and render all pending text.

        Serial threads never touch the GUI — they only append to the deque.
        This slot runs at most every 30 ms, batching any number of chunks into
        a single rendering pass for smooth high-throughput output.
        """
        if not self._textBuffer:
            return
        try:
            while True:
                text, color = self._textBuffer.popleft()
                self._showText(text, color)
        except IndexError:
            pass

    def _isCursorVisible(self):
        vbar = self.Console.verticalScrollBar()
        return vbar.value() == vbar.maximum()

    def messageOut(self, text, style=''):
        """Thread-safe output with optional named style."""
        color = QtGui.QColor(COLOR_MAP[style]) if style else None
        self._textBuffer.append((text, color))

    def keyin(self, key, echo=True):
        """Process typed/pasted characters: buffer, echo, and send on newline."""
        for character in str(key):
            if character == chr(0x7F):
                character = chr(0x8)
            if character in ('\x0d', '\x0a'):
                if echo:
                    self._showText('\r', None)
                self.linebuffer.append('\x00')
                command = ''.join(self.linebuffer)
                self.linebuffer.clear()
                self.top.output.emit(command)
                time.sleep(self.linedelay)
            elif character == chr(8):
                if self.linebuffer:
                    self.linebuffer.pop()
                    if echo:
                        self._showText(character, None)
            else:
                self.linebuffer.append(character)
                if echo:
                    self._showText(character, None)

    # ------------------------------------------------------------------
    # Find text
    # ------------------------------------------------------------------

    def findText(self, text, backwards=False):
        self.Console.setFocus()
        if backwards:
            self.Console.find(text, QtGui.QTextDocument.FindBackward)
        else:
            self.Console.find(text)

    # ------------------------------------------------------------------
    # Settings  (keyed by caller-supplied prefix, e.g. "portTabs/0/")
    # ------------------------------------------------------------------

    def saveToSettings(self, settings, prefix):
        settings.setValue(prefix + 'PortSelect',      self.PortSelect.currentText())
        settings.setValue(prefix + 'BaudRate',        self.BaudRate.currentText())
        settings.setValue(prefix + 'ConsoleColor',    self.ConsoleColor.currentText())
        settings.setValue(prefix + 'ConsoleProtocol', self.ConsoleProtocol.currentText())

    def loadFromSettings(self, settings, prefix):
        self.BaudRate.setCurrentText(
            settings.value(prefix + 'BaudRate', DEFAULT_BAUD))
        self.ConsoleColor.setCurrentText(
            settings.value(prefix + 'ConsoleColor', DEFAULT_COLOR))
        self.ConsoleProtocol.setCurrentText(
            settings.value(prefix + 'ConsoleProtocol', DEFAULT_PROTOCOL))
        self.setColor()
        self.selectProtocol()
        self.selectRate()
        # Restore port selection last (triggers port open in thread)
        saved_port = settings.value(prefix + 'PortSelect', '')
        if saved_port:
            self.PortSelect.setCurrentText(saved_port)
            self.selectPort()
