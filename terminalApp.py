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
from protocols import send_os
from threading import Thread
from protocols.interface.message import note, warning, error, setTextOutput, eprint

from terminal import Ui_Frame
from monitor import portMonitor, updatePortCombo
from portcombo import PortCombo
from baudcombo import BaudCombo
from colorcombo import ColorCombo
from formatcombo import FormatCombo
from monitorframe import MonitorFrame
from porttab import PortTab

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s

appname = "TimbreTalk "
version = "V4"


class terminal(QtWidgets.QMainWindow):
    showPortSignal  = QtCore.pyqtSignal()
    serialPortUpdate = QtCore.pyqtSignal(object)
    settings = QtCore.QSettings("TWE", "Tiny Timbre Talk")
    setProgress = QtCore.pyqtSignal(object)

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

        # Hide the old single-port controls — they now live inside each PortTab.
        self.ui.groupBox_8.hide()

        # -----------------------------------------------------------------
        # Port-tab container (replaces the single Console on the right side)
        # -----------------------------------------------------------------
        self.portTabs = QtWidgets.QTabWidget()
        self.portTabs.setTabsClosable(True)
        self.portTabs.setMovable(True)
        self.portTabs.tabCloseRequested.connect(self._closePortTab)
        self.portTabs.currentChanged.connect(self._onPortTabChanged)
        self.portTabs.tabBar().tabBarDoubleClicked.connect(self._renamePortTab)

        # "+" corner button to add a new port tab
        # QToolButton renders correctly as a corner widget on macOS
        addBtn = QtWidgets.QToolButton()
        addBtn.setText("+")
        addBtn.setToolTip("New port tab")
        addBtn.clicked.connect(lambda: self.addPortTab())
        self.portTabs.setCornerWidget(addBtn, QtCore.Qt.TopRightCorner)

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
            for i in range(self.portTabs.count()):
                self.portTabs.widget(i).linedelay = delay
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
        self.ui.SendFile.clicked.connect(self.sendFile)

        self.ui.textStr1.returnPressed.connect(self.ui.SendText1.click)
        self.ui.textStr2.returnPressed.connect(self.ui.SendText2.click)
        self.ui.textStr3.returnPressed.connect(self.ui.SendText3.click)
        self.ui.textStr4.returnPressed.connect(self.ui.SendText4.click)
        self.ui.hexStr.returnPressed.connect(self.ui.SendHex.click)

        def paste_file(file):
            if file[0]:
                self.ui.fileStr.setText(file[0])
        self.ui.FileSelect.clicked.connect(
            lambda: paste_file(QtWidgets.QFileDialog().getOpenFileName(directory=self.downloaddir)))

        # -----------------------------------------------------------------
        # Monitor tab
        # -----------------------------------------------------------------
        for widget in self.ui.PortMonitors_tab.findChildren(MonitorFrame):
            port     = widget.findChildren(PortCombo)[0]
            baud     = widget.findChildren(BaudCombo)[0]
            color    = widget.findChildren(ColorCombo)[0]
            protocol = widget.findChildren(FormatCombo)[0]
            mname    = widget.findChildren(QtWidgets.QLineEdit)[0]
            pm = portMonitor(port, baud, mname, protocol, color)
            pm.monitorOut.connect(self.messageOut)
            pm.monitorOut.emit(mname.text(), 'white')

        self.serialPortUpdate.connect(portMonitor.updatePortList)
        self.ui.SavePortMonitor.clicked.connect(self.save_settings)
        self.ui.LoadPortMonitor.clicked.connect(self.load_settings)

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
        # Transfer / Download tab
        # -----------------------------------------------------------------
        self.downloaddir = './'

        def download_app():
            tab = self.activeTab()
            if not tab:
                return
            send_os.FW_FILE = self.ui.Download_File.text()
            self.messageOut('\nStarting download...', 'note')
            tab.console.close()
            self.ui.progressBar.setValue(0)

            def send_thread():
                ts = time.time()
                def notifier(i, mx):
                    nonlocal ts
                    if time.time() - ts > 1:
                        ts = time.time()
                        self.setProgress.emit(100 * i // mx)
                if send_os.send_os(tab.console.name, notifier):
                    self.messageOut('\nDownload successful.', 'note')
                    self.ui.progressBar.setValue(100)
                else:
                    self.messageOut('\nDownload failed.', 'error')
                    self.ui.progressBar.setValue(0)
                tab.console.open()
                tab.connectPort()

            self.setProgress.connect(lambda n: self.ui.progressBar.setValue(n))
            t = Thread(name='send OS', target=send_thread, daemon=True)
            t.start()

        def select_file(file):
            if file[0]:
                self.ui.Download_File.setText(file[0])

        self.ui.progressBar.setValue(0)
        self.ui.Start_Download.clicked.connect(download_app)
        self.ui.Select_Download.clicked.connect(
            lambda: select_file(QtWidgets.QFileDialog().getOpenFileName()))

        # -----------------------------------------------------------------
        # Auto-load on startup
        # -----------------------------------------------------------------
        if self.settings.value(self.ui.Auto_Load.objectName()):
            self.load_settings()

    # =====================================================================
    # Port-tab management
    # =====================================================================

    def activeTab(self):
        """Return the currently visible PortTab, or None."""
        w = self.portTabs.currentWidget()
        return w if isinstance(w, PortTab) else None

    def addPortTab(self, label=None):
        """Create and append a new PortTab; return it."""
        tab = PortTab(self.serialHub, self)
        # Install on both the widget and its viewport: key events in a
        # QPlainTextEdit go to the viewport child, not the widget itself.
        tab.Console.installEventFilter(self)
        tab.Console.viewport().installEventFilter(self)
        tab.portChanged.connect(self._showPortUpdate)

        if not isinstance(label, str) or not label:
            label = "Port %d" % (self.portTabs.count() + 1)

        idx = self.portTabs.addTab(tab, label)
        self.portTabs.setCurrentIndex(idx)

        # Populate port list for the new tab immediately
        ports = [p.name for p in self.serialHub.all_ports()]
        tab.updatePortList(ports)

        return tab

    def _closePortTab(self, index):
        """Close a port tab (keep at least one)."""
        if self.portTabs.count() <= 1:
            return
        tab = self.portTabs.widget(index)
        if isinstance(tab, PortTab) and tab.console.is_open():
            tab.console.close()
        self.portTabs.removeTab(index)
        if isinstance(tab, PortTab):
            tab.deleteLater()

    def _renamePortTab(self, index):
        """Double-click tab bar → inline rename dialog."""
        old = self.portTabs.tabText(index)
        name, ok = QtWidgets.QInputDialog.getText(
            self.Window, "Rename Tab", "Tab name:", text=old)
        if ok and name:
            self.portTabs.setTabText(index, name)

    def _onPortTabChanged(self, index):
        """Route global messages to the newly visible tab."""
        tab = self.portTabs.widget(index)
        if isinstance(tab, PortTab):
            setTextOutput(tab.messageOut)

    # =====================================================================
    # Message routing (global note/warning/error → active tab)
    # =====================================================================

    def messageOut(self, text, style=''):
        tab = self.activeTab()
        if tab:
            tab.messageOut(text, style)

    # =====================================================================
    # Port-list management
    # =====================================================================

    def _showPortUpdate(self):
        self.showPortSignal.emit()

    def showPorts(self):
        self.portlistMutex.lock()
        try:
            ports = [p.name for p in self.serialHub.all_ports()]
            for i in range(self.portTabs.count()):
                tab = self.portTabs.widget(i)
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

    def sendText1(self): self._sendText(self.ui.textStr1.text())
    def sendText2(self): self._sendText(self.ui.textStr2.text())
    def sendText3(self): self._sendText(self.ui.textStr3.text())
    def sendText4(self): self._sendText(self.ui.textStr4.text())

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
        self.settings.setValue(self.ui.Tabs.objectName(),     self.ui.Tabs.currentIndex())
        self.settings.setValue(self.ui.Auto_Load.objectName(), self.ui.Auto_Load.isChecked())
        self.settings.setValue(self.ui.Download_File.objectName(), self.ui.Download_File.text())

        # Port tabs
        count = self.portTabs.count()
        self.settings.setValue('portTabs/count', count)
        self.settings.setValue('portTabs/current', self.portTabs.currentIndex())
        for i in range(count):
            tab = self.portTabs.widget(i)
            prefix = 'portTabs/%d/' % i
            self.settings.setValue(prefix + 'label', self.portTabs.tabText(i))
            if isinstance(tab, PortTab):
                tab.saveToSettings(self.settings, prefix)

        # Monitor tab
        portMonitor.save(self.settings)

    def load_settings(self):
        try:
            portMonitor.load(self.settings)

            # Shared tool strings
            self.ui.hexStr.setText(   self.settings.value(self.ui.hexStr.objectName()))
            self.ui.textStr1.setText( self.settings.value(self.ui.textStr1.objectName()))
            self.ui.textStr2.setText( self.settings.value(self.ui.textStr2.objectName()))
            self.ui.textStr3.setText( self.settings.value(self.ui.textStr3.objectName()))
            self.ui.textStr4.setText( self.settings.value(self.ui.textStr4.objectName()))
            self.ui.fileStr.setText(  self.settings.value(self.ui.fileStr.objectName()))
            self.Window.setGeometry(  self.settings.value('Window Geometry'))
            self.ui.Tabs.setCurrentIndex(self.settings.value(self.ui.Tabs.objectName()))
            self.ui.Auto_Load.setChecked(
                self.settings.value(self.ui.Auto_Load.objectName(), type=bool))
            self.ui.Download_File.setText(
                self.settings.value(self.ui.Download_File.objectName()))

            # Restore port tabs
            count = self.settings.value('portTabs/count', type=int) or 1
            current = self.settings.value('portTabs/current', type=int) or 0

            # Remove all current tabs
            while self.portTabs.count():
                w = self.portTabs.widget(0)
                self.portTabs.removeTab(0)
                if isinstance(w, PortTab) and w.console.is_open():
                    w.console.close()
                if isinstance(w, PortTab):
                    w.deleteLater()

            # Recreate saved tabs
            for i in range(count):
                prefix = 'portTabs/%d/' % i
                label  = self.settings.value(prefix + 'label', 'Port %d' % (i + 1))
                tab    = self.addPortTab(label=label)
                tab.loadFromSettings(self.settings, prefix)

            # Restore active tab
            if 0 <= current < self.portTabs.count():
                self.portTabs.setCurrentIndex(current)

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
