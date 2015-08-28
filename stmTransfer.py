# STM32 boot file sender  Robert Chapman III  Aug 25, 2015

from pyqtapi2 import *

import sys, traceback	
from endian import *
from message import *
from checksum import fletcher32
import image, pids
from cpuids import *

printme = 0

class stmSender(QObject):
	setProgress = Signal(object)
	setSize = Signal(object)
	setName = Signal(object)
	setAction = Signal(object)
	setStart = Signal(object)

	ACK = chr(0x79)
	NACK = chr(0x1F)
	
	def __init__(self, parent):
		if printme: print >>sys.stderr, '__init__'
		QObject.__init__(self) # needed for signals to work!!

		self.parent = parent

		# parameters derived
		self.start = 0
		self.address = ""
		self.size = 0
		self.entry = 0
		self.checksum = 0
		self.dir = ''
		self.version = 0
		self.verbose = 0
		self.run = 0
		# timing
		self.transferTimer = QTimer()
		self.transferTimer.timeout.connect(self.timedOut)
		self.transferTimer.setSingleShot(True)

	def selectFile(self, file):
		if printme: print >>sys.stderr, 'selectFile'
		if not file: return
		try:
			self.image = image.imageRecord(file)
			self.dir = self.image.dir
			self.setName.emit(self.image.name)
			self.size = self.image.size
			self.setSize.emit(str(self.image.size))
			self.start = self.image.start
			self.address = hex(self.start)
			self.setStart.emit(hex(self.image.start))
		except Exception, e:
			print >>sys.stderr, e
			traceback.print_exc(file=sys.stderr)
	
	# Boot downloader
	def listenBoot(self):
		note('Redirecting serial port to boot listener')
		self.parent.parent.disconnectPort()
		def showRx(rx):
			note('Rx:%s'%''.join(map(lambda x: ' '+hex(ord(x))[2:],  rx)))
		self.parent.parent.serialPort.source.connect(showRx)
		self.setParam(self.parent.parent.serialPort, 'E', 8, 1)
	
	def noListenBoot(self):
		self.parent.parent.connectPort()
		note('Serial port reconnected')

	def echoTx(self, tx):
		note('Tx:%s'%''.join(map(lambda x: ' '+hex(x)[2:],  tx)))
		self.parent.parent.serialPort.sink(tx)

	# support for sequencing off of replies
	def onAck(self, sequence, successor, failure=None): # setup callback for next step
		if self.verbose:
			note('Tx:%s'%''.join(map(lambda x: ' '+hex(x)[2:],  sequence)))
		self.parent.parent.serialPort.sink(sequence)
		self.nextState = successor
		self.failState = failure

	def nextSuccessor(self,ack): # invoke callback if acked
		if self.verbose:
			note('Rx: %s'% hex(ord(ack[0]))[2:])
		if ack == self.ACK:
			self.nextState()
			return
		if ack == self.NACK:
			if self.failState:
				self.failState()
				return
		error('NACK:'+ack)
		self.abortBoot()

	# states
	def sendFile(self):
		if self.transferTimer.isActive():
			self.abortBoot()
		else:
			if self.image:
				self.startTransferTime = time.time()
				self.connectBoot()
				self.transferTimer.start(2000)
				self.setAction.emit('Abort')
				if self.image.checkUpdates():
					self.setSize.emit(str(self.image.size))
			else:
				error("No image for downloading")
		
	def connectBoot(self):
		note('Acquiring serial port for boot loader')
		self.setProgress.emit(0)
		self.parent.parent.disconnectPort()
		self.setParam(self.parent.parent.serialPort, 'E', 8, 1)
		self.parent.parent.serialPort.source.connect(self.nextSuccessor)
		note('Connect with stm32 boot loader... ')
		self.onAck([0x7F], self.eraseBoot)
		self.setProgress.emit(.025)
	
	def setParam(self, sp, parity, bytesize, stopbits):
		if sp.port:
			sp.port.setParity(parity)
			sp.port.setByteSize(bytesize)
			sp.port.setStopbits(stopbits)

	def eraseBoot(self):
		message('connected')
		note('Erasing...')
		self.transferTimer.start(20000)
		self.onAck(self.checked(0x44), self.erasePages)
		self.setProgress.emit(.05)

	def erasePages(self): # erase pages not supported; erase all
		self.onAck(self.checksummed([0xFF,0xFF]), self.downloadBoot)

	def downloadBoot(self):
		elapsed = time.time() - self.startTransferTime
		message(' flash erased in %.1f seconds'%elapsed,'note')

		note('Download image ')
		self.pointer = self.image.start
		self.writeCommand()
		self.chunk = 256

	def writeCommand(self): # progress bar from .1 to .9
		self.transferTimer.start(2000)
		self.setProgress.emit(.1 + (.8*(self.pointer - self.image.start)/self.image.size))
		if self.pointer < self.image.end:
			self.onAck(self.checked(0x31), self.writeAddress)
		else:
			self.verifyBoot()

	def writeAddress(self):
		address = self.checksummed(longList(self.pointer))
		self.onAck(address, self.writeData)

	def writeData(self):
		if not self.verbose:
			message('.', "note")
		self.chunk = min(self.chunk, self.image.end - self.pointer)
		if self.chunk % 4:
			error('Transfer size not a multiple of 4')
		index = self.pointer - self.image.start
		self.pointer += self.chunk
		data = self.image.image[index:index+self.chunk]
		self.onAck(self.checksummed([self.chunk-1] + data), self.writeCommand)

	def verifyBoot(self): # not verified, just trusted
		# note('\nverify image')
		if self.run:
			self.goCommand()
		else:
			self.reconnectSerial()
	
	def goButton(self):
		self.listenBoot()
		self.parent.parent.serialPort.source.connect(self.nextSuccessor)
		self.startTransferTime = 0
		self.onAck([0x7F], self.goCommand, self.goCommand)
		
	def goCommand(self):
		self.onAck(self.checked(0x21), self.goAddress)

	def goAddress(self):
		if not self.address:
			self.address = "0x8000000"
		self.echoTx(self.checksummed(longList(int(self.address, 0))))
		self.reconnectSerial()
	
	def reconnectSerial(self):
		self.setProgress.emit(1)
		if self.startTransferTime:
			elapsed = time.time() - self.startTransferTime
			transferMsg = 'Finished in %.1f seconds'%elapsed
			rate = (8*self.image.size)/(elapsed*1000)
			rateMsg = ' @ %.1fkbps'%rate
			note(transferMsg+rateMsg)
		self.finishBoot()
	
	def timedOut(self):
		error('Timed out')
		self.abortBoot()

	def abortBoot(self):
		error('Transfer aborted.')
		self.finishBoot()

	def finishBoot(self):
		self.transferTimer.stop()
		self.parent.parent.connectPort()
		note('serial port reconnected')
		self.setAction.emit('Transfer')

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
		self.parent.parent.serialPort.source.connect(self.nextSequence)
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
			self.parent.parent.serialPort.source.disconnect(self.nextSequence)
			note('done command')
		except Exception, e:
			print >>sys.stderr, e
			traceback.print_exc(file=sys.stderr)


	# variable setting
	def setVerbose(self, value):
		self.verbose = value
		
	def setRun(self, value):
		self.run = value