# Jam player file sender  Robert Chapman III  Aug 24, 2015

from pyqtapi2 import *

import sys, traceback	
from endian import *
from message import *
from checksum import fletcher32
import image, pids
from cpuids import *

printme = 0

# spids
(JAM_REQUEST,	# size in bytes (32 bit), name (count prefixed), type (byte)
JAM_REPLY,		# status (byte)
JAM_DATA,		# data
JAM_RESULT, 	# status
JAM_DONE,		# send checksum
# results
REQUEST_OK, REQUEST_TOOBIG, JAM_BUSY, # from request
TRANSFER_OK, CHECK_ERROR, TRANSFER_INCOMPLETE, UNSUPORTED_TYPE, # from transfer
# types
UNKNOWN, JAM_PLAYER, JBC_PLAYER) = range (0,15)

resultText = {
	REQUEST_OK:'REQUEST_OK',
	REQUEST_TOOBIG:' REQUEST_TOOBIG',
	JAM_BUSY:' JAM_BUSY',
	TRANSFER_OK:' TRANSFER_OK',
	CHECK_ERROR:' CHECK_ERROR',
	TRANSFER_INCOMPLETE:' TRANSFER_INCOMPLETE',
	UNSUPORTED_TYPE:'UNSUPORTED_TYPE'}

jamType = {'.jam':JAM_PLAYER, '.jbc':JBC_PLAYER}

class jamSender(QObject):
	setProgress = Signal(object)
	setSize = Signal(object)
	setName = Signal(object)
	setAction = Signal(object)

	def __init__(self, parent):
		if printme: print >>sys.stderr, '__init__'
		QObject.__init__(self) # needed for signals to work!!

		self.parent = parent

		# parameters derived
		self.size = 0
		self.checksum = 0
		self.dir = ''
		self.verbose = 0
		# timing
		self.transferTimer = QTimer()
		self.transferTimer.timeout.connect(self.timedOut)
		self.transferTimer.setSingleShot(True)
		# shortcuts
		self.protocol = self.parent.parent.protocol

		# protocol
		self.protocol.packetSource(pids.JTAG, self.jamResponse)
	
	def who(self):
		return self.parent.parent.who() # packet routing

	def jamResponse(self, packet):
		spid, result = cast('BBBB', packet)[2:4]
		if spid == JAM_REPLY:
			if result == REQUEST_OK:
				note('Request approved. Starting data transfer...')
				self.startTransfer()
			else:
				error('Request denied:'+resultText.get(result,'Unknown'))
				self.abort()
		elif spid == JAM_RESULT:
			if result == TRANSFER_OK:
				note('Transfer complete')
				self.finish()
			else:
				error('Transfer failed. '+resultText.get(result,'Unknown'))
				self.abort()
		else:
			error('Unknown spid:'+hex(spid))
			self.abort()

	def selectFile(self, file):
		if printme: print >>sys.stderr, 'selectFile'
		if not file: return
		try:
			self.image = image.imageRecord(file)
			self.dir = self.image.dir
			self.setName.emit(self.image.name)
			self.size = self.image.size
			self.setSize.emit(str(self.image.size))
		except Exception, e:
			print >>sys.stderr, e
			traceback.print_exc(file=sys.stderr)
	
	# states
	def sendFile(self):
		if self.transferTimer.isActive():
			self.abort()
		else:
			if self.image:
				if self.image.checkUpdates():
					self.setSize(str(self.image.size))
				self.startTransferTime = time.time()
				self.requestTransfer()
				self.transferTimer.start(2000)
				self.setAction.emit('Abort')
			else:
				error("No image for downloading")
		
	def requestTransfer(self):
		self.setProgress.emit(0)
		spid =  [JAM_REQUEST]
		size = longList(self.size)
		name = [len(self.image.name)] + list(self.image.name)
		type = [jamType.get(self.image.type, UNKNOWN)]
		payload = self.who() + spid + size + name + type
		self.protocol.sendNPS(pids.JTAG, payload)
	
	def transferChunk(self):
		if self.left:
			if self.left > self.chunk:
				sendsize = self.chunk
				self.left -= self.chunk
			else:
				sendsize = self.left
				self.left = 0
			data = self.image.image[self.pointer:self.pointer+sendsize]
			payload = self.who() + self.spid + longList(self.i) + data
			self.protocol.sendNPS(pids.JTAG, payload)
			self.setProgress.emit((self.size - self.left)/self.size)
			self.i += 1
			self.pointer += sendsize
			self.transferTimer.start(0)
		else:
			payload = self.who() + [JAM_DONE] + longList(self.image.checksum)
			print hex(self.image.checksum), map(lambda x: hex(x)[2:], longList(self.image.checksum))
			self.protocol.sendNPS(pids.JTAG, payload)

			self.transferTimer.timeout.disconnect()
			self.transferTimer.timeout.connect(self.timedOut)
			self.transferTimer.start(5000)

	def startTransfer(self):
		self.spid = [JAM_DATA]
		self.i = 0
		self.pointer = 0
		self.chunk = 240
		self.left = self.size

		self.transferTimer.timeout.disconnect()
		self.transferTimer.timeout.connect(self.transferChunk)
		self.transferTimer.start(0)

	# possible end sequences
	def timedOut(self):
		error('Timed out')
		self.abort()

	def abort(self):
		error('Transfer aborted.')
		self.finish()

	def finish(self):
		self.transferTimer.stop()
		self.setAction.emit('Transfer')
		elapsed = time.time() - self.startTransferTime
		message(' finished in %.1f seconds'%elapsed,'note')
