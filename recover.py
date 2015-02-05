# recovery  Robert Chapman  Dec 4, 2012
'''
call with: parent, attempts
signals: started, recovered, failed, done
slots: startRecovery, stopRecovery
'''
from pyqtapi2 import *

import pids
from endian import *
from message import *

# parameter spids
AUTOBOOT_PARAM = 1 # whether to autoboot (1) or not (0)
BOOTAPP_PARAM = 2 # address of location to autoboot

	# stop main from running application by changing auto boot parameter
	# send set parameter every 300ms until autoboot changed or user presses abort
	# packet format: who, params; param is a tag value pair where each are a long
	# AUTOBOOT_PARAM (1) - whether to autoboot (1) or not (0)
	# BOOTAP_PARAM (2) - address of location to autoboot

class recover(QObject):
	started = Signal()
	recovered = Signal()
	failed = Signal()
	done = Signal() # signal for done
	stopTimer = Signal()
	startTimer = Signal()

	def __init__(self, parent, attempts=30):
		QObject.__init__(self) # needed for signals to work!!
		# recovery inits
		self.parent = parent
		self.attempts = attempts
		self.recoverTimer = QTimer()
		self.recoverTimer.setInterval(500)
		self.recoverTimer.timeout.connect(self.sendStopAutoboot)
		self.stopTimer.connect(self.recoverTimer.stop)
		self.startTimer.connect(self.recoverTimer.start)

	# shutdown signal
	def shutdown(self):
		self.stopRecovery()
#		note('shutting down recovery\n\r')

	def startRecovery(self): # initial call
		self.started.emit()
		self.parent.protocol.packetSource(pids.PARAM, self.readParam)
		self.startTimer.emit()
	
	def stopRecovery(self):
		self.stopTimer.emit()
		self.done.emit()

	def sendStopAutoboot(self):
		if self.attempts:
			self.attempts -= 1
			who = [self.parent.whoto, self.parent.whofrom]
			parameter1 = longList(AUTOBOOT_PARAM)
			value1 = longList(0)
			set = who + parameter1 + value1
			get = who + parameter1
			self.parent.protocol.sendNPS(pids.SET_PARAM, set)
			self.parent.protocol.sendNPS(pids.GET_PARAM, get)
			note('\nsent stop autobooting.')
		else:
			note('\nRecovery gave up after too many attempts.')
			self.recoverTimer.stop()
			self.failed.emit()

	def readParam(self, packet):
		[parameter, value] =  cast('BBLL', packet)[2:4]
		if parameter == AUTOBOOT_PARAM and value == 0:
			note('\nAutboot disabled.')
			self.stopRecovery()
			self.recovered.emit()

