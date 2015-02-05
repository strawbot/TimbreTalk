#!/usr/bin/env python

# GUI for serial transactions using Qt	Robert Chapman III	Sep 28, 2012
version='1.20'

from pyqtapi2 import *
from cpuids import MAIN_HOST

# update GUI from designer
from compileui import updateUi
updateUi('mainWindow')
updateUi('tabs')

from message import *
import qterm, serialPane, srecordPane
import packagepane
import testpane, cpuids
import sys

class qtran(qterm.terminal):
	def __init__(self):
		qterm.terminal.__init__(self)
		self.whoto = self.whofrom = 0
		self.serialPane = serialPane.serialPane(self)
		srecordPane.srecordPane(self)
		testpane.testPane(self)
		packagepane.packagePane(self)
		self.listRoutes()

		self.statTimer = QTimer()
		self.statTimer.timeout.connect(self.showStats)
		self.statTimer.setInterval(1000)
		self.statTimer.start()
		self.ui.clearTranStats.clicked.connect(self.clearStats)
		# default
		self.whofrom = MAIN_HOST
		self.ui.whoFrom.setCurrentIndex(self.whofrom)
		QErrorMessage.qtHandler()
	
	def showStats(self):
		self.ui.serialInputs.setText(str(self.serialPort.inputs))
		self.ui.serialOutputs.setText(str(self.serialPort.outputs))
		self.ui.sfpLoInputs.setText(str(self.protocol.loinputs))
		self.ui.sfpLoOutputs.setText(str(self.protocol.looutputs))
		self.ui.sfpHiInputs.setText(str(self.protocol.hiinputs))
		self.ui.sfpHiOutputs.setText(str(self.protocol.hioutputs))
		self.ui.inPackets.setText(str(self.protocol.inpackets))
		self.ui.outPackets.setText(str(self.protocol.outpackets))

	def clearStats(self):
		self.serialPort.inputs = 0
		self.serialPort.outputs = 0
		self.protocol.loinputs = 0
		self.protocol.looutputs = 0
		self.protocol.hiinputs = 0
		self.protocol.hioutputs = 0
		self.protocol.inpackets = 0
		self.protocol.outpackets = 0

	# overrides
	def UiAdjust(self):
		# tab defines
		# tab defines
		SerialTab, \
		SrecordTab, \
		ReleaseTab, \
		TestTab, \
		PhraseTab = range(5)
		# adjustments for terminal app
		self.ui.Controls.setCurrentIndex(SerialTab)
	
	def banner(self):
		self.setWindowTitle('Qtran '+version)

	def connectPort(self):
		self.serialPane.connectPort()
	
	# Routing
	def listRoutes(self):
		routes = [['Direct',0]]
		for name,value in cpuids.whoDict.iteritems():
			if value:
				routes.append([name,value])
		points = [point[0] for point in sorted(routes, key = lambda x: x[1])]
		del(points[-1]) # remove routing points
		self.ui.whoTo.clear()
		self.ui.whoTo.insertItems(0, points)
		self.ui.whoFrom.clear()
		self.ui.whoFrom.insertItems(0, points)
		self.ui.whoTo.activated.connect(self.selectWhoTo)
		self.ui.whoFrom.activated.connect(self.selectWhoFrom)
	
	def selectWhoTo(self, index):
		self.whoto = index
		note('changed target to '+self.ui.whoTo.currentText())

	def selectWhoFrom(self, index):
		self.whofrom = index
		note('changed source to ' + self.ui.whoFrom.currentText())
	
	def who(self): # return latest who list
		return [self.whoto, self.whofrom]

if __name__ == "__main__":
	import sys, traceback	
	sys.excepthook = lambda *args: None
	app = QApplication([])
	try:
		qtran = qtran()
		sys.exit(app.exec_())
	except Exception, e:
		print >>sys.stderr, e
		traceback.print_exc(file=sys.stderr)
	qtran.close()
