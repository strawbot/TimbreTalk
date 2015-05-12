# test panel for qtran  Robert Chapman III  Oct 24, 2012

from pyqtapi2 import *
import time
from message import *
import sfp, pids
from endian import *
from random import randrange
from image import *
import traceback	
import listports, serialio
import time

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
	progress = Signal(object)
	ACK = chr(0x79)

	def __init__(self, parent):
		QWidget.__init__(self, parent)
		self.parent = parent
		self.ui = parent.ui
		self.protocol = parent.protocol
		
		self.image = None

		# printme
		self.setupPrintme()
		
		# load
		self.loadTimer = QTimer()
		self.loadTimer.timeout.connect(self.loadFrame)
		self.loadFrames = 0
		self.ui.loadRun.clicked.connect(self.loadRun)
		
		# STM32 Boot Tools
		self.ui.initBoot.clicked.connect(lambda: self.sendHex([0x7F]))
		self.ui.getCommand.clicked.connect(lambda: self.sendHex([0x00,0xFF]))
		self.ui.gvCommand.clicked.connect(lambda: self.sendHex([0x01,0xFE]))
		self.ui.gidCommand.clicked.connect(lambda: self.sendHex([0x02,0xFD]))
		self.ui.readCommand.clicked.connect(self.readCmd)
		self.ui.goCommand.clicked.connect(self.goCmd)
		self.ui.writeCommand.clicked.connect(self.writeCmd)
		self.ui.eraseCommand.clicked.connect(self.eraseCmd)
		
		self.ui.readAddress.setText('08000000')
		self.ui.readLength.setText('10')

		# STM32F4 Boot Loader
		self.ui.bootSelect.clicked.connect(self.selectFile)
		self.ui.sendBoot.clicked.connect(self.sendBoot)
		self.progress.connect(self.progressBar)
		self.transferTimer = QTimer()
		self.transferTimer.timeout.connect(self.abortBoot)
		self.transferTimer.setSingleShot(True)
		
		self.ui.Boot.clicked.connect(self.listenBoot)
		self.ui.Reconnect.clicked.connect(self.noListenBoot)
		self.ui.Init.clicked.connect(lambda: self.echoTx([0x7F]))
		self.ui.Rdp.clicked.connect(lambda: self.echoTx(self.checked(0x92)))
		self.ui.Erase.clicked.connect(lambda: self.echoTx(self.checked(0x44)))
		self.ui.Pages.clicked.connect(lambda: self.echoTx(self.checksummed([0xFF,0xFF])))
		self.ui.Write.clicked.connect(lambda: self.echoTx(self.checked(0x31)))
		self.ui.Address.clicked.connect(lambda: self.echoTx(self.checksummed([8,0,0,0])))
		self.ui.Data.clicked.connect(lambda: self.echoTx(self.checksummed([7,1,2,3,4,5,6,7,8])))
		self.ui.Get.clicked.connect(lambda: self.echoTx(self.checked(0x0)))
		self.ui.Getrpd.clicked.connect(lambda: self.echoTx(self.checked(0x1)))
		self.ui.Getid.clicked.connect(lambda: self.echoTx(self.checked(0x2)))

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

	def selectFile(self):
		if printme: print >>sys.stderr, 'selectBoot'
		try:
			file = QFileDialog().getOpenFileName()
			if file:
				self.image = imageRecord(file)
				self.ui.bootFile.setText(self.image.name)
				self.ui.bootStart.setText(hex(self.image.start))
				self.ui.bootSize.setText(str(self.image.size))
		except Exception, e:
			print >>sys.stderr, e
			traceback.print_exc(file=sys.stderr)
	
	# Boot downloader
	def listenBoot(self):
		note('redirecting serial port to boot listener', True)
		self.parent.disconnectPort()
		def showRx(rx):
			note('Rx:%s'%''.join(map(lambda x: ' '+hex(ord(x))[2:],  rx)))
		self.parent.serialPort.source.connect(showRx)
		self.setParam(self.parent.serialPort, 'E', 8, 1)
	
	def noListenBoot(self):
		self.parent.connectPort()
		note('serial port reconnected')

	def echoTx(self, tx):
		note('Tx:%s'%''.join(map(lambda x: ' '+hex(x)[2:],  tx)))
		self.parent.serialPort.sink(tx)

	# support for sequencing off of replies
	def onAck(self, sequence, successor):
		note('Tx:%s'%''.join(map(lambda x: ' '+hex(x)[2:],  sequence)))
		self.parent.serialPort.sink(sequence)
		self.nextState = successor

	def nextSuccessor(self,ack):
		note('Rx: %s'% hex(ord(ack))[2:])
		if ack == self.ACK:
			self.nextState()
		else:
			error('NACK'+ack)
			self.abortBoot()

	# states
	def sendBoot(self):
		if self.transferTimer.isActive():
			self.abortBoot()
		else:
			if self.image:
				self.startTransferTime = time.time()
				self.connectBoot()
				self.transferTimer.start(2000)
				self.ui.sendBoot.setText('Abort')
			else:
				error("No image for downloading")
		
	def connectBoot(self):
		note('redirecting serial port to boot loader', True)
		self.progress.emit(0)
		self.parent.disconnectPort()
		self.setParam(self.parent.serialPort, 'E', 8, 1)
		self.parent.serialPort.source.connect(self.nextSuccessor)
		note('connect with stm32 boot loader', True)
		self.onAck([0x7F], self.eraseBoot)
		self.progress.emit(.025)
	
	def disableRDP(self):
		self.onAck(self.checked(0x92), self.waitAck)
	
	def waitAck(self):
		self.onAck([], self.eraseBoot)

	def eraseBoot(self):
		self.transferTimer.start(20000)
		self.onAck(self.checked(0x44), self.erasePages)
		self.progress.emit(.05)

	def erasePages(self):
# 		firstSector = sectorIs(self.image.start)
# 		lastSector = sectorIs(self.image.start + self.image.size)
# 		sectors = range(firstSector, lastSector + 1)[0]
# 		self.onAck(self.checksummed([len(sectors) - 1] + sectors), downloadBoot)
		self.onAck(self.checksummed([0xFF,0xFF]), self.downloadBoot)

	def downloadBoot(self):
		elapsed = time.time() - self.startTransferTime
		note(' Flash erased in %.1f seconds'%elapsed, True)

		note('download image')
		self.pointer = self.image.start
		self.writeCommand()
		self.chunk = 256

	def writeCommand(self): # progress bar from .1 to .9
		self.transferTimer.start(2000)
		print self.pointer,self.image.start,self.image.size,(self.pointer - self.image.start)/self.image.size
		self.progress.emit(.1 + (.8*(self.pointer - self.image.start)/self.image.size))
		if self.pointer < self.image.end:
			self.onAck(self.checked(0x31), self.writeAddress)
		else:
			self.verifyBoot()

	def writeAddress(self):
		address = self.checksummed(longList(self.pointer))
		self.onAck(address, self.writeData)

	def writeData(self):
		note('.')
		self.chunk = min(self.chunk, self.image.end - self.pointer)
		if self.chunk % 4:
			error('Transfer size not a multiple of 4')
		index = self.pointer - self.image.start
		self.pointer += self.chunk
		data = self.image.image[index:index+self.chunk]
		self.onAck(self.checksummed([self.chunk-1] + data), self.writeCommand)

	def verifyBoot(self):
		note('\nverify image')
		self.reconnectSerial()
	
	def reconnectSerial(self):
		self.progress.emit(1)
		elapsed = time.time() - self.startTransferTime
		transferMsg = 'Finished in %.1f seconds'%elapsed
		rate = (8*self.image.size)/(elapsed*1000)
		rateMsg = ' @ %.1fkbps'%rate
		note(transferMsg+rateMsg)
		self.transferTimer.stop()
		self.parent.connectPort()
		note('serial port reconnected')
		self.ui.sendBoot.setText('Send')

	def abortBoot(self):
		error('Transfer aborted.')
		self.transferTimer.stop()
		self.parent.connectPort()
		note('serial port reconnected')
		self.ui.sendBoot.setText('Send')

	def progressBar(self, n):
		if printme: print >>sys.stderr, 'progress'
		if n:
			self.ui.bootLoaderProgressBar.setValue(n*1000)
		else:
			self.ui.bootLoaderProgressBar.reset()
			self.ui.bootLoaderProgressBar.setMaximum(1000)

	# STM32 Boot Loader
	def sendHex(self, bytes):
		try:
			note('sending: '+ reduce(lambda a,b: a+b, map(hex, bytes)))
			self.parent.serialPort.sink(bytes)
		except Exception, e:
			print >>sys.stderr, e
			traceback.print_exc(file=sys.stderr)

	def checksummed(self, bytes):
		bytes.append(reduce(lambda a,b: a^b, bytes))
		return bytes
	
	def checked(self, byte):
		return (byte, ~byte&0xFF)

	# command sequencer using signal from receive and iterator on sequences
	# need to include a timeout
	def bootSequence(self, sequences):
		self.parent.serialPort.source.connect(self.nextSequence)
		self.sequences = iter(sequences)
		self.nextSequence(self.ACK)
	
	def nextSequence(self,ack):
		try:
			seq = self.sequences.next()
			if ack != self.ACK:
				error('NACK'+ack)
				raise(StopIteration)
			print seq
			self.sendHex(seq)
		except StopIteration:
			self.parent.serialPort.source.disconnect(self.nextSequence)
			note('done command')
		except Exception, e:
			print >>sys.stderr, e
			traceback.print_exc(file=sys.stderr)

	# sequenced commands
	def readCmd(self):
		try:
			address = self.checksummed(bytearray.fromhex(self.ui.readAddress.text()))
			print address
			length = self.checked(int(self.ui.readLength.text()))
			print length
			self.bootSequence((self.checked(0x11), address, length))
		except Exception, e:
			print >>sys.stderr, e
			traceback.print_exc(file=sys.stderr)

	def goCmd(self):
		address = self.checksummed(bytearray.fromhex(self.ui.goAddress.text()))
		self.bootSequence((self.checked(0x21), address))

	def writeCmd(self):
		address = self.checksummed(bytearray.fromhex(self.ui.writeAddress.text()))
		data = self.checksummed(bytearray.fromhex(self.ui.writedata.text()))
		length = self.checked(len(data)-1)
		self.bootSequence((self.checked(0x31), address, length, data ))

	def sectorIs(self, address):
		for i in range(len(sectors)):
			if sectors[i][1] <= address < (sectors[i][1] + sectors[i][2]*1024):
				return i
		return None

	def eraseCmd(self):
		pass


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