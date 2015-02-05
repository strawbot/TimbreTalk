# machines in Python  Robert Chapman III  Sep 4, 2013

'''
Machines are a concept related to threading. There is a central queue of machines
to be run sequentially. New machines are prepended to this queue. Each machine is
pulled from the queue and it is run. When it completes the next machine is run.
Machines take no arguments and leave no results. Machines are code segments and do
not pause nor block. When there are no machines to be run, the machine runner will
block.

Code has been added to simulate the Qt application, threading and object classes
along with signals. If a signal has an argument it is executed immediately (could
queue the argument I suppose...). If the signal has no argument, it is queued as
a machine.

Could detect if qt api is available and then call it instead.
'''
printme = 0
done = 0

import Queue, threading, time
import os
import sys

machineq = Queue.Queue()

def doneMachines():
	global done
	done = 1
	if printme:
		print >>sys.stderr, 'threads running:'
		threading.enumerate()

def runMachines():
	if printme: print >>sys.stderr, 'running machines'
	while not done:
		machineq.get()() # run the gotten machine
	if printme: print >>sys.stderr, 'machines done'

def activate(machine):
	if printme: print >>sys.stderr, 'activating %s'%machine.func_name
	machineq.put(machine)

def deactivate(machine):
	if printme: print >>sys.stderr, 'deactivating %s'%machine.func_name
	name = machine.func_name
	size = machineq.qsize()
	while size:
		size -= 1
		machine = machineq.get()
		if machine.func_name != name:
			machineq.put(machine)


# signal model to replace Qt stuff
def noop(n=0):
	pass

class Qt():
	QueuedConnection = 0

class Signal(object):
	def __init__(self, object = None):
		self.disconnect()
		
	def connect(self, vector, option=0):
		if printme: print >>sys.stderr, 'connecting to %s'%(vector.func_name)
		if self.vector != noop:
			print >>sys.stderr, 'overwriting connection with %s'%vector.func_name
		self.vector = vector

	def emit(self, arg=None):
		if printme:
			#self.print_my_name()
			print >>sys.stderr, 'emitting'
		if arg == None:
			activate(self.vector)
		else:
			self.vector(arg)

	def disconnect(self):
		self.vector = noop

def pyqtSignal(object=None):
	return Signal(object)

class QObject(object):
	def __init__(self, child=None):
		pass

class QThread(threading.Thread):
	def wait(self, delayMilliSeconds):
		time.sleep(delayMilliSeconds/1000.0)
	
	def start(self):
		self.daemon = True # allows program to terminate if thread is still running
		super(QThread, self).start()

	def quit(self):
		pass
	# cannot quit a thread but since it is a daemon thread it will end by ending the program

class QCoreApplication(QObject):
	def __init__(self, args=[]):
		self.aboutToQuit = Signal()

	def quit(self):
		self.aboutToQuit.emit()
		doneMachines()
	
	def exit(self, n):
		self.aboutToQuit.emit()
		doneMachines()
		os._exit(n)

	def exec_(self):
		if printme: print >>sys.stderr, 'starting up application'
		runMachines()

class QTimer():
	terminate = 0

	def __init__(self):
		self.timeout = Signal()
		self.timer = 0
		self.sec = 0

	def setInterval(self, msec):
		self.sec = msec/1000.0
		if self.timer:
			self.timer.cancel()
			self.start()

	def start(self):
		if self.timer:
			self.timer.cancel()

		if self.sec:
			self.timer = threading.Timer(self.sec, self.run)
			self.timer.start()
	
	def run(self):
		if self.terminate or done:
			return
		self.timeout.emit()
		if self.sec:
			if self.timer:
				self.timer.cancel()
			self.timer = threading.Timer(self.sec, self.run)
			self.timer.start()
		

	def stop(self):
		print >>sys.stderr, "QTimer stop"
		if self.timer:
			self.sec = 0
			self.timer.cancel()
			self.timer = 0
		
# test
if __name__ == '__main__':
	n = 10
	def test1():
		global n
		if n:
			print >>sys.stderr, n
			n -= 1
			activate(test1)
			if n == 5:
				deactivate(test2)
		else:
			doneMachines()
		
	def test2():
		print >>sys.stderr, 'beep'
		activate(test2)

	activate(test1)
	activate(test2)
	activate(noop)
	runMachines()
		

