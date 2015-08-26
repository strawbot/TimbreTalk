# test panel for qtran  Robert Chapman III  Oct 24, 2012

from pyqtapi2 import *
import time, datetime
from message import *
import sfp, pids
from endian import *
from random import randrange
from image import *
import traceback	
import listports, serialio
from stmTransfer import stmSender
from jamTransfer import jamSender

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

		# printme
		self.setupPrintme()
		
		# load
		self.loadTimer = QTimer()
		self.loadTimer.timeout.connect(self.loadFrame)
		self.loadFrames = 0
		self.ui.loadRun.clicked.connect(self.loadRun)
		
		# STM32F4 Boot Loader
		self.stm = stmSender(self)
		self.stm.setName.connect(self.ui.bootFile.setText)
		self.stm.setSize.connect(self.ui.bootSize.setText)
		self.ui.bootSelect.clicked.connect(lambda: self.stm.selectFile(QFileDialog().getOpenFileName(directory=self.stm.dir)))
		self.ui.sendBoot.clicked.connect(self.stm.sendFile)
		self.ui.bootLoaderProgressBar.reset()
		self.ui.bootLoaderProgressBar.setMaximum(1000)
		self.stm.setProgress.connect(lambda n: self.ui.bootLoaderProgressBar.setValue(n*1000))
		self.stm.setAction.connect(lambda: self.ui.sendBoot.setText)
		self.stm.verbose = self.ui.verbose.isChecked()
		self.ui.verbose.stateChanged.connect(self.stm.setVerbose)
		self.stm.run = self.ui.run.isChecked()
		self.ui.run.stateChanged.connect(self.stm.setRun)
		self.stm.setStart.connect(lambda a: self.ui.bootStart.setText(a))
		self.ui.bootStart.textChanged.connect(lambda t: self.stm.address)
 		self.ui.Go.clicked.connect(self.stm.goButton)
		
# 		self.ui.Boot.clicked.connect(self.listenBoot)
# 		self.ui.Reconnect.clicked.connect(self.noListenBoot)
# 		self.ui.Init.clicked.connect(lambda: self.echoTx([0x7F]))
# 		self.ui.Rdp.clicked.connect(lambda: self.echoTx(self.checked(0x92)))
# 		self.ui.Erase.clicked.connect(lambda: self.echoTx(self.checked(0x44)))
# 		self.ui.Pages.clicked.connect(lambda: self.echoTx(self.checksummed([0xFF,0xFF])))
# 		self.ui.Write.clicked.connect(lambda: self.echoTx(self.checked(0x31)))
# 		self.ui.Address.clicked.connect(lambda: self.echoTx(self.checksummed([8,0,0,0])))
# 		self.ui.Data.clicked.connect(lambda: self.echoTx(self.checksummed([7,1,2,3,4,5,6,7,8])))
# 		self.ui.Get.clicked.connect(lambda: self.echoTx(self.checked(0x0)))
# 		self.ui.Getrpd.clicked.connect(lambda: self.echoTx(self.checked(0x1)))
# 		self.ui.Getid.clicked.connect(lambda: self.echoTx(self.checked(0x2)))

		# send jam file
 		self.jam = jamSender(self)
		self.jam.setName.connect(self.ui.jamFile.setText)
		self.jam.setSize.connect(self.ui.jamSize.setText)
 		self.ui.jamSelect.clicked.connect(lambda: self.jam.selectFile(QFileDialog().getOpenFileName(directory=self.jam.dir)))
		self.ui.sendJam.clicked.connect(self.jam.sendFile)
		self.ui.jamLoaderProgressBar.reset()
		self.ui.jamLoaderProgressBar.setMaximum(1000)
		self.jam.setProgress.connect(lambda n: self.ui.jamLoaderProgressBar.setValue(n*1000))
		self.jam.setAction.connect(lambda: self.ui.sendJam.setText)

		# monitor ports - should make a common class and instantiate multiple times
		self.sptimer = QTimer()
		self.portname1 = None
		self.portname2 = None
		self.monitorPort1 = serialio.serialPort(int(self.ui.MonitorBaud1.currentText()))
		self.monitorPort2 = serialio.serialPort(int(self.ui.MonitorBaud2.currentText()))

		self.listPorts()

		self.ui.MonitorPort1.activated.connect(self.selectPort1)
		self.ui.MonitorPort2.activated.connect(self.selectPort2)
		self.ui.MonitorBaud1.activated.connect(self.selectRate1)
		self.ui.MonitorBaud2.activated.connect(self.selectRate2)

		self.ui.setDateTime.clicked.connect(self.setDateTimeNow)
					
	# printme
	def setupPrintme(self):
		import buildversion, endian, infopane, machines
		import pidport, srecordTransfer, transferPane
# 		self.ui.buildversion.setChecked(buildversion.printme)
# 		self.ui.buildversion.stateChanged(lambda x: buildversion.printme = x)
		self.ui.endian.setChecked(endian.printme)
		self.ui.endian.stateChanged.connect(lambda x: setattr(self, endian.printme,x))
# 		self.ui.infopane.setChecked(infopane.printme)
# 		self.ui.infopane.stateChanged(lambda x: infopane.printme = x)
# 		self.ui.machines.setChecked(machines.printme)
# 		self.ui.machines.stateChanged(lambda x: machines.printme = x)
# 		self.ui.pidport.setChecked(pidport.printme)
# 		self.ui.pidport.stateChanged(lambda x: pidport.printme = x)
# 		self.ui.srecordTransfer.setChecked(srecordTransfer.printme)
# 		self.ui.srecordTransfer.stateChanged(lambda x: srecordTransfer.printme = x)
# 		self.ui.transferPane.setChecked(transferPane.printme)
# 		self.ui.transferPane.stateChanged(lambda x: transferPane.printme = x)

	# load test
	def loadRun(self):
		if self.loadFrames:
			self.ui.loadRun.setText('Run')
			self.loadTimer.stop()
		else:
			self.ui.loadRun.setText('Abort')
			self.loadFrames = int(self.ui.loadFrames.text())
			delay = int(self.ui.loadDelay.text())
			self.loadTimer.setInterval(delay)
			self.loadTimer.start()
	
	def loadFrame(self):
		if self.loadFrames:
			self.loadFrames -= 1
			packet = [randrange(0,255) for i in range(int(self.ui.loadSize.text()))]
			self.protocol.sendNPS(pids.TEST_FRAME, packet)
		else:
			self.ui.loadRun.setText('Run')
			self.loadTimer.stop()

	# monitor ports
	def listPorts(self):
		select, disc = '(Select a Port)', '(Disconnect)'

		uiPort1 = self.ui.MonitorPort1
		uiPort2 = self.ui.MonitorPort2
		items = [uiPort1.itemText(i) for i in range(1, uiPort1.count())]
		self.prefix, ports = listports.listports()
		
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
			self.monitorPort1.open(self.prefix, self.portname1, self.monitorPort1.rate)
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
			self.monitorPort2.open(self.prefix, self.portname2, self.monitorPort2.rate)
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

	def serialDone(self):
		note('Serial thread finished')

	def ioError(self, message):
		error(message)

	def connectPort1(self): # override in children
		self.monitorPort1.source.connect(self.sink1)
		self.setParam(self.monitorPort1, 'E', 8, 1)

	def connectPort2(self): # override in children
		self.monitorPort2.source.connect(self.sink2)
		self.setParam(self.monitorPort2, 'E', 8, 1)

	def sink1(self, s):
		ts = self.timestamp()
		message(ts+''.join(map(lambda x: ' '+hex(ord(x))[2:],  s)), self.ui.Color1.currentText())	

	def sink2(self, s):
		ts = self.timestamp()
		message(ts+''.join(map(lambda x: ' '+hex(ord(x))[2:],  s)), self.ui.Color2.currentText())	

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
		self.parent.protocol.sendNPS(pids.EVAL, self.parent.who() + payload)
