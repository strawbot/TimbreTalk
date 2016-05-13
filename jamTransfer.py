# Jam player file sender  Robert Chapman III  Aug 24, 2015

from pyqtapi2 import *
from imageTransfer import imageTransfer
from transfer import *
import pids

jamType = {'.jam':JAM_PLAYER, '.jbc':JBC_PLAYER}

class jamSender(imageTransfer):
	def setupTransfer(self):
		self.protocol.packetSource(pids.JTAG, self.transferResponse)
		self.transferPid = pids.JTAG
		self.transferType = jamType.get(self.ext, UNKNOWN)
