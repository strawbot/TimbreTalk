#!/usr/bin/env python
# part of http://stackoverflow.com/questions/6783194/background-thread-with-qthread-in-pyqt
#from PyQt4 import QtCore
from pyqtapi2 import *
import time
import sys, traceback
from signalcatch import initSignalCatcher

class CObject(QObject):
	finished = pyqtSignal()
	aborted = pyqtSignal()
	
	def run(self):
		print 'C run'
		self.count = 1
		self.timer = QTimer()
		self.timer.timeout.connect(self.work)
		self.timer.setInterval(300)
 		self.timer.start()

	def work(self):
		print "Cthread", self.count
		self.count += 1
		if self.count >= 5:
			self.timer.stop()
#			self.aborted.emit()
			self.finished.emit()
			print 'signals emitted'

# Subclassing QObject and using moveToThread
# http://labs.qt.nokia.com/2007/07/05/qthreads-no-longer-abstract/
class SomeObject(QObject):
	result = 0
	finished = Signal()
	quitthread = Signal()

	def __init__(self, argv, app):
		QObject.__init__(self) # needed for signals to work!!
		self.argv = argv
		self.coreapp = app
		sys.excepthook = lambda *args: None

	def aborted(self):
		print 'aborted'
		self.result = -1
		self.quit()

	def quit(self):
		print 'quit'
		self.finished.emit()

	def run(self):
		self.worker = CObject()
		self.worker.run()
		self.worker.finished.connect(self.quit)
		self.worker.aborted.connect(self.aborted)
		
		count = 0
		while count < 5:
#			QCoreApplication.processEvents() # process CObject timer events 
			time.sleep(.5)
			print count
			count += 1

if __name__ == "__main__":
	import os, signal, sys

	try:
		app = QCoreApplication([])
		worker = SomeObject(sys.argv[1:], app)
		worker.finished.connect(lambda: app.exit(worker.result))
		worker.run()
		sys.exit(app.exec_())

	except Exception, e:
		print ' got an excpeption '
		print e
		traceback.print_exc(file=sys.stderr)
