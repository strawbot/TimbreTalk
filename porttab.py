# porttab.py — per-port terminal tab widget
import collections
import sys
import time
import traceback
from threading import Thread

from PyQt5 import QtCore, QtGui, QtWidgets

from protocols.interface.interface import Interface, Port
from protocols.interface import serialHub as serialHubModule
from protocols.interface.telnetPort import TelnetPort
from protocols.sfpLayer import SfpLayer
from protocols.interface.message import note, warning, error, eprint

from baudcombo import BaudCombo
from colorcombo import ColorCombo
from historylineedit import HistoryLineEdit
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
PROTOCOLS = ["Serial", "SFP", "Alert2 IND", "Telnet", "Monitor"]
MONITOR_DECODE_OPTIONS = ["ASCII", "Hex", "AirLink PDU", "ALERT2 IND", "Dev Config"]
DEFAULT_BAUD = "57600"
DEFAULT_COLOR = "cyan"
DEFAULT_PROTOCOL = "Serial"


class PortTab(QtWidgets.QWidget):
    """A self-contained terminal tab: port controls + console text area."""

    # Emitted whenever this tab opens/closes a port so the parent can refresh.
    portChanged = QtCore.pyqtSignal()

    # Internal: reconnect-open result bounced back to the GUI thread.
    _reconnectResultSignal = QtCore.pyqtSignal(bool)

    # Internal: Telnet connect result and unexpected-drop notification.
    _telnetConnectResultSignal = QtCore.pyqtSignal(bool)
    _telnetDroppedSignal       = QtCore.pyqtSignal()

    RECONNECT_TIMEOUT  = 10.0   # seconds to wait for port to reappear
    RECONNECT_INTERVAL = 500    # ms between re-checks

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

        # Echo suppression for Telnet: after we send a command the device CLI
        # echoes it back.  Store the expected echo here; _consumeEcho() strips
        # it from the front of the first incoming data chunk(s).
        self._echoFilter = ''

        # Monitor mode: cache mode flag (safe to read from background threads)
        # and stateful decode buffers.
        self._monitorMode = False
        self._dcpHold     = bytearray()
        try:
            from protocols.alert2_decode import checkAlert2 as _checkAlert2
            self._alert2checker = _checkAlert2()
        except Exception:
            self._alert2checker = None

        # Reconnect state — all managed on the GUI thread via _reconnectTimer.
        self._lastRate          = 0       # baud rate saved at port open
        self._reconnecting      = False   # True while waiting for port to return
        self._reconnectName     = ''      # port name we're trying to recover
        self._reconnectRate     = 0
        self._reconnectDeadline = 0.0

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

        # Reconnect timer: fires every RECONNECT_INTERVAL ms while waiting
        # for a lost port to reappear.  Single-shot is NOT used so we can
        # keep polling without restarting manually each cycle.
        self._reconnectTimer = QtCore.QTimer(self)
        self._reconnectTimer.timeout.connect(self._tryReconnect)
        self._reconnectResultSignal.connect(self._onReconnectResult)
        self._telnetConnectResultSignal.connect(self._onTelnetConnectResult)
        self._telnetDroppedSignal.connect(self._onTelnetDropped)

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

        # --- Telnet bar (shown instead of PortSelect+BaudRate in Telnet mode) ---
        self._telnetBar = QtWidgets.QWidget(self._portRow)
        trow = QtWidgets.QHBoxLayout(self._telnetBar)
        trow.setContentsMargins(0, 0, 0, 0)
        trow.setSpacing(2)

        self._telnetHost = QtWidgets.QLineEdit(self._telnetBar)
        self._telnetHost.setPlaceholderText("hostname or IP")
        trow.addWidget(self._telnetHost, 1)

        trow.addWidget(QtWidgets.QLabel(":", self._telnetBar))

        self._telnetTcpPort = QtWidgets.QLineEdit(self._telnetBar)
        self._telnetTcpPort.setPlaceholderText("23")
        self._telnetTcpPort.setFixedWidth(42)
        trow.addWidget(self._telnetTcpPort)

        self._connectBtn = QtWidgets.QToolButton(self._telnetBar)
        self._connectBtn.setText("Connect")
        trow.addWidget(self._connectBtn)

        self._telnetBar.hide()
        row.addWidget(self._telnetBar, 1)   # same stretch slot as PortSelect

        self.ConsoleColor = ColorCombo(self._portRow)
        for c in ["white", "cyan", "blue", "green", "yellow", "orange", "magenta", "red"]:
            self.ConsoleColor.addItem(c)
        self.ConsoleColor.setCurrentText(DEFAULT_COLOR)
        row.addWidget(self.ConsoleColor)

        self.ConsoleProtocol = QtWidgets.QComboBox(self._portRow)
        self.ConsoleProtocol.addItems(PROTOCOLS)
        row.addWidget(self.ConsoleProtocol)

        # Decode combo — only visible in Monitor mode
        self._monitorDecodeCombo = QtWidgets.QComboBox(self._portRow)
        self._monitorDecodeCombo.addItems(MONITOR_DECODE_OPTIONS)
        self._monitorDecodeCombo.hide()
        row.addWidget(self._monitorDecodeCombo)

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

        self._portSettingsVisible = True

        layout.addWidget(self._portRow)

        # --- Console text area + command line ---
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

        # Command line — sits flush below the output area; styled to match.
        # Receives whole lines and sends them on Enter.  Serial output in the
        # QPlainTextEdit above is never disturbed by what the user types here.
        self._cmdLine = HistoryLineEdit(self)
        self._cmdLine.setFont(font)
        self._cmdLine.setPlaceholderText('command…')
        self._cmdLine.returnPressed.connect(self._sendCmdLine)

        # Container: Console on top, command line pinned to bottom, no gaps
        _termBox = QtWidgets.QWidget(self)
        _tlay = QtWidgets.QVBoxLayout(_termBox)
        _tlay.setContentsMargins(0, 0, 0, 0)
        _tlay.setSpacing(0)
        _tlay.addWidget(self.Console)
        _tlay.addWidget(self._cmdLine)
        layout.addWidget(_termBox)

        # Apply initial command-line style (colour updated by setColor)
        self._updateCmdLineStyle()

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
        self._connectBtn.clicked.connect(self._toggleTelnet)
        self._telnetHost.returnPressed.connect(self._connectTelnet)
        self._telnetTcpPort.returnPressed.connect(self._connectTelnet)

    def _isTelnetMode(self):
        return self.ConsoleProtocol.currentText() == 'Telnet'

    def _isMonitorMode(self):
        return self.ConsoleProtocol.currentText() == 'Monitor'

    def _updateControlsVisibility(self):
        """Apply correct widget visibility for current mode + collapse state."""
        shown   = self._portSettingsVisible
        telnet  = self._isTelnetMode()
        monitor = self._monitorMode
        # Serial-only controls (Monitor also uses PortSelect + BaudRate)
        self.PortSelect.setVisible(shown and not telnet)
        self.BaudRate.setVisible(shown and not telnet)
        self.toolButton.setVisible(shown and not telnet and not monitor)
        # Telnet bar
        self._telnetBar.setVisible(shown and telnet)
        # Monitor decode combo
        self._monitorDecodeCombo.setVisible(shown and monitor)
        # Mode-independent controls
        self.ConsoleColor.setVisible(shown)
        self.ConsoleProtocol.setVisible(shown)
        # Command line — hidden in Monitor mode (receive-only)
        self._cmdLine.setVisible(not monitor)

    def _togglePortSettings(self):
        """Show/hide the port control widgets (arrow button stays visible)."""
        self._portSettingsVisible = not self._portSettingsVisible
        self._updateControlsVisibility()
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
        was_telnet = isinstance(self.console, TelnetPort)
        self.console.close()
        if was_telnet:
            self._telnetDroppedSignal.emit()

    def selectPort(self):
        if self._isTelnetMode():
            return  # PortSelect is hidden in Telnet mode; ignore stray signals

        # User explicitly chose a port — cancel any pending reconnect first.
        if self._reconnecting:
            self._reconnectTimer.stop()
            self._reconnecting = False
            self.PortSelect.setEnabled(True)

        if self.console.is_open():
            self.console.close()

        if self.PortSelect.currentIndex():
            name = str(self.PortSelect.currentText())
            port = self.serialHub.get_port(name)
            if port is None:
                # Device not connected yet — reset quietly
                self._textBuffer.append((
                    '\n[%s not found — connect the device and reselect]\n' % name,
                    QtGui.QColor('orange')))
                self.PortSelect.setCurrentIndex(0)
                self.noConsole()
                self.portChanged.emit()
                return

            self.PortSelect.setDisabled(True)
            self.console = port
            rate = self.rate()          # capture on GUI thread before spawning
            self._lastRate = rate

            def portOpen():
                try:
                    self.console.open(rate=rate)
                    if self.console.is_open():
                        self.console.ioError.connect(self._ioError)
                        self.console.ioException.connect(self._ioError)
                        self.connectPort()
                    else:
                        self.PortSelect.setCurrentIndex(0)
                        self.noConsole()
                except Exception as e:
                    error('port open failed: %s' % e)
                    self.PortSelect.setCurrentIndex(0)
                    self.noConsole()
                finally:
                    # Always re-enable — even if open() raises or close() was called
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
        # Switching away from Telnet: close any open connection first
        if isinstance(self.console, TelnetPort) and prot != 'Telnet':
            self._disconnectTelnet()
        if prot == 'Serial':
            self.protocol.passthru()
        elif prot == 'SFP':
            self.protocol.connected()
        elif prot == 'Alert2 IND':
            warning('Under Construction')
        elif prot == 'Telnet':
            self.protocol.passthru()
            # Close any open serial port
            if self.console.is_open() and not isinstance(self.console, TelnetPort):
                self.console.close()
                self.noConsole()
        elif prot == 'Monitor':
            # Receive-only: passthru so raw bytes reach _textInputFromThread
            self.protocol.passthru()
            # Reset decode buffers when entering Monitor mode
            self._dcpHold = bytearray()
        else:
            error(prot + ' is not accounted for')
        self._monitorMode = (prot == 'Monitor')
        self._updateControlsVisibility()

    def setColor(self):
        self.color = QtGui.QColor(COLOR_MAP[self.ConsoleColor.currentText()])
        self._updateCmdLineStyle()

    def _updateCmdLineStyle(self):
        """Keep the command line background/foreground in sync with the Console color."""
        rgb = self.color.name()   # e.g. '#00ffff'
        self._cmdLine.setStyleSheet(
            'QLineEdit {'
            '  background-color: black;'
            '  color: %s;'
            '  border: none;'
            '  border-top: 1px solid #1c1c1c;'  # barely-visible hairline separator
            '  padding: 1px 4px;'
            '}' % rgb
        )

    def _sendCmdLine(self):
        """Send the command line as a complete unit and record it in history."""
        if self._monitorMode:
            return  # Monitor is receive-only
        text = self._cmdLine.text()
        if not text:
            return
        self._cmdLine.record()
        if isinstance(self.console, TelnetPort):
            self._echoFilter = text  # suppress the CLI echo coming back
        else:
            # For serial: echo locally since devices don't echo back
            self._showText('> ' + text + '\n', QtGui.QColor('white'))
        # Send to device — same null-terminated format that keyin() uses
        # (TelnetPort.send_data replaces \x00 with \r\n automatically)
        self.top.output.emit(text + '\x00')
        self._cmdLine.clear()

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
        if self._isTelnetMode():
            return  # Telnet connections are not in the serial port list
        name = self.console.name
        # 'notalk' is the dummy name set by noConsole() — never reconnect to it.
        if name and name != 'notalk':
            if name != self.PortSelect.currentText():
                idx = self.PortSelect.findText(name)
                if idx == -1:
                    if not self._reconnecting:
                        # Port disappeared while we had it selected — try to
                        # reconnect for up to RECONNECT_TIMEOUT seconds.
                        self._startReconnect(name)
                    # If already reconnecting, leave the combo alone and let
                    # _tryReconnect handle it.
                else:
                    self.PortSelect.setCurrentIndex(idx)

    # ------------------------------------------------------------------
    # Reconnect logic (all slots run on the GUI thread)
    # ------------------------------------------------------------------

    def _startReconnect(self, port_name):
        """Start the reconnect countdown after a port disappears."""
        self._reconnecting      = True
        self._reconnectName     = port_name
        self._reconnectRate     = self._lastRate
        self._reconnectDeadline = time.time() + self.RECONNECT_TIMEOUT
        self._textBuffer.append((
            '\n[%s lost — reconnecting for up to %g s…]\n'
            % (port_name, self.RECONNECT_TIMEOUT),
            QtGui.QColor('yellow')))
        self.PortSelect.setEnabled(False)
        self._reconnectTimer.start(self.RECONNECT_INTERVAL)
        self.portChanged.emit()

    def _tryReconnect(self):
        """Timer slot: check every RECONNECT_INTERVAL ms for the port to return."""
        if time.time() >= self._reconnectDeadline:
            self._reconnectTimer.stop()
            self._reconnecting = False
            self._textBuffer.append((
                '\n[Reconnect timed out — %s is closed]\n' % self._reconnectName,
                QtGui.QColor('tomato')))
            self.noConsole()
            self.PortSelect.setCurrentIndex(0)
            self.PortSelect.setEnabled(True)
            self.portChanged.emit()
            return

        port = self.serialHub.get_port(self._reconnectName)
        if port is None:
            return      # Not back yet; keep the timer running

        # Port object exists in the hub — try to open it in a thread
        # (SerialPort.open() sleeps 100 ms, so we don't block the GUI).
        self._reconnectTimer.stop()
        self.console = port
        rate = self._reconnectRate
        def do_open():
            try:
                port.open(rate=rate)
            except Exception:
                pass
            self._reconnectResultSignal.emit(port.is_open())
        Thread(target=do_open, daemon=True).start()

    def _onReconnectResult(self, success):
        """GUI thread: called after a reconnect open attempt finishes."""
        if success:
            self._reconnecting = False
            self.console.ioError.connect(self._ioError)
            self.console.ioException.connect(self._ioError)
            self.connectPort()
            self._lastRate = self._reconnectRate
            # Restore the combo selection to the reconnected port.
            idx = self.PortSelect.findText(self._reconnectName)
            if idx >= 0:
                self.PortSelect.setCurrentIndex(idx)
            self.PortSelect.setEnabled(True)
            self._textBuffer.append((
                '\n[Reconnected to %s]\n' % self._reconnectName,
                QtGui.QColor('springgreen')))
            self.portChanged.emit()
        else:
            # open() failed — device may still be booting; keep trying if time allows.
            if time.time() < self._reconnectDeadline:
                self._reconnectTimer.start(self.RECONNECT_INTERVAL)
            else:
                self._reconnecting = False
                self._textBuffer.append((
                    '\n[Reconnect timed out — %s is closed]\n' % self._reconnectName,
                    QtGui.QColor('tomato')))
                self.noConsole()
                self.PortSelect.setCurrentIndex(0)
                self.PortSelect.setEnabled(True)
                self.portChanged.emit()

    # ------------------------------------------------------------------
    # Telnet connect / disconnect
    # ------------------------------------------------------------------

    def _toggleTelnet(self):
        """Connect button clicked: toggle the Telnet connection."""
        if isinstance(self.console, TelnetPort) and self.console.is_open():
            self._disconnectTelnet()
        else:
            self._connectTelnet()

    def _connectTelnet(self):
        """Parse host:port and open a TelnetPort (in a thread)."""
        host = self._telnetHost.text().strip()
        port_str = self._telnetTcpPort.text().strip() or '23'
        if not host:
            error('Telnet: enter a hostname or IP address')
            return
        try:
            tcp_port = int(port_str)
        except ValueError:
            error('Telnet: port must be a number')
            return

        self._connectBtn.setEnabled(False)
        self._connectBtn.setText('Connecting…')

        port = TelnetPort(host, tcp_port)
        self.console = port

        def do_open():
            err = None
            try:
                port.open()
            except Exception as e:
                import traceback as _tb
                err = str(e)
                # Also dump the full traceback to stderr for the developer,
                # and append the condensed last-line detail to the console.
                _tb.print_exc()
            if err:
                self._textBuffer.append((
                    '\n[Telnet: %s]\n' % err,
                    QtGui.QColor('tomato')))
            self._telnetConnectResultSignal.emit(port.is_open())

        Thread(target=do_open, daemon=True).start()

    def _disconnectTelnet(self):
        """Close the Telnet connection and reset the connect button."""
        if isinstance(self.console, TelnetPort) and self.console.is_open():
            self.console.close()
        self.noConsole()
        self._connectBtn.setText('Connect')
        self._connectBtn.setEnabled(True)
        self.portChanged.emit()

    def _onTelnetConnectResult(self, success):
        """GUI thread: called after TelnetPort.open() finishes."""
        if success:
            self.console.ioError.connect(self._ioError)
            self.console.ioException.connect(self._ioError)
            self.connectPort()
            self._connectBtn.setText('Disconnect')
            self._connectBtn.setEnabled(True)
            self._textBuffer.append((
                '\n[Connected to %s]\n' % self.console.name,
                QtGui.QColor('springgreen')))
            self.portChanged.emit()
        else:
            self.noConsole()
            self._connectBtn.setText('Connect')
            self._connectBtn.setEnabled(True)
            self.portChanged.emit()

    def _onTelnetDropped(self):
        """GUI thread: Telnet reader thread detected the connection was lost."""
        self.noConsole()
        self._connectBtn.setText('Connect')
        self._connectBtn.setEnabled(True)
        self._textBuffer.append((
            '\n[Telnet connection lost]\n', QtGui.QColor('tomato')))
        self.portChanged.emit()

    # ------------------------------------------------------------------
    # Text I/O  (thread-safe via Qt signal)
    # ------------------------------------------------------------------

    def _textInputFromThread(self, text):
        """Called from serial/telnet reader thread — push into lock-free buffer."""
        # Telnet reader emits bytes; SFP layer emits str.  Normalise to str so
        # everything downstream (echo filter, _showText, insertPlainText) sees
        # a consistent type.  latin-1 maps each byte 0-255 to the same Unicode
        # code point with no exceptions, preserving all control characters.
        if isinstance(text, (bytes, bytearray)):
            if self._monitorMode:
                # In Monitor mode, apply the selected decode translation and
                # buffer the result.  _monitorMode is a plain bool set on the
                # GUI thread by selectProtocol() — safe to read here.
                decoded = self._applyMonitorDecode(bytes(text))
                if decoded:
                    self._textBuffer.append((decoded, None))
                return
            text = text.decode('latin-1')
        if self._echoFilter:
            text = self._consumeEcho(text)
            if not text:
                return
        self._textBuffer.append((text, None))

    def _applyMonitorDecode(self, data):
        """Translate raw bytes using the selected Monitor decode option.

        Called from the serial reader thread — only reads GUI state via the
        combo's currentText() which is safe for simple reads.

        Returns a str to display, or '' to suppress output entirely.
        """
        decode = self._monitorDecodeCombo.currentText()
        try:
            if decode == 'ASCII':
                from protocols.utilities import asciify
                return asciify(data) + '\n'
            elif decode == 'Hex':
                from protocols.utilities import hexify
                return hexify(data) + '\n'
            elif decode == 'AirLink PDU':
                from protocols.airlink import decode_mant_header
                raw = decode_mant_header(data)
                return ('\n' + raw.strip()).replace('\n', '\n  ') + '\n'
            elif decode == 'ALERT2 IND':
                if self._alert2checker is not None:
                    import time as _time
                    end = int(_time.time() * 1000)
                    report, _ = self._alert2checker(end, end, data)
                    return report if report else ''
            elif decode == 'Dev Config':
                from protocols.dcp_api import decode_dcp
                import time as _time
                self._dcpHold += data
                result = []
                while True:
                    before = len(self._dcpHold)
                    report = decode_dcp(self._dcpHold)
                    after  = len(self._dcpHold)
                    if report:
                        result.append(report)
                    if after == 0 or before == after:
                        break
                return '\n'.join(result)
        except Exception as e:
            pass
        # Fallback: show as latin-1 text
        return data.decode('latin-1')

    def _consumeEcho(self, text):
        """Strip the expected CLI echo from the front of received Telnet data.

        Works statelessly across chunk boundaries: if the echo spans two
        recv() calls, the remaining filter carries over to the next call.
        CR and LF in the received stream are ignored during matching so that
        devices which include them in the echo don't confuse the matcher.
        On any mismatch the filter is cleared and all received data is shown.
        """
        echo = self._echoFilter
        i = 0   # position in received text
        j = 0   # position in echo still to match
        while i < len(text) and j < len(echo):
            c = text[i]
            if c in '\r\n':
                i += 1          # skip line endings in the received stream
                continue
            if c == echo[j]:
                i += 1
                j += 1
            else:
                self._echoFilter = ''   # mismatch — show everything
                return text
        self._echoFilter = echo[j:]     # '' when fully matched, partial otherwise
        if not self._echoFilter:
            # Also swallow the CR/LF that follows the echoed command
            while i < len(text) and text[i] in '\r\n':
                i += 1
        return text[i:]

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
        if self._monitorMode:
            return  # Monitor is receive-only
        for character in str(key):
            if character == chr(0x7F):
                character = chr(0x8)
            if character in ('\x0d', '\x0a'):
                if echo:
                    self._showText('\r', None)
                text = ''.join(self.linebuffer)
                if isinstance(self.console, TelnetPort):
                    self._echoFilter = text  # suppress the CLI echo coming back
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
        settings.setValue(prefix + 'TelnetHost',      self._telnetHost.text())
        settings.setValue(prefix + 'TelnetTcpPort',   self._telnetTcpPort.text())
        settings.setValue(prefix + 'MonitorDecode',   self._monitorDecodeCombo.currentText())

    def loadFromSettings(self, settings, prefix):
        self.BaudRate.setCurrentText(
            settings.value(prefix + 'BaudRate', DEFAULT_BAUD))
        self.ConsoleColor.setCurrentText(
            settings.value(prefix + 'ConsoleColor', DEFAULT_COLOR))
        self.ConsoleProtocol.setCurrentText(
            settings.value(prefix + 'ConsoleProtocol', DEFAULT_PROTOCOL))
        self._telnetHost.setText(settings.value(prefix + 'TelnetHost', ''))
        self._telnetTcpPort.setText(settings.value(prefix + 'TelnetTcpPort', ''))
        self._monitorDecodeCombo.setCurrentText(
            settings.value(prefix + 'MonitorDecode', 'ASCII'))
        self.setColor()
        self.selectProtocol()
        if not self._isTelnetMode():
            self.selectRate()
            # Restore serial port selection last (triggers port open in thread)
            saved_port = settings.value(prefix + 'PortSelect', '')
            if saved_port:
                self.PortSelect.setCurrentText(saved_port)
                self.selectPort()
        # For Telnet, host:port is restored but the user connects manually
