# Generic File Transfer  Robert Chapman III  May 11, 2016

from pyqtapi2 import *

import sys, traceback	
from endian import *
from message import *
from checksum import fletcher32
import image
from transfer import *

class imageTransfer(image.imageRecord):
	setProgress = Signal(object)
	setAction = Signal(object)
	# perhaps the following parameters should be in the children files which use SFP
	# or bring pids into this module and have it as an SFP transfer but make a super
	# class which is protocol independant
	chunk = 240 # default size to transfer; should derive from MAX_FRAME_LENGTH
	transferPid = 0 # pid for transfer operations
	transferType = 0 # type of file if needed

	def __init__(self, parent):
		super(imageTransfer, self).__init__(parent)
		
		# timing
		self.transferTimer = QTimer()
		self.transferTimer.timeout.connect(self.timedOut)
		self.transferTimer.setSingleShot(True)
		self.transferDelay = 0

		# shortcuts
		self.protocol = self.parent.protocol
		

	def who(self):
		return self.parent.parent.who() # packet routing

	# states
	def sendFile(self):
		if self.transferTimer.isActive():
			self.abort()
		else:
			if self.image:
				self.checkUpdates()
				self.startTransferTime = time.time()
				self.setProgress.emit(0)
				self.setupTransfer()
				self.requestTransfer()
				self.transferTimer.start(2000)
				self.setAction.emit('Abort')
			else:
				error("No image for downloading")
		
	def setupTransfer(self):
		pass

	def startTransfer(self):
		self.i = 0
		self.pointer = 0
		self.left = self.size

		self.transferTimer.timeout.disconnect()
		self.transferTimer.timeout.connect(self.transferChunk)
		self.transferTimer.start(self.transferDelay)

	def transferChunk(self):
		if self.left:
			if self.left > self.chunk:
				sendsize = self.chunk
				self.left -= self.chunk
			else:
				sendsize = self.left
				self.left = 0
			self.transferData(self.image[self.pointer:self.pointer+sendsize])
			self.setProgress.emit((self.size - self.left)/self.size)
			self.i += 1
			self.pointer += sendsize
			self.transferTimer.start(self.transferDelay)
		else:
			self.transferDone()
			self.transferTimer.timeout.disconnect()
			self.transferTimer.timeout.connect(self.timedOut)
			self.transferTimer.start(20000)

	# states
	def requestTransfer(self):
		size = longList(self.size)
		name = [len(self.name)] + list(self.name)
		type = [self.transferType]
		payload = self.who() + [TRANSFER_REQUEST] + size + name + type
		self.protocol.sendNPS(self.transferPid, payload)
	
	def transferData(self, data):
		payload = self.who() + [TRANSFER_DATA] + longList(self.i) + data
		self.protocol.sendNPS(self.transferPid, payload)
	
	def transferDone(self):
		payload = self.who() + [TRANSFER_DONE] + longList(self.checksum)
		self.protocol.sendNPS(self.transferPid, payload)

	def transferResponse(self, packet):
		spid, result = cast('BBBB', packet)[2:4]
		if spid == TRANSFER_REPLY:
			if result == REQUEST_OK:
				note('Request approved. Starting data transfer...')
				self.startTransfer()
			else:
				error('Request denied:'+resultText.get(result,'Unknown'))
				self.abort()
		elif spid == TRANSFER_RESULT:
			if result == TRANSFER_OK:
				note('Transfer complete')
				self.finish()
			else:
				error('Transfer failed. '+resultText.get(result,'Unknown'))
				self.abort()
		else:
			error('Unknown spid:'+hex(spid))
			self.abort()

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

	# receive file
	def getFile(self):
		if self.transferTimer.isActive():
			self.abort()
		else:
			self.emptyImage()
			self.startTransferTime = time.time()
			self.setProgress.emit(0)
			self.requestFile()
			self.transferTimer.start(2000)
			self.setAction.emit('Abort')
	
	def requestFile(self):
		pass