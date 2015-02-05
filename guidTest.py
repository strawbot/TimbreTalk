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

class guidTest(QWidget):
	def __init__(self, parent):
		QWidget.__init__(self, parent)
		self.ui = parent.ui
		self.protocol = parent.protocol
		self.parent = parent
		for guid in testGuids:
			text = '%s (%d,0x%X)'%(guidNamesWidths[guid][0],guid,guid)
			self.ui.guidSelect.addItem(text, guid)
		self.parent.protocol.packetSource(pids.GUID, self.guidHandler)

		# signals
		self.ui.getGuid.clicked.connect(self.getGuid)
		self.ui.setGuid.clicked.connect(self.setGuid)
		self.ui.regGuid.clicked.connect(self.regGuid)
		self.ui.dregGuid.clicked.connect(self.dregGuid)
	
	# support
	def spid(self, n):
		if self.ui.guid16.checkState():
			return guid16[n]
		return n

	def currentGuid(self):
		return self.ui.guidSelect.itemData(self.ui.guidSelect.currentIndex())
	
	def listGuid(self):
		if self.ui.guid16.checkState():
			return shortList(self.currentGuid())
		return longList(self.currentGuid())

	def currentValue(self):
		guid = self.currentGuid()
		n = self.ui.guidValue.text()
		if not n:
			n = '0'
		value = []
		width = guidNamesWidths[guid][1]
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
		return value

	def setValue(self, guid, payload):
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
		self.ui.guidValue.setText(value)

	def sendGuid(self, spid, value=[]):
		tid = [0, 0]
		guid = self.listGuid()
		packet = self.parent.who() + tid + [spid] + guid + value
		if printme: print packet
		self.protocol.sendNPS(pids.GUID, packet)

	# packet handler
	def guidHandler(self, packet):
		if printme: print 'guid packet:', packet
		spid =  cast('BBBBB', packet)[4]
		if spid == SET_GUID_VALUE:
			guid =  cast('BBBBBL', packet)[5]
			self.setValue(guid, packet[9:])
		elif spid == SET_GUID_VALUE16:
			guid =  cast('BBBBBH', packet)[5]
			self.setValue(guid, packet[7:])

	# buttons: get, set, reg, dereg
	def getGuid(self):
		self.sendGuid(self.spid(GET_GUID_VALUE))
		
	def setGuid(self):
		self.sendGuid(self.spid(SET_GUID_VALUE), self.currentValue())
		
	def regGuid(self):
		self.sendGuid(self.spid(REGISTER_GUID))
		
	def dregGuid(self):
		self.sendGuid(self.spid(DEREGISTER_GUID))
		
