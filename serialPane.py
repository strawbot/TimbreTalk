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

		self.portParametersMenu()

		# signals
		self.ui.SFP.clicked.connect(self.selectSfp)
		self.ui.Serial1.clicked.connect(self.selectSerial)
		self.ui.Ping.clicked.connect(self.sendPing)
		self.ui.ResetRcvr.clicked.connect(self.resetRcvr)
		self.ui.ProtocolDump.stateChanged.connect(self.protocolDump)
		self.ui.sendHex.clicked.connect(self.sendHex)
		
		self.parent.serialPort.opened.connect(self.setParamButtonText)
		
		# setup
		self.ui.SFP.click()
		self.parent.protocol.packetSource(pids.TALK_OUT, self.talkPacket)

	def portParametersMenu(self):
		# menu for serial port parameters
		paramenu = QMenu(self)
		paramenu.addAction("N 8 1", lambda: self.setParam('N', 8, 1))
		
		paritymenu = paramenu.addMenu('Parity')
		paritymenu.addAction('None', lambda: self.setParam('N',0,0))
		paritymenu.addAction('Even', lambda: self.setParam('E',0,0))
		paritymenu.addAction('Odd', lambda: self.setParam('O',0,0))

		bytesizemenu = paramenu.addMenu('Byte size')
		bytesizemenu.addAction('8', lambda: self.setParam(0,8,0))
		bytesizemenu.addAction('7', lambda: self.setParam(0,7,0))
		bytesizemenu.addAction('6', lambda: self.setParam(0,6,0))
		bytesizemenu.addAction('5', lambda: self.setParam(0,5,0))
		
		stopmenu = paramenu.addMenu('Stopbits')
		stopmenu.addAction('1', lambda: self.setParam(0,0,1))
		stopmenu.addAction('1.5', lambda: self.setParam(0,0,1.5))
		stopmenu.addAction('2', lambda: self.setParam(0,0,2))

		self.ui.toolButton.setMenu(paramenu)
		
		self.setParamButtonText()

	def setParamButtonText(self):
		sp = self.parent.serialPort
		if sp.stopbits == 1.5:
			self.ui.toolButton.setText("%s %i %0.1f"%(sp.parity,sp.bytesize,sp.stopbits))
		else:
			self.ui.toolButton.setText("%s %i %i"%(sp.parity,sp.bytesize,sp.stopbits))

	def setParam(self, parity, bytesize, stopbits):
		try:
			sp = self.parent.serialPort
			if parity: sp.parity = parity
			if bytesize: sp.bytesize = bytesize
			if stopbits: sp.stopbits = stopbits
			self.setParamButtonText()

			if sp.port:
				sp.port.setParity(sp.parity)
				sp.port.setByteSize(sp.bytesize)
				sp.port.setStopbits(sp.stopbits)
				note('Changed port settings to %s%d%d'%(sp.port.getParity(),sp.port.getByteSize(),sp.port.getStopbits()))
		except Exception, e:
			print >>sys.stderr, e
			traceback.print_exc(file=sys.stderr)
			error("can't set Params")
	
	def sendHex(self):
		try:
			self.parent.serialPort.sink(bytearray.fromhex(self.ui.hexNum.text()))
		except Exception, e:
			print >>sys.stderr, e
			traceback.print_exc(file=sys.stderr)
			error("can't set Params")
	
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

