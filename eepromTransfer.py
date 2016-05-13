# EEPROM text file transfer  Robert Chapman III  May 12, 2016

from pyqtapi2 import *
from imageTransfer import imageTransfer
from transfer import *
import pids

class eepromTransfer(imageTransfer):
	def setupTransfer(self):
		self.protocol.packetSource(pids.EEPROM, self.transferResponse)
		self.transferPid = pids.EEPROM
		self.transferType = TEXT_TRANSFER
