# Jam player file sender  Robert Chapman III  Aug 24, 2015

from pyqtapi2 import *
from endian import *
from message import *
from imageTransfer import imageTransfer
import pids

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

class jamSender(imageTransfer):
	def __init__(self, parent):
		super(jamSender, self).__init__(parent)
		# shortcuts
		self.protocol = self.parent.parent.protocol
		# protocol
		if  "JTAG" in dir(pids):
			self.protocol.packetSource(pids.JTAG, self.jamResponse)

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

	# states
	def requestTransfer(self):
		size = longList(self.size)
		name = [len(self.image.name)] + list(self.image.name)
		type = [jamType.get(self.image.type, UNKNOWN)]
		payload = self.who() + [JAM_REQUEST] + size + name + type
		self.protocol.sendNPS(pids.JTAG, payload)
	
	def transferData(self, data):
		payload = self.who() + [JAM_DATA] + longList(self.i) + data
		self.protocol.sendNPS(pids.JTAG, payload)
	
	def transferDone(self):
		payload = self.who() + [JAM_DONE] + longList(self.image.checksum)
		self.protocol.sendNPS(pids.JTAG, payload)