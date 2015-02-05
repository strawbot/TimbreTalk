#!/usr/bin/env python
# part of http://stackoverflow.com/questions/6783194/background-thread-with-qthread-in-pyqt
#from PyQt4 import QtCore
from pyqtapi2 import *
import time
import sys, traceback

class BThread(QThread):
	def run(self):
		count = 1
		while count < 5:
			time.sleep(.5)
			print "Bthread"
			count += 1
#		self.abort.emit()
#		raise Exception('abort')
		
# Subclassing QThread
# http://doc.qt.nokia.com/latest/qthread.html
class AThread(QThread):
	done = False
	err = 0
	def run(self):
#		try:
		if True:
			self.setTerminationEnabled()
			count = 0
			bt = BObject() #BThread()
			bt.finished.connect(self.abort)
			bt.run() #start()
			bt.timer.start()
			while count < 5:
				time.sleep(1)
				print "Athread"
				count += 1
				if count == 20:
					raise Exception('abort')
			while not self.done:
				time.sleep(.1)
#		except Exception, e:
#			print ' got and excpetion '
#			self.quit()
#			self.err = -1
#			print e
#			traceback.print_exc(file=sys.stderr)

	def abort(self):
		print 'aborting'
		self.quit()
		raise Exception('abort')

#
class BObject(QThread):
	err = 0
#	finished = pyqtSignal()
	aborted = pyqtSignal()
	
	def run(self):
		print 'b run'
		self.setTerminationEnabled()
		self.count = 1
		self.timer = QTimer()
		self.timer.timeout.connect(self.work)
		self.timer.setInterval(.1)
 		self.timer.start()
 		self.exec_()

	def work(self):
		print "Bthread", self.count
		self.count += 1
		if self.count >= 5:
			self.timer.stop()
			self.aborted.emit()
			self.exit(self.err)

class CObject(QObject):
	err = 0
	done = False
	finished = pyqtSignal()
	aborted = pyqtSignal()
	
	def run(self):
		print 'b run'
		self.count = 1
		self.timer = QTimer()
		self.timer.timeout.connect(self.work)
		self.timer.setInterval(1500)
 		self.timer.start()

	def work(self):
		print "Cthread", self.count
		self.count += 1
		if self.count >= 5:
			self.timer.stop()
			self.aborted.emit()
			self.finished.emit()
			self.done = True
			print 'signals emitted'

# Subclassing QObject and using moveToThread
# http://labs.qt.nokia.com/2007/07/05/qthreads-no-longer-abstract/
class SomeObject(QObject):
	err = 0
	done = False
	finished = pyqtSignal()
	quitthread = pyqtSignal()

	def aborted(self):
		print 'aborted'
		self.err = -1
		self.isDone()

	def isDone(self):
		print 'isdone'
		self.done = True

	def run(self):
		count = 0
# 		self.thread = QThread()
# 		self.worker = CObject()
# 		self.worker.moveToThread(self.thread)
# 		#QMetaObject.invokeMethod(self.worker.run, Qt.QueuedConnection)
# 		self.thread.started.connect(self.worker.run, Qt.QueuedConnection)
# 		self.worker.aborted.connect(self.aborted, Qt.QueuedConnection)
# 		self.worker.finished.connect(self.quitthread, Qt.QueuedConnection)
# 		self.quitthread.connect(self.thread.quit, Qt.QueuedConnection)
# 		self.thread.finished.connect(self.isDone, Qt.QueuedConnection)
# 		self.thread.start()
		self.worker = CObject()
		self.worker.run()
		self.worker.finished.connect(self.isDone)
		self.worker.aborted.connect(self.aborted)
		
		while count < 5:
			time.sleep(.5)
			print count
			count += 1

# 		while not self.done:
# 				pass
				#self.thread.quit()
# 			else:
# 				print 'thread wait'
			
		while not self.done:
			QCoreApplication.processEvents()
			time.sleep(.5)
		self.finished.emit()

if __name__ == "__main__":
# 	app = QCoreApplication([])
# 	thread = AThread()
# 	thread.finished.connect(lambda: app.exit(thread.err))
# 	thread.start()
# 	sys.exit(app.exec_())

	try:
		app = QCoreApplication([])
		objThread = QThread()
		obj = SomeObject()
		obj.moveToThread(objThread)
		obj.finished.connect(objThread.quit)
		objThread.started.connect(obj.run)
		objThread.finished.connect(lambda: app.exit(obj.err))
		objThread.start()
		sys.exit(app.exec_())
	except Exception, e:
		print ' got and excpetion '
		print e
		traceback.print_exc(file=sys.stderr)
