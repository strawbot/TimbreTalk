# SFSP Small Frame Synchronous Protocol  Robert Chapman III  Jul 4, 2012

# sfsp format: |0 length |1 sync |2 pid |3 payload | checksum |
#  sync = ~length
#  length = sizeof payload + 4
#  pid = TALK_OUT
#  payload = k
#  checksum = length + sync + pid + payload

from pyqtapi2 import *

import sys, time, os, Queue
from signalcatch import initSignalCatcher
from message import *

# packet ids
from pids import *

MAX_PACKET_LENGTH = 100		# this should be shared with sfap.py
MAX_PAYLOAD_LENGTH = MAX_PACKET_LENGTH - 1 # pid not part of payload
MIN_SFSP_LENGTH = 4
FRAME_OVERHEAD = (MIN_SFSP_LENGTH - 1) # bytes used for transporting frame excluding pid
MIN_SFSP_FRAME = (MIN_SFSP_LENGTH + 1) # length, sync, pid, checksum(2)
MAX_SFSP_LENGTH = (MAX_PACKET_LENGTH + MIN_SFSP_LENGTH)
MAX_SFSP_FRAME = (MAX_SFSP_LENGTH + 1)
PACKET_OVERHEAD = 1 		# pid
WHO_SIZE = 2
WHO_PACKET_OVERHEAD = (PACKET_OVERHEAD+WHO_SIZE)   # pid, who
TID_SIZE = 2
SPID_SIZE = 1
SPID_PACKET_OVERHEAD = WHO_PACKET_OVERHEAD + TID_SIZE + SPID_SIZE   # pid, who, tid, spid
MAX_WHO_PACKET_PAYLOAD = (MAX_PACKET_LENGTH - WHO_PACKET_OVERHEAD)
MAX_SPID_PACKET_PAYLOAD = (MAX_PACKET_LENGTH - SPID_PACKET_OVERHEAD)

LENGTH_OK = 1
LENGTH_LONG = 2
LENGTH_SHORT = 3

# protocol class
class sfspProtocol(QThread):
	
	source = Signal(object)
	byteTimeout = Signal()
	sinkBytes = Signal()
	packetHandler = {}
	frame = []
	VERBOSE = 0

	def __init__(self):
		super(sfspProtocol, self).__init__() # needed for signals to work!!
		self.sfspState = self.hunting	# states: hunting, syncing, receiving
		self.talkTarget = 0
		self.lastsink = time.time()
		self.loinputs = 0
		self.looutputs = 0
		self.hiinputs = 0
		self.hioutputs = 0
		self.inpackets = 0
		self.outpackets = 0
		
#		initSignalCatcher()

		# separate thread for packet distributer
		class packetDistributer(QThread): # distribute packets from queue
			def __init__(self, q, ph):
				QThread.__init__(self)
				self.q = q
				self.ph = ph
				
			def run(self): # route packet to proper place
				while True:
					try:
						packet = self.q.get()
					except:
						break;
					pid = packet[0]
					handler = self.ph.get(pid)
					if handler:
						handler(packet[1:])
					else:
						self.unknownPacket(packet)

			def unknownPacket(self, packet): # no handler for this packet
				if pids.get(packet[0]):
					error("Error: no handler for %s (0x%x)" %(pids[packet[0]], packet[0]))
				else:
					messageDump("Error: unknown packet: 0x%x " %(packet[0]), packet)

		self.packetq = Queue.Queue()
		self.pd = packetDistributer(self.packetq, self.packetHandler)
		self.pd.start()
		
		# incoming byte stream
		self.sinkBytes.connect(self.processBytes)
		self.byteTimer = QTimer()
		self.byteTimer.timeout.connect(self.processBytes)
		self.byteTimer.setInterval(100)
		self.byteTimer.start()

		self.byteTimeout.connect(self.initRx)
		
		def pingBack(packet): # responder
			self.sendNPS(PING_BACK, [])
		self.packetSource(PING, pingBack)

	# thread for receiver
	def processBytes(self): # run rx state machine receiver
		t = time.time()
		if len(self.frame):
			if (t - self.lastsink) > 15:
				error("Frame timeout - resetting receiver")
				self.byteTimeout.emit()
			else:
				self.sfspState()					
		self.lastsink = t

	# shutdown signal
	def shutdown(self):
		pass
#		note('shutting down SFP\n\r')

	def resetRx(self):
		self.sfspState = self.hunting
		del self.frame[:]

	def initRx(self): # to reinitialize an unsynced recevier
 		warning("Receiver reset from state: %s  frame size: %i"%(self.sfspState.__name__, len(self.frame)))
		self.resetRx()

	# sending SFSP frames
	def sendNPS(self, pid, payload): # send a payload via normal packet service
		self.outpackets += 1
		self.hioutputs += len(payload) + 1
		length = len(payload) + FRAME_OVERHEAD + 1 # pid is separate from payload
		sync = ~length & 0xff
		frame = [length, sync, pid]
		for c in payload:
			try:
				i = ord(c)
			except:
				i = int(c)
			frame.append(i)
		sum1, sum2 = self.checkSum(frame)
		frame.extend([sum1 & 0xff, sum2 & 0xff])
#		print >>sys.stderr, 'sfsp lower source %s'%type(frame)
		self.source.emit(''.join(map(chr, frame)))
		if self.VERBOSE:
			messageDump("\nFrame TX:",frame)
		self.looutputs += len(frame)
	
	# receiving SFSP frames
	
	def routeFrame(self): # pass frame to packet layer
		#print >>sys.stderr, 'sfsp upper source %s'%type(self.frame)
		pid = self.frame[2]
		if pid: # pid of zero is empty sps packet
			self.packetq.put(self.frame[2:self.frame[0]-1])
			# [6,~6,pid,x,y,cs1,cs2] packet = pid,x,y
	
	# support
	def sfspLengthOk(self, length):
		if length >= MIN_SFSP_LENGTH:
			if length <= MAX_SFSP_LENGTH:
				return LENGTH_OK
			elif length < 255:
				return LENGTH_LONG
		else:
			return LENGTH_SHORT
	
	def sfspSync(self, length, sync):
		return (~length & 0xFF) == sync

	def frameOk(self): # check checksum
		sum1, sum2 = self.checkSum(self.frame)
		end = self.frame[0]
		return (sum1 == self.frame[end-1]  and  sum2 == self.frame[end])
	
	def checkSum(self, frame): # calculate checksum
		sum1 = sum2 = 0
		for i in range(0, frame[0]-1):
			sum1 += frame[i]
			sum2 += sum1
		return ((sum1 & 0xFF), (sum2 & 0xFF))
	
	# Receiver states
	def hunting(self): # look for frame length
		if len(self.frame) > 0:
			lengthValue = self.sfspLengthOk(self.frame[0])
			if lengthValue is LENGTH_OK:
				self.sfspState = self.syncing
				self.frameStart = time.time() # use to discard stale bytes
				self.bytesToReceive = self.frame[0]
				self.sfspState() # recursive
			else:
				if lengthValue is LENGTH_SHORT:
					error("host: short frame")
				else:
					error("host: long frame")
				del(self.frame[0])
				
	def syncing(self): # wait for sync byte
		if len(self.frame) > 2:
			if self.sfspSync(self.frame[0], self.frame[1]):
				if self.VERBOSE:
					note("host: synced")
				self.sfspState = self.receiving
				self.sfspState() # recursive
			else:
				if self.VERBOSE:
					error("host: not synced")
				del(self.frame[0:2])

	def receiving(self): # receive rest of frame
		if len(self.frame) > self.frame[0]:
			self.sfspState = self.hunting
			if self.frameOk():
				if self.VERBOSE:
					note("host: good frame")
				if self.frame[2] & ACK_BIT:
					self.spsFrame()
				self.routeFrame()
				self.inpackets += 1
				self.hiinputs += self.frame[0] - 3
				del self.frame[0:self.frame[0]+1]
				self.sfspState() # recursive
			else:
				error("host: bad checksum")
				del self.frame[0]
			
	def dumping(self): # dump rest of received frame
		pass

	def spsFrame(self): # handle sps frames
#			frame.after_idle(faketransfer)
		self.sendNPS(SPS_ACK, [])
		self.frame[2] &= PID_BITS

	def sink(self, c): # external sink
		#print >>sys.stderr, 'sfsp lower sink %s'%type(c)
		self.loinputs += len(c)
		self.frame += map(ord,c)
		if self.VERBOSE:
#			o = ord(c)
#			if c < ' ' or c > '~':
#				c = '<>'
#			string = 'RX: %X "%s"'%(o,c)
			messageDump('RX: ',c)
		self.sinkBytes.emit()

	# packet handlers
	def packetSource(self, pid, handler): # route packets to handler
		self.packetHandler[pid] = handler
	
	def removeHandler(self, pid): # remove packet handler
		if self.packetHandler.get(pid):
			self.packetHandler.pop(pid)
