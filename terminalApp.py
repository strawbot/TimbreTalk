# TimbreTalk — multi-port terminal
import os
import sys
import time
import traceback

from PyQt5 import QtGui, QtWidgets, QtCore

from protocols.interface.interface import Interface, Port
from protocols.interface import serialHub
from protocols.sfpLayer import SfpLayer
from protocols import pids
from threading import Thread
from protocols.interface.message import note, warning, error, setTextOutput, eprint

from terminal import Ui_Frame
from porttab import PortTab
from panesplit import PaneSplitter

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s

appname = "TimbreTalk "
version = "V5"


class terminal(QtWidgets.QMainWindow):
    showPortSignal   = QtCore.pyqtSignal()
    serialPortUpdate = QtCore.pyqtSignal(object)
    settings         = QtCore.QSettings("TWE", "Tiny Timbre Talk")
    _pingResult      = QtCore.pyqtSignal(bool, str)   # (success, rtt_or_error)
    _messageSignal   = QtCore.pyqtSignal(str, str)    # note/warning/error -> GUI thread

    def __init__(self):
        super(terminal, self).__init__()
        self.Window = QtWidgets.QFrame()
        self.ui = Ui_Frame()

        # terminal.py still references self.ui.Console before setupUi;
        # keep a stub so setupUi can place it in the layout (we hide it after).
        self.ui.Console = QtWidgets.QPlainTextEdit(self.Window)

        self.ui.setupUi(self.Window)
        self.banner()
        self.Window.show()

        # -----------------------------------------------------------------
        # IP ping widget — inserted between Tools and Settings panels
        # -----------------------------------------------------------------
        self._buildPingWidget()

        # -----------------------------------------------------------------
        # Port-tab container (replaces the single Console on the right side)
        # PaneSplitter supports drag-to-split and multiple panes.
        # -----------------------------------------------------------------
        self._lastActiveTab = None   # most recently focused PortTab
        QtWidgets.QApplication.instance().focusChanged.connect(
            self._onFocusChanged)

        self.portTabs = PaneSplitter()
        self.portTabs.tabCloseRequest.connect(self._closePortTab)
        self.portTabs.currentChanged.connect(self._onPortTabChanged)
        self.portTabs.addTabRequested.connect(
            lambda pane: self.addPortTab(target_pane=pane))

        # Swap the stub Console out of its layout and insert portTabs
        self.ui.verticalLayout.replaceWidget(self.ui.Console, self.portTabs)
        self.ui.Console.hide()

        # -----------------------------------------------------------------
        # Serial hub (shared across all tabs)
        # -----------------------------------------------------------------
        self.portlistMutex = QtCore.QMutex()
        self.serialHub = serialHub.SerialHub()
        self.serialHub.whofrom = pids.MAIN_HOST
        self.serialHub.update.connect(self._showPortUpdate)
        self.showPortSignal.connect(self.showPorts)
        self._messageSignal.connect(self._doMessageOut)

        # -----------------------------------------------------------------
        # First port tab
        # -----------------------------------------------------------------
        self.addPortTab(label="Port 1")

        # Route global note/warning/error messages to the active tab
        setTextOutput(self.messageOut)

        # -----------------------------------------------------------------
        # Line delay
        # -----------------------------------------------------------------
        def SetLineDelay():
            delay = int(self.ui.LineDelay.text()) / 1000
            for tab, _lbl in self.portTabs.allTabs():
                if isinstance(tab, PortTab):
                    tab.linedelay = delay
        self.ui.LineDelay.returnPressed.connect(SetLineDelay)

        # -----------------------------------------------------------------
        # Find bar (bottom row — acts on active tab's Console)
        # -----------------------------------------------------------------
        self.ui.Find.clicked.connect(self.findText)
        self.ui.pushButton.clicked.connect(self._clearConsole)

        # -----------------------------------------------------------------
        # Shared Tools connections (left panel Console tab)
        # -----------------------------------------------------------------
        self.ui.SendHex.clicked.connect(self.sendHex)
        self.ui.SendText1.clicked.connect(self.sendText1)
        self.ui.SendText2.clicked.connect(self.sendText2)
        self.ui.SendText3.clicked.connect(self.sendText3)
        self.ui.SendText4.clicked.connect(self.sendText4)
        self.ui.SendText5.clicked.connect(self.sendText5)
        self.ui.SendText6.clicked.connect(self.sendText6)
        self.ui.SendFile.clicked.connect(self.sendFile)

        self.ui.textStr1.returnPressed.connect(self.ui.SendText1.click)
        self.ui.textStr2.returnPressed.connect(self.ui.SendText2.click)
        self.ui.textStr3.returnPressed.connect(self.ui.SendText3.click)
        self.ui.textStr4.returnPressed.connect(self.ui.SendText4.click)
        self.ui.textStr5.returnPressed.connect(self.ui.SendText5.click)
        self.ui.textStr6.returnPressed.connect(self.ui.SendText6.click)
        self.ui.hexStr.returnPressed.connect(self.ui.SendHex.click)

        def paste_file(file):
            if file[0]:
                self.ui.fileStr.setText(file[0])
        self.downloaddir = './'
        self.ui.FileSelect.clicked.connect(
            lambda: paste_file(QtWidgets.QFileDialog().getOpenFileName(directory=self.downloaddir)))

        self.showPorts()

        # -----------------------------------------------------------------
        # Platform tweaks
        # -----------------------------------------------------------------
        if sys.platform == 'darwin':
            self.raise_()
        else:
            tab = self.activeTab()
            if tab:
                font = tab.Console.font()
                if sys.platform[:5] == 'linux':
                    font.setFamily(_fromUtf8("Andale Mono"))
                font.setPointSize(font.pointSize() - 3)
                tab.Console.setFont(font)

        # -----------------------------------------------------------------
        # Auto-load on startup
        # -----------------------------------------------------------------
        if self.settings.value(self.ui.Auto_Load.objectName()):
            self.load_settings()

    # =====================================================================
    # Port-tab management
    # =====================================================================

    def _onFocusChanged(self, _old, new):
        """Track whichever PortTab most recently held keyboard focus."""
        w = new
        while w:
            if isinstance(w, PortTab):
                self._lastActiveTab = w
                return
            w = w.parent() if hasattr(w, 'parent') else None

    def activeTab(self):
        """Return the PortTab with current or most recently held focus.

        When focus is inside a PortTab (e.g. the Console text area) return it
        directly.  When focus is elsewhere — e.g. in a Send Text field — return
        the last PortTab that had focus so sends go to the right window.
        """
        # Is focus currently inside a PortTab?
        w = QtWidgets.QApplication.focusWidget()
        while w:
            if isinstance(w, PortTab):
                return w
            w = w.parent() if hasattr(w, 'parent') else None
        # Focus is in the tools panel or elsewhere — use last focused terminal.
        if self._lastActiveTab is not None:
            return self._lastActiveTab
        # Final fallback: current tab in the primary pane.
        w = self.portTabs.currentWidget()
        return w if isinstance(w, PortTab) else None

    def addPortTab(self, label=None, target_pane=None):
        """Create a new PortTab and add it to target_pane (or the active pane)."""
        tab = PortTab(self.serialHub, self)
        tab.Console.installEventFilter(self)
        tab.Console.viewport().installEventFilter(self)
        tab.portChanged.connect(self._showPortUpdate)

        if not isinstance(label, str) or not label:
            label = "Port %d" % (self.portTabs.count() + 1)

        self.portTabs.addTab(tab, label, pane=target_pane)

        ports = [p.name for p in self.serialHub.all_ports()]
        tab.updatePortList(ports)
        return tab

    def _closePortTab(self, pane, local_idx):
        """Close a specific tab; keep at least one tab total."""
        if self.portTabs.count() <= 1:
            return
        tab = pane.widget(local_idx)
        if isinstance(tab, PortTab) and tab.console.is_open():
            tab.console.close()
        pane.removeTab(local_idx)
        if pane.count() == 0 and self.portTabs.paneCount() > 1:
            self.portTabs.removePane(pane)
        if isinstance(tab, PortTab):
            tab.deleteLater()

    def _onPortTabChanged(self, _index):
        """Route global messages to the newly visible tab."""
        tab = self.activeTab()
        if tab:
            setTextOutput(tab.messageOut)

    # =====================================================================
    # Message routing (global note/warning/error → active tab)
    # =====================================================================

    def messageOut(self, text, style=''):
        """note()/warning()/error() land here from any thread (e.g. the
        background serial reader/poller threads on disconnect) — emit a real
        Qt signal so the actual widget lookup below always runs on the GUI
        thread instead of touching Qt/AppKit off-thread (which can hang the
        app with a spinning beachball on macOS)."""
        self._messageSignal.emit(text, style)

    def _doMessageOut(self, text, style=''):
        tab = self.activeTab()
        if tab:
            tab.messageOut(text, style)

    # =====================================================================
    # Port-list management
    # =====================================================================

    # =====================================================================
    # IP ping
    # =====================================================================

    def _buildPingWidget(self):
        """Add an IP-ping row to the Console tab, above the expanding spacer."""
        import subprocess as _sp
        self._subprocess = _sp           # keep reference for _doPing

        box = QtWidgets.QGroupBox('Network', self.Window)
        row = QtWidgets.QHBoxLayout(box)
        row.setContentsMargins(6, 4, 6, 4)
        row.setSpacing(4)

        row.addWidget(QtWidgets.QLabel('Ping:', box))

        self._pingAddr = QtWidgets.QLineEdit(box)
        self._pingAddr.setPlaceholderText('IP address or hostname')
        self._pingAddr.returnPressed.connect(self._doPing)
        row.addWidget(self._pingAddr, 1)

        pingBtn = QtWidgets.QPushButton('Ping', box)
        pingBtn.clicked.connect(self._doPing)
        self._pingBtn = pingBtn
        row.addWidget(pingBtn)

        # Coloured dot: grey=idle, amber=running, green=ok, red=fail
        self._pingDot = QtWidgets.QLabel('●', box)
        self._pingDot.setFixedWidth(16)
        self._pingDot.setAlignment(QtCore.Qt.AlignCenter)
        self._pingDot.setStyleSheet('color: #505050; font-size: 14px;')
        self._pingDot.setToolTip('Ping status')
        row.addWidget(self._pingDot)

        # Insert after Tools (groupBox_7 is index 0 in verticalLayout_9)
        self.ui.verticalLayout_9.insertWidget(1, box)

        self._pingResult.connect(self._onPingResult)

    def _doPing(self):
        addr = self._pingAddr.text().strip()
        if not addr:
            return
        self._pingBtn.setEnabled(False)
        self._pingDot.setStyleSheet('color: #d08000; font-size: 14px;')  # amber
        self._pingDot.setToolTip('Pinging %s …' % addr)

        sp = self._subprocess
        def do_ping():
            try:
                # macOS: -c 1 count, -t 2 timeout in seconds
                r = sp.run(
                    ['ping', '-c', '1', '-t', '2', addr],
                    capture_output=True, timeout=5)
                if r.returncode == 0:
                    # Extract round-trip time from output, e.g. "time=1.23 ms"
                    out = r.stdout.decode(errors='ignore')
                    rtt = ''
                    for token in out.split():
                        if token.startswith('time='):
                            rtt = token[5:]   # e.g. "1.23"
                            break
                    self._pingResult.emit(True, rtt + ' ms' if rtt else 'ok')
                else:
                    self._pingResult.emit(False, 'no reply')
            except Exception as e:
                self._pingResult.emit(False, str(e))

        Thread(target=do_ping, daemon=True).start()

    def _onPingResult(self, success, detail):
        self._pingBtn.setEnabled(True)
        if success:
            self._pingDot.setStyleSheet('color: #00bb44; font-size: 14px;')  # green
            self._pingDot.setToolTip('Reachable — %s' % detail)
        else:
            self._pingDot.setStyleSheet('color: #dd2222; font-size: 14px;')  # red
            self._pingDot.setToolTip('Unreachable — %s' % detail)

    def _showPortUpdate(self):
        self.showPortSignal.emit()

    def showPorts(self):
        self.portlistMutex.lock()
        try:
            ports = [p.name for p in self.serialHub.all_ports()]
            for tab, _lbl in self.portTabs.allTabs():
                if isinstance(tab, PortTab):
                    tab.updatePortList(ports)
            self.serialPortUpdate.emit(ports)
        finally:
            self.portlistMutex.unlock()

    # =====================================================================
    # Keyboard / event filter  (routes to active tab)
    # =====================================================================

    def eventFilter(self, obj, event):
        # Key events in a QPlainTextEdit go to the viewport, so we cannot
        # check `obj is tab.Console`.  Since the filter is only installed on
        # Console widgets (and their viewports), any KeyPress that reaches
        # here belongs to one of them — route it to the active tab.
        if event.type() == QtCore.QEvent.KeyPress:
            key = event.text()
            if key:
                tab = self.activeTab()
                if tab:
                    tab.keyin(key)
                    return True
        return super().eventFilter(obj, event)

    # =====================================================================
    # Find / Clear
    # =====================================================================

    def findText(self):
        tab = self.activeTab()
        if not tab:
            return
        try:
            text = self.ui.FindText.text()
            backwards = bool(self.ui.FindBackwards.checkState())
            tab.findText(text, backwards)
        except Exception as e:
            print(e, file=sys.stderr)
            traceback.print_exc(file=sys.stderr)

    def _clearConsole(self):
        tab = self.activeTab()
        if tab:
            tab.Console.clear()

    # =====================================================================
    # Send helpers  (operate on active tab)
    # =====================================================================

    def sendHex(self):
        tab = self.activeTab()
        if not tab:
            return
        try:
            text = self.ui.hexStr.text()
            if text:
                tab.top.output.emit(bytes.fromhex(text))
        except Exception as e:
            print(e)
            error('bad hex string')
            traceback.print_exc(file=sys.stderr)

    def _sendText(self, text):
        tab = self.activeTab()
        if not tab:
            return
        try:
            if text:
                tab.keyin(text + '\n')
        except Exception:
            error('bad text string')
            traceback.print_exc(file=sys.stderr)

    def sendText1(self): self.ui.textStr1.record(); self._sendText(self.ui.textStr1.text())
    def sendText2(self): self.ui.textStr2.record(); self._sendText(self.ui.textStr2.text())
    def sendText3(self): self.ui.textStr3.record(); self._sendText(self.ui.textStr3.text())
    def sendText4(self): self.ui.textStr4.record(); self._sendText(self.ui.textStr4.text())
    def sendText5(self): self.ui.textStr5.record(); self._sendText(self.ui.textStr5.text())
    def sendText6(self): self.ui.textStr6.record(); self._sendText(self.ui.textStr6.text())

    def sendFile(self):
        tab = self.activeTab()
        if not tab:
            return
        for line in open(self.ui.fileStr.text(), 'r').readlines():
            self._sendText(line)

    # =====================================================================
    # Window title
    # =====================================================================

    def banner(self):
        self.Window.setWindowTitle(appname + version)

    # =====================================================================
    # Shutdown
    # =====================================================================

    def closeEvent(self, event):
        """Close all open ports in parallel before the window goes away."""
        open_tabs = [t for t, _ in self.portTabs.allTabs()
                     if isinstance(t, PortTab) and t.console.is_open()]
        if open_tabs:
            closers = [Thread(target=t.console.close, daemon=True) for t in open_tabs]
            for c in closers: c.start()
            for c in closers: c.join(timeout=3.0)   # never hang on exit
        event.accept()

    # =====================================================================
    # Settings  — save / load
    # =====================================================================

    def save_settings(self):
        self.settings.clear()
        self.settings.setValue('Window Geometry', self.Window.geometry())

        # Shared tool strings
        self.settings.setValue(self.ui.hexStr.objectName(),   self.ui.hexStr.text())
        self.settings.setValue(self.ui.textStr1.objectName(), self.ui.textStr1.text())
        self.settings.setValue(self.ui.textStr2.objectName(), self.ui.textStr2.text())
        self.settings.setValue(self.ui.textStr3.objectName(), self.ui.textStr3.text())
        self.settings.setValue(self.ui.textStr4.objectName(), self.ui.textStr4.text())
        self.settings.setValue(self.ui.fileStr.objectName(),  self.ui.fileStr.text())

        # Tabs (main left panel) and misc
        self.settings.setValue(self.ui.Auto_Load.objectName(), self.ui.Auto_Load.isChecked())

        # Port tabs — flat list with pane membership + full splitter tree
        all_tabs = self.portTabs.allTabsWithPane()
        self.settings.setValue('portTabs/count',     len(all_tabs))
        self.settings.setValue('portTabs/paneCount', self.portTabs.paneCount())
        self.settings.setValue('portTabs/layout',    self.portTabs.saveLayout())
        for i, (tab, label, pane_idx) in enumerate(all_tabs):
            prefix = 'portTabs/%d/' % i
            self.settings.setValue(prefix + 'label',     label)
            self.settings.setValue(prefix + 'paneIndex', pane_idx)
            if isinstance(tab, PortTab):
                tab.saveToSettings(self.settings, prefix)

        # Ping address
        self.settings.setValue('pingAddr', self._pingAddr.text())


    def load_settings(self):
        try:
            # Shared tool strings
            self.ui.hexStr.setText(   self.settings.value(self.ui.hexStr.objectName()))
            self.ui.textStr1.setText( self.settings.value(self.ui.textStr1.objectName()))
            self.ui.textStr2.setText( self.settings.value(self.ui.textStr2.objectName()))
            self.ui.textStr3.setText( self.settings.value(self.ui.textStr3.objectName()))
            self.ui.textStr4.setText( self.settings.value(self.ui.textStr4.objectName()))
            self.ui.fileStr.setText(  self.settings.value(self.ui.fileStr.objectName()))
            self.Window.setGeometry(  self.settings.value('Window Geometry'))
            self.ui.Auto_Load.setChecked(
                self.settings.value(self.ui.Auto_Load.objectName(), type=bool))

            self._pingAddr.setText(self.settings.value('pingAddr', ''))

            count = self.settings.value('portTabs/count', type=int) or 1

            # Close all open ports in parallel so N ports take ~200 ms, not N×200 ms
            all_existing = list(self.portTabs.allTabs())
            open_tabs = [t for t, _ in all_existing
                         if isinstance(t, PortTab) and t.console.is_open()]
            if open_tabs:
                closers = [Thread(target=t.console.close, daemon=True) for t in open_tabs]
                for c in closers: c.start()
                for c in closers: c.join(timeout=3.0)   # cap wait per port
            for tab, _ in all_existing:
                if isinstance(tab, PortTab):
                    tab.deleteLater()

            # Rebuild the pane layout from scratch
            self.portTabs.resetLayout()

            # 1. Create tabs and place each in the correct pane
            for i in range(count):
                prefix   = 'portTabs/%d/' % i
                label    = self.settings.value(prefix + 'label',     'Port %d' % (i + 1))
                pane_idx = int(self.settings.value(prefix + 'paneIndex', 0) or 0)
                pane     = self.portTabs.paneAt(pane_idx)
                tab      = self.addPortTab(label=label, target_pane=pane)
                tab.loadFromSettings(self.settings, prefix)

            # 2. Restore the splitter tree (pane positions / nesting / orientation)
            self.portTabs.applyLayout(self.settings.value('portTabs/layout', ''))

        except TypeError:
            print("Error: some settings haven't been set!")
            self.save_settings()


# =========================================================================
# Entry point
# =========================================================================
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)

    # Splash screen
    splash_pix = QtGui.QPixmap(420, 220)
    splash_pix.fill(QtGui.QColor("#2b2b2b"))
    painter = QtGui.QPainter(splash_pix)
    painter.setPen(QtGui.QColor("white"))
    titleFont = QtGui.QFont()
    titleFont.setPointSize(20)
    titleFont.setBold(True)
    painter.setFont(titleFont)
    painter.drawText(
        splash_pix.rect().adjusted(0, -30, 0, -30),
        QtCore.Qt.AlignCenter, appname + version)
    msgFont = QtGui.QFont()
    msgFont.setPointSize(11)
    painter.setFont(msgFont)
    painter.drawText(
        splash_pix.rect().adjusted(0, 30, 0, 30),
        QtCore.Qt.AlignCenter, "Starting up, please wait...")
    painter.end()
    splash = QtWidgets.QSplashScreen(splash_pix)
    splash.show()
    app.processEvents()

    term = terminal()
    splash.finish(term.Window)

    try:
        sys.exit(app.exec_())
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
