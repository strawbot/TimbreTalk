# test panel for qtran  Robert Chapman III  Oct 24, 2012

from pyqtapi2 import *
import time
from message import *
import sfp, pids
from endian import *
from random import randrange
import traceback	

class testPane(QWidget):
	def __init__(self, parent):
		QWidget.__init__(self, parent)
		self.parent = parent
		self.ui = parent.ui
		self.protocol = parent.protocol
		
		self.transfer = 0

		# printme
		self.setupPrintme()
		
		# load
		self.loadTimer = QTimer()
		self.loadTimer.timeout.connect(self.loadFrame)
		self.loadFrames = 0
		self.ui.loadRun.clicked.connect(self.loadRun)
		
		# STM32 Boot Loader
		self.ui.initBoot.clicked.connect(lambda: self.sendHex([0x7F]))
		self.ui.getCommand.clicked.connect(lambda: self.sendHex([0x00,0xFF]))
		self.ui.gvCommand.clicked.connect(lambda: self.sendHex([0x01,0xFE]))
		self.ui.gidCommand.clicked.connect(lambda: self.sendHex([0x02,0xFD]))
		self.ui.readCommand.clicked.connect(self.readCmd)
		self.ui.goCommand.clicked.connect(self.goCmd)
		self.ui.writeCommand.clicked.connect(self.writeCmd)
		self.ui.eraseCommand.clicked.connect(self.eraseCmd)
		self.ACK = chr(0x79)
		
		self.ui.readAddress.setText('08000000')
		self.ui.readLength.setText('10')

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

	def eraseCmd(self):
		pass

