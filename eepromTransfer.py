# EEPROM text file transfer  Robert Chapman III  May 12, 2016

from pyqtapi2 import *
from imageTransfer import imageTransfer
from transfer import *
import pids
from message import *
import binascii
import sys
import traceback

class eepromTransfer(imageTransfer):
	endToken = "END;"
	scriptOk = Signal(object)
	scriptCrc = 0

	def setupTransfer(self):
		self.protocol.setHandler(pids.EEPROM, self.transferResponse)
		self.transferPid = pids.EEPROM
		self.transferType = TEXT_TRANSFER

	def checkScriptCrc(self):
		image = ''.join(map(chr, self.image))
		if image.find(self.endToken) == -1:
			warning('Could not find ' + self.endToken + ' within script')
			self.scriptOk.emit(False)
		else:
			endp = image.find(self.endToken);
			endp += len(self.endToken)
			self.scriptCrc = 0
			calcCrc = binascii.crc32(image[:endp]) & 0xFFFFFFFF
			if len(image[endp:]) >= 8:
				self.scriptCrc = int(image[endp:endp+8], 16)
				if calcCrc == self.scriptCrc:
					self.scriptOk.emit(True)
					return
			note('Calculated CRC should be: %08X' % calcCrc)
			self.scriptOk.emit(False)
