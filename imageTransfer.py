# Generic File Transfer  Robert Chapman III  May 11, 2016

from pyqtapi2 import *

import sys, traceback	
from endian import *
from message import *
from checksum import fletcher32
import image

class imageTransfer(image.imageRecord):
	setProgress = Signal(object)
	setAction = Signal(object)
	chunk = 240 # default size to transfer

	def __init__(self, parent):
		super(imageTransfer, self).__init__(parent)
		
		# timing
		self.transferTimer = QTimer()
		self.transferTimer.timeout.connect(self.timedOut)
		self.transferTimer.setSingleShot(True)

	def who(self):
		return self.parent.parent.who() # packet routing

	# states
	def sendFile(self):
		if self.transferTimer.isActive():
			self.abort()
		else:
			if self.image:
				if self.checkUpdates():
					self.setSize(str(self.size))
				self.startTransferTime = time.time()
				self.setProgress.emit(0)
				self.requestTransfer()
				self.transferTimer.start(2000)
				self.setAction.emit('Abort')
			else:
				error("No image for downloading")
		
	def startTransfer(self):
		self.i = 0
		self.pointer = 0
		self.left = self.size

		self.transferTimer.timeout.disconnect()
		self.transferTimer.timeout.connect(self.transferChunk)
		self.transferTimer.start(0)

	def requestTransfer(self): # can be used to inform/check/erase
		pass
	
	def transferData(self, data): # used for all data transfers
		pass
	
	def transferDone(self): # can be used to verify
		pass

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
			self.transferTimer.start(0)
		else:
			self.transferDone()
			self.transferTimer.timeout.disconnect()
			self.transferTimer.timeout.connect(self.timedOut)
			self.transferTimer.start(20000)

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
