# PID ports  Robert Chapman III  12/12/12

# a thread is started for each pidxxin port for any packets pushed on that port
# any packets received for that pid are pushed to that pid
# ? who can connect? How many can connect? can multiple processes input to a common?
# ? how can one obtain control of a port? Can it be analogous to packetSource?

from pyqtapi2 import *

import sys
import os
from signalcatch import initSignalCatcher

def pidinport(pid):
	return 'pid%din'%pid

def pidoutport(pid):
	return 'pid%dout'%pid

printme = 0

class pidServer(QThread):
	'''
	An input and output pipe are created. For pid 32 (decimal)
	 pid32in and pid32out will be created.
	To access them, pid32in should be opened as: pid32in = os.open('pid32in', os.O_WRONLY)
	  pid32out should be opened as: pid32out = open('pid32out', 'r')
	Usage:
	 os.write(pid32out, string)
	 pid32in.readline()[:-1]
	'''
	def __init__(self, pid):
		if printme: print >>sys.stderr, '__init__'
		QThread.__init__(self) # needed for signals to work!!
		initSignalCatcher()
		
		pidin = pidinport(pid)
		pidout = pidoutport(pid)
		
		if os.path.exists(pidin):
			os.remove(pidin)
		os.mkfifo(pidin)  # only on unix; use remove or unlink to get rid of
		
		if os.path.exists(pidout):
			os.remove(pidout)
		os.mkfifo(pidout)
		
		self.pout = self.pidOutOpen(pid)
		self.pin = self.pidInOpen(pid)
					
	def pidInOpen(self, pid):
		if printme: print >>sys.stderr, 'pidInOpen'
		return os.open(pidinport(pid), os.O_WRONLY)
	
	def pidOutOpen(self, pid):
		if printme: print >>sys.stderr, 'pidOutOpen'
		return open(pidoutport(pid), 'r')
	
	def read(self):
		if printme: print >>sys.stderr, 'read'
		print >>sys.stderr, self.pin.readline()[:-1]
	
	def write(self, s):
		if printme: print >>sys.stderr, 'write'
		os.write(self.pout, s)

class pidClient(QThread):
	'''
	Client for server above. Server should go first
	'''
	def __init__(self, pid):
		if printme: print >>sys.stderr, '__init__'
		QThread.__init__(self) # needed for signals to work!!
	
		pidin = pidinport(pid)
		pidout = pidoutport(pid)
		
		if not os.path.exists(pidin):
			print >>sys.stderr, 'no port from server found'
		if not os.path.exists(pidout):
			print >>sys.stderr, 'no port from server found'
		
		self.pin = self.pidInOpen(pid)
		self.pout = self.pidOutOpen(pid)
					
	def pidInOpen(self, pid):
		if printme: print >>sys.stderr, 'pidInOpen'
		return os.open(pidoutport(pid), os.O_WRONLY)
	
	def pidOutOpen(self, pid):
		if printme: print >>sys.stderr, 'pidOutOpen'
		return open(pidinport(pid), 'r')

	def read(self):
		if printme: print >>sys.stderr, 'read'
		print >>sys.stderr, self.pin.readline()[:-1]
	
	def write(self, s):
		if printme: print >>sys.stderr, 'write'
		os.write(self.pout, s)

if __name__ == "__main__":
	s = pidServer(22)
