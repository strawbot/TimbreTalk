# serial panel for qtran  Robert Chapman III  Oct 20, 2012

from pyqtapi2 import *
from message import *
import sfsp, pids
import sys

class serialPane(QWidget):
	def __init__(self, parent):
		QWidget.__init__(self, parent)
		self.parent = parent
		self.ui = parent.ui
		parent.protocol = sfsp.sfspProtocol()

		# signals
		self.ui.SFP.clicked.connect(self.selectSfp)
		self.ui.Serial1.clicked.connect(self.selectSerial)
		self.ui.Ping.clicked.connect(self.sendPing)
		self.ui.ResetRcvr.clicked.connect(self.resetRcvr)
		self.ui.ProtocolDump.stateChanged.connect(self.protocolDump)
		
		# setup
		self.ui.SFP.click()
		self.parent.protocol.packetSource(pids.TALK_OUT, self.talkPacket)

	def disconnectFlows(self):
		def disconnectSignals(signal):
#			while self.protocol.receivers(SIGNAL('source')) > 0:
			try:
				signal.disconnect()
			except:
				pass
		disconnectSignals(self.parent.protocol.source)
		disconnectSignals(self.parent.serialPort.source)
		disconnectSignals(self.parent.source)

	def connectPort(self):
		if self.ui.SFP.isChecked():
			self.selectSfp()
		else:
			self.selectSerial()

	def selectSfp(self):
		if not self.ui.SFP.isChecked():
			note('changed to SFP')
			self.self.resetRcvr()
		self.disconnectFlows()
		if self.ui.LoopBack.isChecked():
			self.parent.serialPort.source.connect(self.parent.serialPort.sink)
			self.parent.protocol.source.connect(self.parent.protocol.sink)
			self.parent.source.connect(self.talkSink)
		else:
			self.parent.protocol.source.connect(self.parent.serialPort.sink)
			self.parent.serialPort.source.connect(self.parent.protocol.sink)
			self.parent.source.connect(self.talkSink)
	
	def selectSerial(self):
		if not self.ui.Serial1.isChecked():
			note('changed to no-protocol serial')
		self.disconnectFlows()
		if self.ui.LoopBack.isChecked():
			self.parent.source.connect(self.parent.sink)
		else:
			self.parent.serialPort.source.connect(self.parent.sink)
			self.parent.source.connect(self.parent.serialPort.sink)

	def protocolDump(self, flag):
		self.parent.protocol.VERBOSE = flag
		note('protocol dump ',(flag != 0))

	# talk connections
	def talkPacket(self, packet): # handle text packets
		self.parent.sink(''.join(map(chr, packet[2:])))

	def talkSink(self, s): # have a text port
		s = str(s)
		who = self.parent.who()
		if self.ui.InBuffered.isChecked():
			talkout = pids.EVAL
			s = s.strip()
			payload = who+map(ord,s)+[0]
		else:
			talkout = pids.TALK_IN
			payload = who+map(ord,s)
		self.parent.protocol.sendNPS(talkout, payload)

	def sendPing(self, flag):
		self.parent.protocol.sendNPS(pids.PING, [])

	def resetRcvr(self):
		try:
			self.parent.protocol.initRx()
		except Exception, e:
			print >>sys.stderr, e
			traceback.print_exc(file=sys.stderr)
			error("can't reset receiver")

	def setId(self):
		self.parent.protocol.sendNPS(pids.SET_ID, [self.parent.whoto])

