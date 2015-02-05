# for sending guids
from guidsmain import guidNamesWidths
from guidtestset import *
import pids
from endian import *
from pyqtapi2 import *

printme = 0

GET_GUID_VALUE, \
SET_GUID_VALUE, \
GET_GUID_FLAGS, \
SET_GUID_FLAGS, \
REGISTER_GUID, \
DEREGISTER_GUID, \
GET_GUID_VALUE16, \
SET_GUID_VALUE16, \
GET_GUID_FLAGS16, \
SET_GUID_FLAGS16, \
REGISTER_GUID16, \
DEREGISTER_GUID16 = range(12) # remove the registration of a 16-bit GUID

guid32 = \
[GET_GUID_VALUE, \
SET_GUID_VALUE, \
GET_GUID_FLAGS, \
SET_GUID_FLAGS, \
REGISTER_GUID, \
DEREGISTER_GUID] 

guid16 = \
[ GET_GUID_VALUE16, \
SET_GUID_VALUE16, \
GET_GUID_FLAGS16, \
SET_GUID_FLAGS16, \
REGISTER_GUID16, \
DEREGISTER_GUID16\
]

class guidManager(QObject):
	def __init__(self, parent):
		self.protocol = parent.protocol
		self.parent = parent
		self.parent.protocol.packetSource(pids.GUID, self.guidHandler)

	def guidValue(self, guid, n):
		value = []
		width = guidNamesWidths[int(guid,0)][1]
		if width == 1:
			value = [0xFF & int(n, 0)]
		elif width == 2:
			value = shortList(int(n, 0))
		elif width == 4:
			value = longList(int(n, 0))
		elif width == 8:
			value = longlongList(int(n, 0))
		elif width == 10:
			value = map(ord, (n+'          ')[0:10]) # pad with blanks
		return longList(int(guid,0)) + value

	def showValue(self, guid, payload):
		width = guidNamesWidths[guid][1]
		if width == 1:
			value = str(payload[0])
		elif width == 2:
			value = str(short(payload[0:width]))
		elif width == 4:
			value = str(long(payload[0:width]))
		elif width == 8:
			value = str(longlong(payload[0:width]))
		elif width == 10:
			value = ''.join(chr(c) for c in payload[0:width])
		print 'guid:', guid, ' value:',value

	def sendGuid(self, guid, value):
		tid = [0, 0]
		print  self.parent.who(), tid, [SET_GUID_VALUE], self.guidValue(guid , value)
		packet = self.parent.who() + tid + [SET_GUID_VALUE] + self.guidValue(guid, value)
		if printme: print packet
		self.protocol.sendNPS(pids.GUID, packet)
	
	def deregisterGuid(self, guid):
		tid = [0, 0]
		print  self.parent.who(), tid, [DEREGISTER_GUID], longList(guid)
		packet = self.parent.who() + tid + [DEREGISTER_GUID] + longList(guid)
		if printme: print packet
		self.protocol.sendNPS(pids.GUID, packet)

	# packet handler
	def guidHandler(self, packet):
		if printme: print 'guid packet:', packet
		spid =  cast('BBBBB', packet)[4]
		if spid == SET_GUID_VALUE:
			guid =  cast('BBBBBL', packet)[5]
			self.showValue(guid, packet[9:])
		elif spid == SET_GUID_VALUE16:
			guid =  cast('BBBBBH', packet)[5]
			self.showValue(guid, packet[7:])
