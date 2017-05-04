# SFP Small Frame Synchronous Protocol	Robert Chapman III	Jul 4, 2012
# Bytes in and out are binary
# doesn't implement: SPS or routing
# callouts: newFrame, newPacket
# redefine newFrame and newPacket to get signals to know when to call
# distributer or txBytes
# call ins: rxBytes and sendNPS

import time
import sys
if sys.version_info > (3, 0):
	import queue as Queue
else:
	import Queue
from collections import deque
import pids
from sfpErrors import *

# sfp format: |0 length |1 sync |2 pid |3 payload | checksum |
#  sync = ~length
#  length = sizeof sync + sizeof pid + sizeof payload + sizeof checksum
#  pid = TALK_OUT
#  checksum covers: length + sync + pid + payload
LENGTH_LENGTH = 1
SYNC_LENGTH = 1
PID_LENGTH = 1
CHECKSUM_LENGTH = 2

# defines - lengths in bytes
MIN_FRAME_LENGTH = (SYNC_LENGTH + PID_LENGTH + CHECKSUM_LENGTH)
MAX_SFP_SIZE = (LENGTH_LENGTH + pids.MAX_FRAME_LENGTH)
MIN_SFP_SIZE = (LENGTH_LENGTH + MIN_FRAME_LENGTH)
FRAME_OVERHEAD = (MIN_FRAME_LENGTH - PID_LENGTH)

# protocol class
class sfpProtocol(object):
	VERBOSE = 0	 # set to non zero for debugging

	def __init__(self):
		self.receivedPool = Queue.Queue()  # holds received frames
		self.transmitPool = Queue.Queue()  # holds outgoing frames
		self.handler = {}  # for associating handlers with PIDs
		self.setHandler(pids.SPS, self.spsHandler)
		self.frame = deque() # incoming data
		self.sfpState = self.hunting  # receive states: hunting, syncing, receiving
		self.frameTime = time.time()  # to know when data is stale
		self.length = 0
		self.result = NO_ERROR
		self.message = ""
		self.spsbitExpect = None
		self.frameTimeout = pids.SFP_FRAME_TIME

	# receiver: frame contains received bytes and is parsed for a frame
	def rxBytes(self, bytes):  # run rx state machine receiver
		if self.VERBOSE:
			self.dump('RX: ', bytes)

		if self.frame and (time.time() - self.frameTime) > self.frameTimeout:
			self.frameTimeout += self.frameTimeout
			self.error(FRAME_TIMEOUT,"Frame timeout - resetting receiver")
			self.note("doubling timeout to %d"%self.frameTimeout)
			self.resetRx()
		else:
			self.frame.extend(bytes)
			while self.sfpState():
				pass
			if bytes:
				self.frameTime = time.time()

	# states
	def hunting(self):  # look for frame length
		if not self.frame:
			return False

		self.length = self.frame.popleft()
		self.result = self.checkLength()
		if self.result is LENGTH_OK:
			self.sfpState = self.syncing
			self.frameTime = time.time()
		elif self.result is LENGTH_SHORT:
			self.error(LENGTH_SHORT,"host: short frame")
		elif self.result is LENGTH_LONG:
			self.error(LENGTH_LONG,"host: long frame")
		return True

	def syncing(self):  # wait for sync byte
		if not self.frame:
			return False

		if self.checkSync(self.frame[0]):
			if self.VERBOSE:
				self.note(FRAME_SYNCED,"host: synced")
			self.sfpState = self.receiving
		else:
			if self.VERBOSE:
				self.error(NOT_SYNCED,"host: not synced")
			self.sfpState = self.hunting
		return True

	def receiving(self):  # receive rest of frame
		if len(self.frame) < self.length:
			return False

		self.sfpState = self.hunting
		if self.frameOk():
			frame = list(self.frame) # convert to list for slicing
			self.frame.clear()
			self.frame.extend(frame[self.length:])

			if frame[1] & ~pids.PID_BITS:
				self.spsFrame(frame)
			else:
				self.goodFrame(frame)
		else:
			self.error(BAD_CHECKSUM,"host: bad checksum")
		return True

	# support
	def resetRx(self):
		self.sfpState = self.hunting
		self.frame.clear()

	def initRx(self):  # to reinitialize an unsynced recevier
		self.warning(RX_RESET,"Receiver reset from state: %s	frame size: %i" % (self.sfpState.__name__, len(self.frame)))
		self.resetRx()

	def checkLength(self):
		if MIN_FRAME_LENGTH <= self.length <= pids.MAX_FRAME_LENGTH:
			return LENGTH_OK

		if self.length == 0 or self.length == 0xFF:
			return LENGTH_IGNORE

		if self.length < MIN_FRAME_LENGTH:
			return LENGTH_SHORT

		return LENGTH_LONG

	def checkSync(self, sync):
		return (~self.length & 0xFF) == sync

	def frameOk(self):	# check checksum
		sum = sumsum = self.length
		for index in range(self.length-CHECKSUM_LENGTH):
			sum += self.frame[index]
			sumsum += sum
		return sum&0xFF == self.frame[self.length-2] and sumsum&0xFF == self.frame[self.length-1]

	def checkSum(self, frame):	# calculate checksum
		sum = sumsum = 0
		for byte in frame:
			sum += byte
			sumsum += sum
		return (sum & 0xFF), (sumsum & 0xFF)

	# frame handlers
	def goodFrame(self, frame):
		if self.VERBOSE:
			self.note(GOOD_FRAME, "host: good frame")
		self.receivedPool.put(frame[1:self.length - CHECKSUM_LENGTH])
		self.newPacket()

	# SPS Frame: if ACK_BIT set, send an ack; if SPS_BIT is not expected, ignore frame
	def spsFrame(self, frame):
		self.sendNPS(pids.SPS_ACK)
		spsbit = frame[1] & pids.SPS_BIT
		if spsbit == self.spsbitExpect or self.spsbitExpect == None:
			self.spsbitExpect = spsbit ^ pids.SPS_BIT
			frame[1] &= pids.PID_BITS
			self.goodFrame(frame)
		else:
			self.result = IGNORE_FRAME

	# packet handlers
	def newPacket(self):  # redefine to receive packets
		pass

	def distributer(self):	 # distribute packets from queue
		if not self.receivedPool.empty():
			packet = self.receivedPool.get()
			pid = packet[0]
			handler = self.handler.get(pid)
			if handler:
				handler(packet[1:])
			elif pids.pids.get(packet[0]):
				self.error(NO_HANDLER,"Error: no handler for %s (0x%x)" % (pids.pids[packet[0]], packet[0]))
			else:
				self.dump("Error: unknown packet: 0x%x " % (packet[0]), packet)

	def spsHandler(self, packet):
		pass

	def setHandler(self, pid, handler):  # route packets to handler
		self.handler[pid] = handler

	def removeHandler(self, pid):  # remove packet handler
		if self.handler.get(pid):
			self.handler.pop(pid)

	# sending SFP frames
	def sendNPS(self, pid, payload=[]):  # send a payload via normal packet service
		length = len(payload) + FRAME_OVERHEAD + 1	 # pid is separate from payload
		sync = ~length & 0xff
		frame = [length, sync, pid] + payload
		sum, sumsum = self.checkSum(frame)
		frame.extend([sum, sumsum])
		if self.VERBOSE:
			self.dump("\nFrame TX:", frame)
		self.transmitPool.put(frame)
		self.newFrame()

	def newFrame(self):  # redefine to send a new frame
		pass

	def txBytes(self):
		if self.transmitPool:
			return self.transmitPool.get()
		return []

	# errors and messages
	def error(self, code = 0, string = ""):
		self.result = code
		self.message = string

	def warning(self, code = 0, string = ""):
		self.result = code
		self.message = string

	def note(self, code = 0, string = ""):
		self.result = code
		self.message = string

	def dump(self, tag, buffer):
		self.result = buffer
		self.message = tag
