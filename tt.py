#!/usr/bin/env python

# GUI for serial transactions using Qt	Robert Chapman III	Sep 28, 2012
version='1.7.4'

from pyqtapi2 import *
from protocols.pids import DIRECT, whoDict
from protocols import sfp

# update GUI from designer
from compileui import updateUi
updateUi('mainWindow')
updateUi('tabs')

from message import *
import qterm, serialPane, transferPane
import infopane
import utilitypane

class sfpQt (QObject, sfp.sfpProtocol):
	source = Signal(object)

	def __init__(self):
		QObject.__init__(self)
		sfp.sfpProtocol.__init__(self)

	def sink(self, bytes):
		self.rxBytes(map(ord, bytes))

	def newFrame(self):
		self.source.emit(''.join(map(chr, self.txBytes())))

	def newPacket(self):
		self.distributer()

	def error(self, code = 0, string = ""):
		self.result = code
		error(string)

	def warning(self, code = 0, string = ""):
		self.result = code
		warning(string)

	def note(self, code = 0, string = ""):
		self.result = code
		note(string)

	def dump(self, tag, buffer):
		messageDump(tag, buffer)

class timbreTalk(qterm.terminal):
	def __init__(self):
		qterm.terminal.__init__(self)
		self.protocol = sfpQt()
		self.whoto = self.whofrom = 0
		self.serialPane = serialPane.serialPane(self)
		transferPane.srecordPane(self)
		utilitypane.utilityPane(self)
		infopane.infoPane(self)
		self.listRoutes()

		# default
		self.whofrom = DIRECT
		self.ui.whoFrom.setCurrentIndex(self.whofrom)
		QErrorMessage.qtHandler()

		# to handle warnings about tablets when running under a VM
		# http://stackoverflow.com/questions/25660597/hide-critical-pyqt-warning-when-clicking-a-checkboc
		def handler(msg_type, msg_string):
			pass
		qInstallMsgHandler(handler)

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
		self.setWindowTitle('Timbre Talk '+version)

	def connectPort(self):
		self.serialPane.connectPort()

	def disconnectPort(self):
		self.serialPane.disconnectFlows()

	# Routing
	def listRoutes(self):
		routes = [['Direct',0]]
		for name,value in whoDict.iteritems():
			if value:
				routes.append([name,value])
		points = [point[0] for point in sorted(routes, key = lambda x: x[1])]
		del(points[-1]) # remove routing points
		self.ui.whoTo.clear()
		self.ui.whoTo.insertItems(0, points)
		self.ui.whoFrom.clear()
		self.ui.whoFrom.insertItems(0, points)
		self.ui.whoTo.currentIndexChanged.connect(self.selectWhoTo)
		self.ui.whoFrom.currentIndexChanged.connect(self.selectWhoFrom)

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
# 	kwargs = dict(x.split('=', 1) for x in sys.argv[1:])
# 	name = kwargs.get('name', '')
# 	port = kwargs.get('port', '/dev/ttyACM0')
#	sys.excepthook = lambda *args: None
	app = QApplication([])
	try:
		timbreTalk = timbreTalk()
		sys.exit(app.exec_())
	except Exception as e:
		print >>sys.stderr, e
		traceback.print_exc(file=sys.stderr)
	timbreTalk.close()
