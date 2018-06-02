# test panel for qtran  Robert Chapman III  Oct 24, 2012

from pyqtapi2 import *
import time, datetime
from message import *
from protocols import sfp, pids
from endian import *
from image import *
import listports, serialio
from microTransfer import stmTransfer, efmTransfer
from jamTransfer import jamSender
from eepromTransfer import eepromTransfer
from configTransfer import configTransfer

current_milli_time = lambda: int(round(time.time() * 1000))

printme = 0

#, sector, address,, size
sectors = [[0, 0x08000000, 16],
            [1, 0x08004000, 16],
            [2, 0x08008000, 16],
            [3, 0x0800C000, 16],
            [4, 0x08010000, 64],
            [5, 0x08020000, 128],
            [6, 0x08040000, 128],
            [7, 0x08060000, 128],
            [8, 0x08080000, 128],
            [9, 0x080A0000, 128],
            [10, 0x080C0000, 128],
            [11, 0x080E0000, 128],
            [12, 0x08100000, 16],
            [13, 0x08104000, 16],
            [14, 0x08108000, 16],
            [15, 0x0810C000, 16],
            [16, 0x08110000, 64],
            [17, 0x08120000, 128],
            [18, 0x08140000, 128],
            [19, 0x08160000, 128],
            [20, 0x08180000, 128],
            [21, 0x081A0000, 128],
            [22, 0x081C0000, 128],
            [23, 0x081E0000, 128]]

class utilityPane(QWidget):
    def __init__(self, parent):
        QWidget.__init__(self, parent)
        self.parent = parent
        self.ui = parent.ui
        self.protocol = parent.protocol
        self.startTransferTime = 0
        self.image = None
        self.dir = ''
        self.micro = None

        # config file transfer
        self.config = configTransfer(self)
        self.config.setName.connect(self.ui.configFileName.setText)
        self.ui.configFileName.editingFinished.connect(lambda: self.config.updateName(self.ui.configFileName.text()))
        self.config.setSize.connect(self.ui.configFileSize.setText)
        self.ui.configFileSelect.clicked.connect(
            lambda: self.config.selectFile(QFileDialog().getOpenFileName(directory=self.config.dir)))
        self.ui.configFileToSL.clicked.connect(self.config.sendFile)
        self.ui.configFileProgressBar.reset()
        self.ui.configFileProgressBar.setMaximum(1000)
        self.config.setProgress.connect(lambda n: self.ui.configFileProgressBar.setValue(n * 1000))
        self.config.setAction.connect(lambda: self.ui.configFileToSL.setText)
        self.ui.configFileToHost.clicked.connect(lambda: self.config.requestFile(self.ui.configFileName.text()))

        # micro Boot Loader: STM32F4 & EFM32GG
        self.selectMicro()
        self.ui.microSelect.activated.connect(self.selectMicro)
        self.ui.microSelect.currentIndexChanged.connect(self.selectMicro)
        self.micro.setName.connect(self.ui.bootFile.setText)
        self.micro.setSize.connect(self.ui.bootSize.setText)
        self.ui.bootSelect.clicked.connect(lambda: self.micro.selectFile(QFileDialog().getOpenFileName(directory=self.micro.dir)))
        self.ui.sendBoot.clicked.connect(self.micro.sendFile)
        self.ui.bootLoaderProgressBar.reset()
        self.ui.bootLoaderProgressBar.setMaximum(1000)
        self.micro.setProgress.connect(lambda n: self.ui.bootLoaderProgressBar.setValue(n*1000))
        self.micro.setAction.connect(lambda text: self.ui.sendBoot.setText(text))
        self.micro.verbose = self.ui.verbose.isChecked()
        self.ui.verbose.stateChanged.connect(self.micro.setVerbose)
        self.micro.run = self.ui.run.isChecked()
        self.ui.run.stateChanged.connect(self.micro.setRun)
        self.micro.setStart.connect(lambda a: self.ui.bootStart.setText(a))
        self.ui.bootStart.textChanged.connect(lambda t: self.micro.address)
        self.ui.Go.clicked.connect(self.micro.goButton)
        self.ui.autobaud.clicked.connect(lambda: self.micro.send('U'))
        self.ui.resetEfm32.clicked.connect(lambda: self.micro.send('r'))
        self.ui.getFlashCRC.clicked.connect(lambda: self.micro.send('v'))
        self.ui.getApplCRC.clicked.connect(lambda: self.micro.send('c'))
        self.ui.exitDownload.clicked.connect(self.micro.exitDownload)

        self.ui.setDateTime.clicked.connect(self.setDateTimeNow)

        # send jam file
        self.jam = jamSender(self)
        self.jam.setName.connect(self.ui.jamFile.setText)
        self.jam.setSize.connect(self.ui.jamSize.setText)
        self.ui.jamSelect.clicked.connect(lambda: self.jam.selectFile(QFileDialog().getOpenFileName(directory=self.jam.dir)))
        self.ui.sendJam.clicked.connect(self.jam.sendJam)
        self.ui.sendFile.clicked.connect(self.jam.sendFile)
        self.ui.jamLoaderProgressBar.reset()
        self.ui.jamLoaderProgressBar.setMaximum(1000)
        self.jam.setProgress.connect(lambda n: self.ui.jamLoaderProgressBar.setValue(n*1000))
        self.jam.setAction.connect(lambda: self.ui.sendJam.setText)

        # Transfer EEPROM Script
        self.eeprom = eepromTransfer(self)
        self.eeprom.setName.connect(self.ui.eepromFile.setText)
        self.eeprom.setSize.connect(self.ui.eepromSize.setText)
        self.ui.eepromSelect.clicked.connect(lambda: self.eeprom.selectFile(QFileDialog().getOpenFileName(directory=self.eeprom.dir)))
        self.ui.sendEeprom.clicked.connect(self.eeprom.sendFile)
        self.ui.eepromLoaderProgressBar.reset()
        self.ui.eepromLoaderProgressBar.setMaximum(1000)
        self.eeprom.setProgress.connect(lambda n: self.ui.eepromLoaderProgressBar.setValue(n*1000))
        self.eeprom.setAction.connect(lambda: self.ui.sendEeprom.setText)
        self.eeprom.scriptOk.connect(self.crcStatus)
        self.eeprom.imageLoaded.connect(self.eeprom.checkScriptCrc)

        # monitor ports
        self.portMonitor1 = portMonitor(1,
        								self.ui.MonitorPort1,
                                        self.ui.MonitorBaud1,
                                        self.ui.MonitorColor1,
                                        self.ui.MonitorFormat1)
        self.portMonitor2 = portMonitor(2,
        								self.ui.MonitorPort2,
                                        self.ui.MonitorBaud2,
                                        self.ui.MonitorColor2,
                                        self.ui.MonitorFormat2)

        self.monitors = [self.portMonitor1, self.portMonitor2]

        self.sptimer = QTimer()
        self.listPorts()

    def setDateTimeNow(self):
        n = datetime.datetime.now()
        cmd = "%d %d %d setdate %d %d %d settime date"% \
               (n.year%100, n.month, n.day, n.hour, n.minute, n.second)
        payload = map(ord, cmd) + [0]
        self.protocol.sendNPS(pids.EVAL_PID, self.parent.who() + payload)

    def crcStatus(self, flag):
        self.ui.crcValue.setText('%08X' % self.eeprom.scriptCrc)
        self.ui.crcStatus.setText('ok' if flag else 'bad')

    def selectMicro(self):
        if self.ui.microSelect.currentText() == "STM32F4":
            self.micro = stmTransfer(self)
        elif self.ui.microSelect.currentText() == "EFM32":
            self.micro = efmTransfer(self)
        else:
            print("No micro available. Don't know: %s"%self.ui.microSelect.currentText())

    # get list of current ports
    # go through combobox and add and remove items for each monitor
    # check each monitor selection and if item no longer applicable, change portname to None
    def listPorts(self):
        select, disc = '(Select a Port)', '(Disconnect)'

        ports = listports.listports()
        port = self.monitors[0].port
        items = [port.itemText(i) for i in range(1, port.count())]

        for monitor in self.monitors:
            uiPort = monitor.port
            for r in list(set(items)-set(ports)): # items to be removed
                uiPort.removeItem(uiPort.findText(r))
            for a in list(set(ports)-set(items)): # items to be added
                uiPort.addItem(a)

            if monitor.portname:
                if monitor.portname != uiPort.currentText():
                    index = uiPort.findText(monitor.portname)
                    if index == -1:
                        index = 0
                        monitor.portname = None
                    uiPort.setCurrentIndex(index)

            text = disc if uiPort.currentIndex() else select
            if uiPort.itemText(0) != text:
                uiPort.setItemText(0, text)

        self.sptimer.singleShot(1000, self.listPorts)

# utilities
def isAscii(c):
	return c >= ' ' and c <= '~'

def toHex(c):
	return '<' + hex(ord(c))[2:] + '>'

def asciify(s):
	return ''.join([c if isAscii(c) else toHex(c) for c in s])

def hexify(s):
	return ''.join(map(lambda x: ' ' + hex(ord(x))[2:], s))

class portMonitor(QObject):
    def __init__(self, whoami, port, baud, color, format):
        QObject.__init__(self)
        self.sfp = sfp.sfpProtocol()

        self.port = port
        self.baud = baud
        self.color = color.currentText
        self.format = format

        self.port.activated.connect(self.selectPort)
        self.baud.activated.connect(self.selectRate)
        
        self.sfp.newPacket = self.distributer
        self.serial = serialio.serialPort(int(self.baud.currentText()))
        self.portname = None
        self.whoami = whoami

    def distributer(self):  # distribute packets from queue
        if not self.sfp.receivedPool.empty():
            packet = self.sfp.receivedPool.get()
            pid = packet[0]
            if pids.pids.get(pid):
                self.text("Packet: {} {}".format(pids.pids[pid], asciify(map(chr, packet[1:]))))
            else:
                error("Unknown PID: (0x{:02x})".format(pid))

    def selectRate(self):
        self.port.setRate(int(self.baud.currentText()))

    def selectPort(self):
        if self.serial.isOpen():
            self.serial.close()
        if self.port.currentIndex():
            self.portname = self.port.currentText()
            self.serial.open(self.portname, self.serial.rate)
            if self.serial.isOpen():
                self.serial.closed.connect(self.serialDone)
                self.serial.ioError.connect(self.ioError)
                self.serial.ioException.connect(self.ioError)
                self.connectPort()
            else:
                self.port.setCurrentIndex(0)
                self.portname = None
        else:
            self.portname = None

    def serialDone(self):
        note('{}: serial thread finished'.format(self.portname))

    def ioError(self, message):
        error(message)

    def connectPort(self):  # override in children
        self.serial.source.connect(self.sink)

    def text(self, text):
        message('\n{} '.format(self.whoami) + self.timestamp() + text, self.color())

    def sink(self, s):
        format = self.format.currentText()
        if format == 'ASCII':
            self.text(asciify(s))
        elif format == 'SFP':
            self.sfp.rxBytes(map(ord, s))
        else:
            self.text(hexify(s))

    def timestamp(self):
        ms = current_milli_time()
        return "%d.%03d: " % (ms / 1000, ms % 1000)
