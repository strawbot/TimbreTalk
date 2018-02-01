# test panel for qtran  Robert Chapman III  Oct 24, 2012

from pyqtapi2 import *
import time, datetime
from message import *
from protocols import pids
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

        # monitor ports - should make a common class and instantiate multiple times
        self.sptimer = QTimer()
        self.portname1 = None
        self.portname2 = None
        self.monitorPort1 = serialio.serialPort(int(self.ui.MonitorBaud1.currentText()))
        self.monitorPort2 = serialio.serialPort(int(self.ui.MonitorBaud2.currentText()))
        self.selectFormat1()
        self.selectFormat2()
        self.listPorts()

        self.ui.MonitorPort1.activated.connect(self.selectPort1)
        self.ui.MonitorPort2.activated.connect(self.selectPort2)
        self.ui.MonitorBaud1.activated.connect(self.selectRate1)
        self.ui.MonitorBaud2.activated.connect(self.selectRate2)
        self.ui.monitorFormat1.activated.connect(self.selectFormat1)
        self.ui.monitorFormat2.activated.connect(self.selectFormat2)

    def selectMicro(self):
        if self.ui.microSelect.currentText() == "STM32F4":
            self.micro = stmTransfer(self)
        elif self.ui.microSelect.currentText() == "EFM32":
            self.micro = efmTransfer(self)
        else:
            print("No micro available. Don't know: %s"%self.ui.microSelect.currentText())

    # monitor ports
    def listPorts(self):
        select, disc = '(Select a Port)', '(Disconnect)'

        uiPort1 = self.ui.MonitorPort1
        uiPort2 = self.ui.MonitorPort2
        items = [uiPort1.itemText(i) for i in range(1, uiPort1.count())]
        ports = listports.listports()
        ports = [p for p in ports if listports.jlink not in p]

        for r in list(set(items)-set(ports)): # items to be removed
            uiPort1.removeItem(uiPort1.findText(r))
            uiPort2.removeItem(uiPort2.findText(r))
        for a in list(set(ports)-set(items)): # items to be added
            uiPort1.addItem(a)
            uiPort2.addItem(a)

        if self.portname1:
            if self.portname1 != uiPort1.currentText():
                index = uiPort1.findText(self.portname1)
                if index == -1:
                    index = 0
                    self.portname1 = None
                uiPort1.setCurrentIndex(index)

        if self.portname2:
            if self.portname2 != uiPort2.currentText():
                index = uiPort2.findText(self.portname2)
                if index == -1:
                    index = 0
                    self.portname2 = None
                uiPort2.setCurrentIndex(index)

        text = disc if uiPort1.currentIndex() else select
        if uiPort1.itemText(0) != text:
            uiPort1.setItemText(0, text)
        text = disc if uiPort2.currentIndex() else select
        if uiPort2.itemText(0) != text:
            uiPort2.setItemText(0, text)

        self.sptimer.singleShot(1000, self.listPorts)

    def selectRate1(self):
        self.monitorPort1.setRate(int(self.ui.MonitorBaud1.currentText()))

    def selectRate2(self):
        self.monitorPort2.setRate(int(self.ui.MonitorBaud2.currentText()))

    def selectPort1(self):
        if self.monitorPort1.isOpen():
            self.monitorPort1.close()
        if self.ui.MonitorPort1.currentIndex():
            self.portname1 = self.ui.MonitorPort1.currentText()
            self.monitorPort1.open(self.portname1, self.monitorPort1.rate)
            if self.monitorPort1.isOpen():
                self.monitorPort1.closed.connect(self.serialDone)
                self.monitorPort1.ioError.connect(self.ioError)
                self.monitorPort1.ioException.connect(self.ioError)
                self.connectPort1()
            else:
                self.ui.MonitorPort1.setCurrentIndex(0)
                self.portname1 = None
        else:
            self.portname1 = None

    def selectPort2(self):
        if self.monitorPort2.isOpen():
            self.monitorPort2.close()
        if self.ui.MonitorPort2.currentIndex():
            self.portname2 = self.ui.MonitorPort2.currentText()
            self.monitorPort2.open(self.portname2, self.monitorPort2.rate)
            if self.monitorPort2.isOpen():
                self.monitorPort2.closed.connect(self.serialDone)
                self.monitorPort2.ioError.connect(self.ioError)
                self.monitorPort2.ioException.connect(self.ioError)
                self.connectPort2()
            else:
                self.ui.MonitorPort2.setCurrentIndex(0)
                self.portname2 = None
        else:
            self.portname1 = None

    def selectFormat1(self):
        self.format1 = self.ui.monitorFormat1.currentText()

    def selectFormat2(self):
        self.format2 = self.ui.monitorFormat2.currentText()

    def serialDone(self):
        note('Serial thread finished')

    def ioError(self, message):
        error(message)

    def connectPort1(self): # override in children
        self.monitorPort1.source.connect(self.sink1)
        # self.setParam(self.monitorPort1, 'E', 8, 1)

    def connectPort2(self): # override in children
        self.monitorPort2.source.connect(self.sink2)
        # self.setParam(self.monitorPort2, 'E', 8, 1)

    def sink1(self, s):
        ts = self.timestamp()
        if self.format1 == 'ASCII':
            text = ''.join([c if c >= ' ' and c <= '~' else '<'+hex(ord(c))[2:]+'>' for c in s])
        else:
            text = ''.join(map(lambda x: ' '+hex(ord(x))[2:],  s))
        message('\n1 '+ts+text, self.ui.Color1.currentText())

    def sink2(self, s):
        ts = self.timestamp()
        if self.format2 == 'ASCII':
            text = ''.join([c if c >= ' ' and c <= '~' else '<'+hex(ord(c))[2:]+'>' for c in s])
        else:
            text = ''.join(map(lambda x: ' '+hex(ord(x))[2:],  s))
        message('\n2 '+ts+text, self.ui.Color2.currentText())

    def setParam(self, sp, parity, bytesize, stopbits):
        if sp.port:
            sp.port.setParity(parity)
            sp.port.setByteSize(bytesize)
            sp.port.setStopbits(stopbits)

    def timestamp(self):
        ms = current_milli_time()
        return "%d.%03d: "%(ms/1000,ms%1000)

    def setDateTimeNow(self):
        n = datetime.datetime.now()
        cmd = "%d %d %d setdate %d %d %d settime date"% \
               (n.year%100, n.month, n.day, n.hour, n.minute, n.second)
        payload = map(ord, cmd) + [0]
        self.protocol.sendNPS(pids.EVAL_PID, self.parent.who() + payload)

    def crcStatus(self, flag):
        self.ui.crcValue.setText('%08X' % self.eeprom.scriptCrc)
        self.ui.crcStatus.setText('ok' if flag else 'bad')
