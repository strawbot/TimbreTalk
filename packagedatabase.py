# firmware database  Robert Chapman III  Sep 18, 2013

from pyqtapi2 import *

import struct
from endian import *
from cpuids import *
import pids
import sys, traceback
from checksum import *
from firmwarespids import *

printme = 0

# mirror values in memorymaps.h
FERAM_BASE_ADDRESS = 0x06020000
FWDB_MAGIC = 0xF12DBA5E

def NIB_CHECK(n): return (0xFF & ~n<<4 | n)
IMAGE_LEFT	= NIB_CHECK(1)
IMAGE_RIGHT	= NIB_CHECK(2)
IMAGE_NONE	= NIB_CHECK(3)
IMAGE_MFG	= NIB_CHECK(4)

choices = {	IMAGE_LEFT : "Left",
			IMAGE_RIGHT: "Right",
			IMAGE_NONE : "None",
			IMAGE_MFG  : "Mfg"}

NO_CARD, IO_CARD, SWB_CARD = 0, 1, 2

slottypes = {	NO_CARD: '--',
				IO_CARD: 'IO card',
				SWB_CARD: 'SWB card'}

'''
typedef struct {
	uchar Major;	// year
	uchar Minor;	// month
	unsigned short build;	// day,hour,minute
} majorMinorBuild;

typedef union {
	majorMinorBuild mmb;
	unsigned long version;
} versionNumber;

typedef struct { // package versions set by upgrader
	versionNumber package;
	versionNumber launcher;
	versionNumber mainapp;
	versionNumber uboot;
	versionNumber linux;
	versionNumber displayapp;
	versionNumber ioapp;
	versionNumber swbapp;
} PackageInfo;

typedef struct { // version numbers for all the firmware in the box and which to run
	// set at initialization
	ulong	magic;
	// set by boot and launcher and display
	uchar			runningChoice; // actual set by boot
	uchar			pendingChoice; // preference set by launcher or display
	ushort	size;
	ulong	checkSum; // updated with content updates - start after checksum

	// set by upgrader
	PackageInfo		packageLeft;
	PackageInfo		packageRight;

	// set at initialization and recovery
	versionNumber	mainboot;
	// set by launcher
	ulong			slotaType
	versionNumber	slotaBoot;
	versionNumber	slotaApp;
	versionNumber	slotaHiboot;
	// set by launcher
	ulong			slotbType
	versionNumber	slotbBoot;
	versionNumber	slotbApp;
	versionNumber	slotbHiboot;
	// set by upgrader?
	versionNumber	database;
} firmwareDatabase;
'''

class firmwareDatabase(QObject):
	fdbupdate = Signal()

	fdbFrontStruct = "LBBHL"
	piStruct = "LLLLLLLL"
	fdbBackStruct = "LLLLLLLLLL"
	fdbStruct = fdbFrontStruct + piStruct + piStruct + fdbBackStruct

	fdbAddress = FERAM_BASE_ADDRESS	# memory cast as database
	fdbSize = struct.calcsize('='+fdbStruct)

	piOffset = struct.calcsize('='+fdbFrontStruct)
	piSize = struct.calcsize('='+piStruct)
	
	fdbFront = fdbAddress
	fdbFrontSize = piOffset
	piLeft = fdbAddress + piOffset
	piRight = piLeft + piSize
	fdbBack = piRight + piSize
	fdbBackSize = struct.calcsize('='+fdbBackStruct)
	fwdbSize = fdbFrontSize + 2*piSize + fdbBackSize

	def __init__(self, parent):
		QObject.__init__(self, parent)
		self.parent = parent

		self.magic = 0
		self.checksum = 0
		self.size = 0

		self.running = 0
		self.pending = 0

		self.packageLeft = 0
		self.launcherLeft = 0
		self.mainappLeft = 0
		self.ubootLeft = 0
		self.linuxLeft = 0
		self.displayappLeft = 0
		self.ioappLeft = 0
		self.swbappLeft = 0

		self.packageRight = 0
		self.launcherRight = 0
		self.mainappRight = 0
		self.ubootRight = 0
		self.linuxRight = 0
		self.displayappRight = 0
		self.ioappRight = 0
		self.swbappRight = 0
		
		self.mainboot = 0
		
		self.slotaType = 0
		self.slotaBoot = 0
		self.slotaApp = 0
		self.slotaHiboot = 0
		
		self.slotbType = 0
		self.slotbBoot = 0
		self.slotbApp = 0
		self.slotbHiboot = 0
		
		self.database = 0
		
		self.fwdb = [0]*self.fwdbSize

# services
	def readFirmwareDatabase(self):
		if printme: print >>sys.stderr, 'readFirmwareDatabase'
		try:
			self.parent.protocol.packetSource(pids.MEM_DATA, self.fdbReturned)
			who = [MAIN_CPU, self.parent.whofrom]
			payload1 = longList(self.fdbFront) + [self.fdbFrontSize]
			payload2 = longList(self.piLeft) + [self.piSize]
			payload3 = longList(self.piRight) + [self.piSize]
			payload4 = longList(self.fdbBack) + [self.fdbBackSize]
			self.parent.protocol.sendNPS(pids.MEM_READ, who + payload1)
			self.parent.protocol.sendNPS(pids.MEM_READ, who + payload2)
			self.parent.protocol.sendNPS(pids.MEM_READ, who + payload3)
			self.parent.protocol.sendNPS(pids.MEM_READ, who + payload4)
		except Exception, e:
			print >>sys.stderr, e
			traceback.print_exc(file=sys.stderr)

	def rebuildDatabase(self):
		if printme: print >>sys.stderr, 'rebuildDatabase'
		who = [MAIN_CPU, MAIN_CPU]
		self.parent.protocol.sendNPS(pids.FIRMWARE, who + [FWDB_REBUILD])

	def fdbReturned(self, packet):
		if printme: print >>sys.stderr, 'fdbReturned'
		try:
			memdata = "BBLB"
			address = cast(memdata, packet)[2]
			content = packet[struct.calcsize('='+memdata):]
			if printme: print >>sys.stderr, 'address: %X'%address

			if address == self.fdbFront:
				self.fwdb[:self.fdbFrontSize] = content
				self.magic = cast(self.fdbFrontStruct, content)[0]
				self.running = cast(self.fdbFrontStruct, content)[1]
				self.pending = cast(self.fdbFrontStruct, content)[2]
				self.size = cast(self.fdbFrontStruct, content)[3]
				self.checksum = cast(self.fdbFrontStruct, content)[4]

			elif address == self.piLeft:
				self.fwdb[self.piOffset:self.piOffset+self.piSize] = content
				self.packageLeft = cast(self.piStruct, content)[0]
				self.launcherLeft = cast(self.piStruct, content)[1]
				self.mainappLeft = cast(self.piStruct, content)[2]
				self.ubootLeft = cast(self.piStruct, content)[3]
				self.linuxLeft = cast(self.piStruct, content)[4]
				self.displayappLeft = cast(self.piStruct, content)[5]
				self.ioappLeft = cast(self.piStruct, content)[6]
				self.swbappLeft = cast(self.piStruct, content)[7]

			elif address == self.piRight:
				self.fwdb[self.piOffset+self.piSize:self.piOffset+2*self.piSize] = content
				self.packageRight = cast(self.piStruct, content)[0]
				self.launcherRight = cast(self.piStruct, content)[1]
				self.mainappRight = cast(self.piStruct, content)[2]
				self.ubootRight = cast(self.piStruct, content)[3]
				self.linuxRight = cast(self.piStruct, content)[4]
				self.displayappRight = cast(self.piStruct, content)[5]
				self.ioappRight = cast(self.piStruct, content)[6]
				self.swbappRight = cast(self.piStruct, content)[7]

			elif address == self.fdbBack:
				self.fwdb[self.piOffset+2*self.piSize:] = content
				self.mainboot = cast(self.fdbBackStruct, content)[0]
		
				self.slotaType = cast(self.fdbBackStruct, content)[1]
				self.slotaBoot = cast(self.fdbBackStruct, content)[2]
				self.slotaApp = cast(self.fdbBackStruct, content)[3]
				self.slotaHiboot = cast(self.fdbBackStruct, content)[4]
		
				self.slotbType = cast(self.fdbBackStruct, content)[5]
				self.slotbBoot = cast(self.fdbBackStruct, content)[6]
				self.slotbApp = cast(self.fdbBackStruct, content)[7]
				self.slotbHiboot = cast(self.fdbBackStruct, content)[8]
		
				self.database = cast(self.fdbBackStruct, content)[9]

			else:
				error("memory read got an unexpected address %X"%address)
				return
			
			if len(self.fwdb) != self.fwdbSize:
				print >>sys.stderr, 'fw db is wrong size. is: %d should be: %d'%(len(self.fwdb), self.fwdbSize)

			self.fdbupdate.emit()
		except Exception, e:
			print >>sys.stderr, e
			traceback.print_exc(file=sys.stderr)

	def runningChoice(self):
		return choices.get(self.running, 'Invalid')

	def pendingChoice(self):
		return choices.get(self.pending, 'Invalid')

	def magicStatus(self):
		if self.magic == FWDB_MAGIC:
			return 'Ok'
		return 'Fail'

	def checksumStatus(self):
		checksum = fletcher32(self.fwdb[self.piOffset:], self.fwdbSize-self.fdbFrontSize)
		if self.checksum == checksum:
			return 'Ok'
		if printme: print >>sys.stderr, 'Failed checksum. read: %X  calc: %x'%(self.checksum, checksum)
		return 'Fail'

	def version(self, mmb):
		BAD_HEAD = 0xBADD4EAD # from launcher.h for invalid header
		if mmb == BAD_HEAD:
			return "no image"
		if mmb == 0:
			return "?"
		major = mmb>>24
		minor = mmb>>16&0xFF
		build = mmb&0xFFFF
		if major in range(13,99) and minor in range(1,13) and build <= 24*60*30:
			return "%d.%d.%X"%(major, minor, build)
		return "invalid"
	
	def slotType(self, t):
		return slottypes.get(t, 'unknown')
