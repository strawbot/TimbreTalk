# srecord transfer states  Robert Chapman  Dec 4, 2012
'''
call with parameters: parent, filename, target address, header flag
signals: progress, done, aborted
slots: stopSending, startSending
'''
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

printme = 0

# states
IDLE, ERASE, TRANSFER, VERIFY, STOPPING = range(5)

# parameters
NAME, START, TARGET, SIZE, ENTRY, CHECKSUM, HEADER, FILE, BOOTAPP = range(9)

# used for classifying errors from targets
memoryErrors = {
	0:'NO_ERRORS',
	0x01:'ERR_NOTAVAIL: Desired program/erase operation is not available',
	0x02:'ERR_RANGE: The address is out of range',
	0x03:'ERR_BUSY: Device is busy',
	0x04:'ERR_SPEED: This device does not work in the active speed mode',
	0x05:'ERR_PROTECT: Flash is write protected',
	0x06:'ERR_VALUE: Read value is not equal to written value',
	0x07:'ERR_PARAM_VALUE: destination address or length is odd'}

# srecord and target
PACKET_OVERHEAD = 1 		# pid
SIZE_OF_WHO = 2
WHO_PACKET_OVERHEAD = (PACKET_OVERHEAD+SIZE_OF_WHO)   # pid, who
MAX_PACKET_LENGTH = 100
EVALUATE_PACKET_OVERHEAD = WHO_PACKET_OVERHEAD # pid, who
MAX_WHO_PACKET_PAYLOAD = (MAX_PACKET_LENGTH - WHO_PACKET_OVERHEAD)
MEMORY_PACKET_OVERHEAD = 4 + 1 # 32bit address + length
maxMemTransfer = MAX_WHO_PACKET_PAYLOAD - MEMORY_PACKET_OVERHEAD

class sRecordTransfer(QObject):
	starting = Signal()
	aborted = Signal()
	done = Signal() # signal for done
	progress = Signal(object)
	eraseStart = Signal()
	transferStart = Signal()
	verifyStart = Signal()
	eraseFail = Signal()
	transferFail = Signal()
	verifyFail = Signal()
	eraseDone = Signal()
	transferDone = Signal()
	verifyDone = Signal()
	ecPacket = Signal(object)
	tcPacket = Signal(object)
	vcPacket = Signal(object)

	def __init__(self, parent, file='', target=0, header=0, whofor=0):
		if printme: print >>sys.stderr, '__init__'
		QObject.__init__(self) # needed for signals to work!!

		self.parent = parent

		# parameters derived
		self.start = 0
		self.size = 0
		self.entry = 0
		self.checksum = 0
		self.dir = ''
		self.version = 0
		# parameters passed
		self.target = target
		self.headerFlag = header
		self.whofor = whofor
		self.useFile(file)
		
		if file:
			self.getSrecord(file)

		# srecord setup
		self.sendState = IDLE
		self.transferTimer = QTimer()
		self.transferTimer.timeout.connect(self.sendAgain)

		# external signals
		self.ecPacket.connect(self.ecPacketHandler)
		self.tcPacket.connect(self.tcPacketHandler)
		self.vcPacket.connect(self.vcPacketHandler)
		
	def who(self):
		if self.whofor:			# use default
			return [self.whofor, self.parent.whofrom]
		return self.parent.who() # packet routing
			
	# slots
	def eraseConfirmed(self, packet):
		self.ecPacket.emit(packet)
	
	def transferConfirmed(self, packet):
		self.tcPacket.emit(packet)
	
	def verifyConfirmed(self, packet):
		self.vcPacket.emit(packet)
	

	# shutdown signal
	def shutdown(self):
		if printme: print >>sys.stderr, 'shutdown'
		pass
#		note('shutting down srecord transfer\r')

	# set filename and directory
	def useFile(self, file):
		if printme: print >>sys.stderr, 'useFile'
		self.file = file
		self.dir = ''
		self.time = 0
		self.filename = ''
		if file:
			self.time = os.path.getmtime(self.file) # remember for checking later
			x = self.file.rsplit('/', 1)
			if len(x) > 1:
				self.dir, self.filename = x
			else:
				self.dir, self.filename = '', x[0]
			self.loadSrecord()

	# load srecord as image
	def getSrecord(self, file):
		if printme: print >>sys.stderr, 'getSrecord'
		note('loading srecord: %s'%file)
		self.useFile(file)

	def loadSrecord(self):
		try:
			if printme: print >>sys.stderr, 'loadSrecord'
			srec = srecord.Srecord(self.file)
			self.start = srec.start
			self.size = srec.size
			self.entry = srec.entry
			self.image, self.checksum = srec.sRecordImage()
			version = map(ord, versionDate(self.image))
			self.releaseDate = version + [0]*(RELEASE_DATE_LENGTH - len(version))
			name = map(ord, versionName(self.image))
			self.appName = name + [0]*(APP_NAME_LENGTH - len(name))
			self.version = versionNumber(self.image)
		except Exception, e:
			print >>sys.stderr, e
			traceback.print_exc(file=sys.stderr)
	
	def checkLatest(self):
		if printme: print >>sys.stderr, 'checkLatest'
		if self.time != os.path.getmtime(self.file):
			warning(' disk image is newer - reloading ')
			t = self.target	# remember old addresses
			s = self.start
			self.loadSrecord()
			if self.start == s: # assume same target address if srecord same start
				self.target = t

	def headersize(self): # adjust header size for srecord
		if printme: print >>sys.stderr, 'headersize'
		if self.headerFlag:
			return HEADER_SIZE
		return 0

	def header(self):
		#	[ version# start dest size entry checksum headerSize releaseDate appName headerChecksum ]
		if printme: print >>sys.stderr, 'header'
		if self.headersize():
			version = longList(self.version)
			start = longList(self.target + self.headersize())
			dest = longList(self.start)
			size = longList(self.size)
			entry = longList(self.entry)
			checksum = longList(self.checksum)
			headerSize = longList(HEADER_SIZE)
			releaseDate = self.releaseDate
			appName = self.appName

			head = version + start + dest + size + entry + checksum \
				    + headerSize + releaseDate + appName
			headerChecksum = longList(fletcher32(head, HEADER_SIZE - 4))
			return head + headerChecksum
		return []

	# srecord downloading
	def fileOperation(self, operation):
		try:
			if printme: print >>sys.stderr, 'starting'
			if self.sendState == IDLE:
				self.whoto, self.whofrom = self.who()
				self.checkLatest()
				if not self.image: # image not loaded?
					error('No srecord image loaded.')
					self.stopSending()
					return
				header = self.header()
				filler = [0xff] * (self.start - self.target - len(header))
				self.download = header + filler + self.image[:self.size]
				self.targetPointer = self.target
				self.left = self.length = len(self.download)
				self.startTransferTime = time.time()
				self.progress.emit(0)
				self.parent.protocol.packetSource(pids.ERASE_CONF, self.eraseConfirmed)
				self.parent.protocol.packetSource(pids.WRITE_CONF, self.transferConfirmed)
				self.parent.protocol.packetSource(pids.MEM_CHECK, self.verifyConfirmed)
				self.starting.emit()
				operation()
				self.transferTimer.setInterval(15000)
				self.transferTimer.start()
				self.retries = 5
			else:
				self.stopSending()
		except Exception, e:
			print >>sys.stderr, e
			traceback.print_exc(file=sys.stderr)
			self.stopSending()

	def startSending(self):
		self.fileOperation(self.erase)
	
	def startVerify(self):
		self.fileOperation(self.verify)

	def abortSignal(self):
		if printme: print >>sys.stderr, 'abortSignal'
		if self.sendState == ERASE:
			self.eraseFail.emit()
		elif self.sendState == TRANSFER:
			self.transferFail.emit()
		elif self.sendState == VERIFY:
			self.verifyFail.emit()

	def stopSending(self):
		if printme: print >>sys.stderr, 'stopping'
		self.transferTimer.stop()
		if self.sendState == IDLE:
			return
		elif self.sendState != IDLE:
			if self.sendState != STOPPING:
				warning('stopSending: aborting send srecord')
				self.abortSignal()
				#traceback.print_stack()
			self.sendState = IDLE
			self.download = 0
			self.left = 0
			self.aborted.emit()
		self.done.emit()

	def gracefulExit(self):
		if printme: print >>sys.stderr, 'graceful exit'
		self.transferTimer.stop()
		if self.sendState != IDLE:
			if self.sendState != STOPPING:
				warning('gracefulExit: aborting send srecord')
				self.abortSignal()
			self.sendState = IDLE
			self.download = 0
			self.left = 0
		self.done.emit()

	# send again
	def sendAgain(self): # timeout occurred
		if printme: print >>sys.stderr, 'sendAgain'
		if self.sendState != IDLE:
			if self.retries:
				self.retries -= 1
				warning('Timed out, no response. Trying again...')
				if self.sendState == ERASE:
					self.erase()
				elif self.sendState == TRANSFER:
					self.sendChunk()
				elif self.sendState == VERIFY:
					self.verify()
			else:
				error('Too many timeouts. Giving up.')
				self.abortSignal()
				self.stopSending()
				self.transferTimer.stop()
		else:
			self.transferTimer.stop()

	# erasure
	def erase(self): # erase a section of flash memory
		if printme: print >>sys.stderr, 'erase'
		self.sendState = ERASE
		end = self.targetPointer + self.left
		note('Erasing flash - start: %X  end: %X ...'%(self.targetPointer,end))
		self.progress.emit(.5)
		self.eraseStart.emit()
		start = longList(self.targetPointer)
		end = longList(end)
		payload = [self.whoto, self.whofrom] + start + end
		self.parent.protocol.sendNPS(pids.ERASE_MEM, payload)
		
	def ecPacketHandler(self, packet): # confirmed that memory has been erased
		if printme: print >>sys.stderr, 'ecPacketHandler'
		if self.sendState != ERASE:
			self.stopSending()
			return
		result = cast('BBLLL', packet)[4]
		if result:
			message = memoryErrors.get(result) if result in memoryErrors else hex(result)
			error('Flash erase failed %s'%message)
			self.eraseFail.emit()
			self.stopSending()
		else:
			self.progress.emit(1)
			self.eraseDone.emit()
			elapsed = time.time() - self.startTransferTime
			note(' Flash erased in %.1f seconds'%elapsed)
			self.transferTimer.setInterval(2000)
			self.transfer()

	# transferring image
	def transfer(self):
		if printme: print >>sys.stderr, 'transfer'
		note('Transferring Image...')
		self.sendState = TRANSFER
		self.imagePointer = 0
		self.chunk = 0
		self.progress.emit(0)
		self.transferStart.emit()
		self.sendChunk()
		
	def sendChunk(self):
		if printme: print >>sys.stderr, 'sendChunk:',
		if self.sendState != TRANSFER:
			self.stopSending()
			return
		self.transferTimer.start()
		n = float(self.length - self.left)/self.length
		if printme: print >>sys.stderr, self.left
		self.progress.emit(n)
		if self.left >= maxMemTransfer:
			self.sent = maxMemTransfer
		else:
			self.sent = self.left
		who = [self.whoto, self.whofrom]
		address = longList(self.targetPointer)
		length = [self.sent]
		data = self.download[self.imagePointer:self.imagePointer+self.sent]
		payload = who+address+length+data
		self.parent.protocol.sendNPS(pids.FLASH_WRITE, payload)

	def tcPacketHandler(self, packet):
		if printme: print >>sys.stderr, 'tcPacketHandler'
		if self.sendState != TRANSFER:
			self.stopSending()
			return
		result = cast('BBLBB', packet)[4]
		if result:
			message = memoryErrors.get(result) if result in memoryErrors else hex(result)
			error('Memory write failed: %s at address: %X'%(message, self.targetPointer))
#			self.transferFail.emit()
#			self.stopSending()
		else:
			self.retries = 5
			self.chunk += 1
			self.left -= self.sent
			self.targetPointer += self.sent
			self.imagePointer += self.sent
			if self.left:
				self.sendChunk()
			else:
				self.transferDone.emit()
				self.transferTimer.setInterval(4000)
				self.transferTimer.start()
				self.verify()

	# verifying
	def verify(self):
		if printme: print >>sys.stderr, 'verify'
		note('Verifying...')
		self.sendState = VERIFY
		who = [self.whoto, self.whofrom]
		address = longList(self.target)
		length = longList(len(self.download))
		payload = who+address+length
		self.parent.protocol.sendNPS(pids.CHECK_MEM, payload)
		self.progress.emit(0)
		self.progress.emit(.50)
		self.verifyStart.emit()
		
	def vcPacketHandler(self, packet):
		if printme: print >>sys.stderr, 'vcPacketHandler'
		if self.sendState != VERIFY:
			self.stopSending()
			return
		targetCheckSum = cast('BBLLL', packet)[4]
		hostCheckSum = fletcher32(self.download, len(self.download))
		if targetCheckSum == hostCheckSum:
			self.progress.emit(1)
			self.verifyDone.emit()
			note('Verified.\n')
			self.transferStats()
		else:
			error('Target image is different.')
			self.verifyFail.emit()
		self.sendState = STOPPING
		self.gracefulExit()

	def transferStats(self):
		if printme: print >>sys.stderr, 'transferStats'
		if self.left == 0:
			elapsed = time.time() - self.startTransferTime
			transferMsg = 'Finished in %.1f seconds'%elapsed
			rate = (8*len(self.download))/(elapsed*1000)
			rateMsg = ' @ %.1fkbps'%rate
			note(transferMsg+rateMsg)

class ubootTransfer(sRecordTransfer):
	MAX_IMAGE_SIZE = 1024 * 1024 # 1MB
	HOLE_FILL = 0xFF

	def getSrecord(self, file):
		if printme: print >>sys.stderr, 'getImage'
		note('loading image: %s'%file)
		self.useFile(file) # calls loadSrecord

	def loadSrecord(self):
		if printme: print >>sys.stderr, 'loadImage'
		try:
			self.image = map(ord, open(self.file, 'rb').read())
			self.size = len(self.image)
			self.checksum = fletcher32(self.image, self.size)
			date = extractUbootDate(self.image)
			self.version = buildVersion(date)
			self.releaseDate = [0]*RELEASE_DATE_LENGTH
			self.releaseDate[:len(date)] = map(ord, date)
			self.appName = [0]*APP_NAME_LENGTH
			self.appName[:len(ubootTag)] = map(ord, ubootTag)
			if printme: print >>sys.stderr, self.size, self.checksum
		except Exception, e:
			print >>sys.stderr, e
			traceback.print_exc(file=sys.stderr)
