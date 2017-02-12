# Jam player file sender  Robert Chapman III  Aug 24, 2015

from pyqtapi2 import *
from imageTransfer import imageTransfer
from transfer import *
import pids

jamType = {'.jam':JAM_PLAYER, '.jbc':JBC_PLAYER}

class jamSender(imageTransfer):
	def __init__(self, parent):
		super(jamSender, self).__init__(parent)
		if 'JAM' in pids.pids.keys():
			self.protocol.packetSource(pids.JAM, self.transferResponse)
			self.protocol.packetSource(pids.FILES, self.transferResponse)
		self.transferDelay = 100

	def sendJam(self):
		imageTransfer.transferPid = pids.JAM
		self.transferType = jamType.get(self.ext, UNKNOWN)
		imageTransfer.sendFile(self)

	def sendFile(self):
		imageTransfer.transferPid = pids.FILES
		self.transferType = 0
		imageTransfer.sendFile(self)
