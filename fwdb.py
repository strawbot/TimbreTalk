#!/usr/bin/env python

from pyqtapi2 import *

import os, time, traceback
import srecord, pids
from endian import *
from message import *
from checksum import fletcher32
from targets import *
import sys, traceback	
from buildversion import *
from cpuids import *
from struct import *
from firmwarespids import *
from packagedatabase import *

printme = 0
isMainWaitTime = 120
retryInterval = 5
isMainRetries = isMainWaitTime / retryInterval
REBOOT_TIME_SEC = 2
LEFT, RIGHT = 0,1

class fwdb(QObject):
	
	donePass = Signal() # signal for done
	doneFail = Signal() # signal for done
	progress = Signal(object)
	fwPacket = Signal(object)
	guidPacket = Signal(object)

	#runningChoice;    # Byte   
        #pendingChoice;    # Byte   
        #mainboot;         # long_t 
        #database;         # long_t 
        #packageLeft;      # long_t 
        #launcherLeft;     # long_t 
        #mainappLeft;      # long_t 
        #ubootLeft;        # long_t 
        #linuxLeft;        # long_t 
        #displayappLeft;   # long_t 
        #ioappLeft;        # long_t 
        #swbappLeft;       # long_t 
        #packageRight;     # long_t 
        #launcherRight;    # long_t 
        #mainappRight;     # long_t 
        #ubootRight;       # long_t 
        #linuxRight;       # long_t 
        #displayappRight;  # long_t 
        #ioappRight;       # long_t 
        #swbappRight;      # long_t 
        #slotaType;        # long_t 
        #slotbType;        # long_t 

	def __init__(self, parent, target=0, whofor=0):
		if printme: print >>sys.stderr, '__init__'
		QObject.__init__(self) # needed for signals to work!!
		self.parent = parent
		# parameters passed
		self.target = target
		self.whofor = whofor
		self.whoto, self.whofrom = self.who()
		
		self.fwPacket.connect(self.fwPacketHandler)
		self.parent.protocol.packetSource(pids.FIRMWARE, self.fwHandle)
		
		self.guidPacket.connect(self.guidPacketHandler)
		self.parent.protocol.packetSource(pids.GUID, self.guidHandle)
		self.transferTimer = QTimer()
		
	
	def who(self):
		who = self.parent.who() # packet routing
		if who[0] == SLOTB_CPU:
			return who

		if self.whofor:			# use default
			return [self.whofor, self.parent.whofrom]

		return who

	def printFwDb(self):
		print >>sys.stderr, 'runningChoice   {0}'.format(self.runningChoice)
        	print >>sys.stderr, 'pendingChoice   {0}'.format(self.pendingChoice)
        	print >>sys.stderr, 'mainboot        {0}'.format(self.mainboot)
        	print >>sys.stderr, 'database        {0}'.format(self.database)
        	print >>sys.stderr, 'packageLeft     {0}'.format(self.packageLeft)
        	print >>sys.stderr, 'launcherLeft    {0}'.format(self.launcherLeft)
        	print >>sys.stderr, 'mainappLeft     {0}'.format(self.mainappLeft)
        	print >>sys.stderr, 'ubootLeft       {0}'.format(self.ubootLeft)
        	print >>sys.stderr, 'linuxLeft       {0}'.format(self.linuxLeft)
        	print >>sys.stderr, 'displayappLeft  {0}'.format(self.displayappLeft)
        	print >>sys.stderr, 'ioappLeft       {0}'.format(self.ioappLeft)
        	print >>sys.stderr, 'swbappLeft      {0}'.format(self.swbappLeft)
        	print >>sys.stderr, 'packageRight    {0}'.format(self.packageRight)
        	print >>sys.stderr, 'launcherRight   {0}'.format(self.launcherRight)
        	print >>sys.stderr, 'mainappRight    {0}'.format(self.mainappRight)
        	print >>sys.stderr, 'ubootRight      {0}'.format(self.ubootRight)
        	print >>sys.stderr, 'linuxRight      {0}'.format(self.linuxRight)
        	print >>sys.stderr, 'displayappRight {0}'.format(self.displayappRight)
        	print >>sys.stderr, 'ioappRight      {0}'.format(self.ioappRight)
        	print >>sys.stderr, 'swbappRight     {0}'.format(self.swbappRight)
        	print >>sys.stderr, 'slotaType       {0}'.format(self.slotaType)
        	print >>sys.stderr, 'slotbType       {0}'.format(self.slotbType)
		

	def extractFwDbInfo(self, data):
		fwDpPacketFormat = 'BBLLLLLLLLLLLLLLLLLLLL'
		self.runningChoice, self.pendingChoice, self.mainboot, self.database, self.packageLeft, self.launcherLeft, self.mainappLeft, self.ubootLeft, self.linuxLeft, self.displayappLeft, self.ioappLeft, self.swbappLeft, self.packageRight, self.launcherRight, self.mainappRight, self.ubootRight, self.linuxRight, self.displayappRight, self.ioappRight, self.swbappRight, self.slotaType, self.slotbType = cast(fwDpPacketFormat, data)
		self.printFwDb()
		return 0

	def sendAgain(self, payload):
		if printme: print >>sys.stderr, 'sendAgain'
		if self.retries:
			self.retries = self.retries - 1
			self.parent.protocol.sendNPS(payload[0], payload[1:])
		else:
			self.doneFail.emit()

	def send(self, payload):
		self.transferTimer.stop()
		self.transferTimer.timeout.connect(lambda: self.sendAgain(payload))
		self.transferTimer.setInterval(retryInterval * 1000)
		self.transferTimer.start()
		self.sendAgain(payload)
		

	def printPackageLeft(self):
		print >>sys.stderr, '{0}'.self.packageLeft;
	
	def printPackageLeft(self):
		print >>sys.stderr, '{0}'.self.packageRight;

	def setDefaultRetries(self):
		self.retries = 2
	
	def invalidate(self, side):
		if printme: print >>sys.stderr, 'invalidate'
		note('Invalidating ...')

		payload = [pids.FIRMWARE, self.whoto, self.whofrom, FWDB_INVALIDATE, side]
		self.setDefaultRetries()
		self.send(payload)
		return 0
	
	def rebuild(self, side):
		if printme: print >>sys.stderr, 'rebuild'
		note('rebuilding ...')

		payload = [pids.FIRMWARE, self.whoto, self.whofrom, FWDB_REBUILD, side]
		self.setDefaultRetries()
		self.send(payload)
		return 0
	
	def setBoot(self, side):
		if printme: print >>sys.stderr, 'set boot'
		note('set boot ...')

		payload = [pids.FIRMWARE, self.whoto, self.whofrom, FWDB_SET_CHOICE, side]
		self.setDefaultRetries()
		self.send(payload)
		return 0
	
	def reboot(self):
		if printme: print >>sys.stderr, 'reboot'
		note('reboot ...')

		payload = [pids.FIRMWARE, self.whoto, self.whofrom, FWDB_REBOOT, REBOOT_TIME_SEC]
		self.setDefaultRetries()
		self.send(payload)
		return 0
	
	def getVersion(self):
		if printme: print >>sys.stderr, 'query version'
		note('query version ...')

		payload = [pids.FIRMWARE, self.whoto, self.whofrom, FWDB_QUERY_REQ]
		self.setDefaultRetries()
		self.send(payload)
		return 0
	
	def isMain(self):
		if printme: print >>sys.stderr, 'query main'
		note('query main ...')

		payload = [pids.GUID, 0x01, 0x02, 0x00, 0x00, 0x06, 0x03, 0x8f]
		self.retries = isMainRetries;
		self.send(payload)
		return 0
	
	def sendOp(self, op, side):
		rtn = -1
		
		if side == LEFT:
			side = IMAGE_LEFT
		elif side == RIGHT:
			side = IMAGE_RIGHT
		else:
			side = IMAGE_LEFT

		if op == 'invalid':
			rtn = self.invalidate(side)
		elif op == 'rebuild':
			rtn = self.rebuild(side)
		elif op == 'setboot':
			rtn = self.setBoot(side)
		elif op == 'reboot':
			rtn = self.reboot()
		elif op == 'version':
			rtn = self.getVersion()
		elif op == 'ismain':
			rtn = self.isMain()

		return rtn

	def fwHandle(self, packet):
		if printme: print >>sys.stderr, 'fw handle'
		self.fwPacket.emit(packet)
	
	def guidHandle(self, packet):
		if printme: print >>sys.stderr, 'guid handle'
		self.guidPacket.emit(packet)
	
	def fwPacketHandler(self, packet):
		if printme: print >>sys.stderr, 'fw packet handler {0}'.format(packet)
		self.transferTimer.stop()
		#whoTo, whoFrom, spid = unpack('>BBB', packet[:3])
		#whoTo, whoFrom, spid = unpack('>BBB', ''.join(chr(x) for x in packet[:3]))
		whoTo, whoFrom, spid = cast('BBB', packet[:3])

		if spid == FWDB_QUERY_RESP:
			rtn = self.extractFwDbInfo(packet[3:])
		elif spid == FWDB_INVALIDATE_RESP:
			rtn = 0
		elif spid == FWDB_REBUILD_RESP:
			rtn = 0
		elif spid == FWDB_REBOOT_RESP:
			rtn = 0
		elif spid == FWDB_SET_CHOICE_RESP:
			rtn = 0
		else:
			rtn = -1

		if rtn == 0:
			self.donePass.emit()
		else:
			self.doneFail.emit()

	def guidPacketHandler(self, packet):
		if printme: print >>sys.stderr, 'guid packet handler'
		self.transferTimer.stop()
		self.donePass.emit()

