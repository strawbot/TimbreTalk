
from pyqtapi2 import *

import sys, time, os, Queue
from signalcatch import initSignalCatcher
from struct import *
import array
try: 
	import posix_ipc
except:
	import no_posix_ipc as posix_ipc
		
class sfpMessageQueRecv(QThread): # Receive messages from the message queue.
	def __init__(self, mqName, packetq):
		QThread.__init__(self)
		self.packetq = packetq
		self.mqName = mqName
		# TODO use a timeout option on the queue. 
		self.mqRecv = posix_ipc.MessageQueue(self.mqName)	
		
		initSignalCatcher()
		
	def run(self): 
		while True:
			(message, priority) = self.mqRecv.receive()
			#message = array.array('B', message)
			message = map(ord, message)
			self.packetq.put(message)

class sfpMessageQueSend(): 
	def __init__(self, mqName):
		self.mqName = mqName
		# TODO use a timeout option on the queue. 
		self.mqSend = posix_ipc.MessageQueue(self.mqName)

	def sink(self, frame): 
		lengthOfFrame = ord(frame[0]) + 1	
		pidIndex = 2
		crcLength = 2
		lastPayloadByteIndex = lengthOfFrame - crcLength
		self.mqSend.send(frame[pidIndex:lastPayloadByteIndex])
