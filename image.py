# build image from intel hex or motorola Srecord file  Robert Chapman III  May 7, 2015

from pyqtapi2 import *

import sys, traceback
from message import *
from checksum import fletcher32
import os
from ctypes import *

printme = 0

class imageRecord(QObject):
	MAX_IMAGE_SIZE = 1024 * 1024 * 2 # 2MB
	HOLE_FILL = 0xFF
	setSize = Signal(object)
	setName = Signal(object)
	setStart = Signal(object)
	imageLoaded = Signal()

	def __init__(self, parent):
		QObject.__init__(self) # needed for signals to work!!
		self.parent = parent
		self.records = []
		self.image = []
		self.file = ''
		self.dir = ''
		self.name = ''
		self.timestamp = 0
		self.size = 0
		self.checksum = 0
		self.ext = ''

	def createImage(self, file):
		if file:
			if printme: print("Creating Image for: "+file)
			self.file = file
			x = self.file.rsplit('/', 1)
			if len(x) > 1:
				self.dir, self.name = x
			else:
				self.name = x[0]

			self.ext = self.name.rsplit('.', 1)[-1]
			self.addRecord()
			self.imageLoaded.emit()

	def selectFile(self, file):
		if not file: return
		try:
			self.createImage(file)
			self.setName.emit(self.name)
			self.setSize.emit(str(self.size))
			self.setStart.emit(hex(self.start))
		except Exception, e:
			print >>sys.stderr, e
			traceback.print_exc(file=sys.stderr)
	
	def checkUpdates(self):
		if self.timestamp != os.path.getmtime(self.file):
			warning(' disk image is newer - reloading ')
			self.selectFile(self.file)
			return True
		return False

	def addRecord(self): # turn file into list of address,data tuples
		self.timestamp = os.path.getmtime(self.file) # remember for checking later
		self.start = 0xFFFFFFFF
		self.end = self.entry = self.size = 0
		del self.records[:]

		if self.ext in ['jbc', 'jam', 'txt', 'text']:
			self.emptyImage()
			self.image.extend(map(ord, open(self.file,'rb').read()))
			self.end = self.size = len(self.image)
		else:
			if self.ext in ['srec', 'S19']: self.addSrecord()
			elif self.ext in ['hex']: self.addHexRecord()
			elif self.ext in ['elf']: self.addElfRecord()
			else:
				error('Unknown format. File suffix not any of: .hex, .srec, .S19, .elf, .jbc, .jam, .txt, .text: %s'%self.name)
				self.start = 0
				return
			self.makeImage()
		if self.start == 0xFFFFFFFF:
			self.start = 0
		self.checksum = fletcher32(self.image, len(self.image))

	def emptyImage(self):
		del self.image[:]
		
	def makeImage(self): # direct memory image from hex strings with holes as 0xFF
		self.emptyImage()
		self.size = self.end - self.start
		self.size = (self.size + 3) & ~3  # round up to multiple of 4
		if self.size > self.MAX_IMAGE_SIZE:
			error('Image is too large! %d'%self.size)
		else:
			self.image = [self.HOLE_FILL]*self.size
			if printme: print("Size: %d"%self.size)
			for record in self.records:
				a = record[0] - self.start
				data = record[1]
				if printme: print(" a = %x  data = %s "%(a,data[0:20]))
				for i in range(0,len(data),2):
					if self.image[a+i/2] != 0xFF:
						warning('\nimageRecord.makeImage: Overwrite data at %x'%(self.start + a + i/2))
					self.image[a+i/2] = int(data[i:i+2], 16)
	
	'''
	Intel Hex format from Wikipedia:
	 Summarized:
	  [0] :
	  [1:2] byte count
	  [3:6] address
	  [7:8] type: 00 data; 01 end; 02 ext seg; 03 seg start; 04 ext addr; 05 lin start
	  [9:-2] data
	  [-2:] checksum: 2's complement of sump of all preceding bytes; ignored
	'''
	def addHexRecord(self):
		try:
			base = 0
			for line in open(self.file, 'r').readlines():
				line = line.strip()
				if line:
					if line[0] == ':':
						count = int(line[1:3], 16)
						address = int(line[3:7], 16) + base
						type = int(line[7:9])
						data = line[9:-2]
						checksum = line[-2:]
						if type == 0:
							self.records.append((address,data))
							self.start = min(self.start, address)
							self.end = max(self.end, address + len(data)/2)
						elif type == 1:
							pass # end of file
						elif type == 2:
							base = int(data, 16) * 16
						elif type == 4:
							base = int(data, 16) << 16
						elif type == 3 or type == 5:
							self.entry = int(data, 16)
						else:
							raise Exception('Unknown hex record:%s'%line)
			if printme: print("Start: %X  End: %X"%(self.start, self.end))
		except:
			error('Error parsing hex-record file! Unknown format')

	''' S-Record file description from Wikipedia:
	Components
	   1. Start code, one character, an S.
	   2. Record type, one digit, 0 to 9, defining the type of the data field.
	   3. Byte count, two hex digits, indicating the number of bytes (hex digit pairs)
		  that follow in the rest of the record (in the address, data and checksum fields).
	   4. Address, four, six, or eight hex digits as determined by the record type for the
		  memory location of the first data byte. The address bytes are arranged in big
		  endian format.
	   5. Data, a sequence of 2n hex digits, for n bytes of the data.
	   6. Checksum, two hex digits - the least significant byte of ones' complement of the
		  sum of the values represented by the two hex digit pairs for the byte count,
		  address and data fields.

	Summarily:
		[0] S
		[1] type
		[2:4] count
		[4:8,10,12] address
		[:-2] data
		[-2:] checksum; ignored

	There are eight record types, listed below:
	Record 	Description 	Address Bytes 	Data Sequence
		S0 	Block header 		2 			Yes
		S1 	Data sequence 		2 			Yes
		S2 	Data sequence 		3 			Yes
		S3 	Data sequence 		4 			Yes
		S5 	Record count 		2 			No
		S7 	End of block 		4 			No
		S8 	End of block 		3 			No
		S9 	End of block 		2		 	No

	S0
	The S0 record data sequence contains vendor specific data rather than
	program data. String with file name and possibly version info.

	S1, S2, S3
	Data sequence, depending on size of address needed. A 16-bit/64K system
	uses S1, 24-bit address uses S2 and full 32-bit uses S3.

	S5
	The record count in the S5 record is stored in the 2-byte address field.

	S7, S8, S9
	The address field of the S7, S8, or S9 records may contain a starting
	address for the program.
	'''
	def addSrecord(self):
		try:
			for line in open(self.file, 'r').readlines():
				line = line.strip()
				if not line:
					continue
				if line[0] == 'S':
					s = line[1]
					count = line[2:4]
					checksum = line[-2:]
					if   s == '1':
						address = int(line[4:8], 16)
						data = line[8:-2]
					elif s == '2':
						address = int(line[4:10], 16)
						data = line[10:-2]
					elif s == '3':
						address = int(line[4:12], 16)
						data = line[12:-2]
					else:
						if   s == '0':
							data = line[8:-2]
						elif   s == '5':
							pass
						elif s == '7':
							self.entry = int(line[4:12], 16)
						elif s == '8':
							self.entry = int(line[4:10], 16)
						elif s == '9':
							self.entry = int(line[4:8], 16)
						else:
							raise Exception('Unknown s record:%s'%line)
						continue
					self.records.append((address,data))
					self.start = min(self.start, address)
					self.end = max(self.end, address+len(data)/2)
		except:
			error('Error parsing s-record file! Unknown format')

	''' ELF file format: ELF file main Header format:
		Byte	ident[16]; 0x7f 3 chars; class; encoding; version; 
		Short	type
		Short	machine
		Long 	version
		Long	entry // longlong for 64-bit
		Long	phoff // longlong for 64-bit
		Long	shoff // longlong for 64-bit
		Long	flags
		Short	ehsize
		Short	phentsize
		Short	phnum
		Short	shentsize
		Short	shnum
		Short	shstrndx
	Program headers start at phoff and there are phnum of them. They contain
	information about the parts to build the image.
	'''
	def addElfRecord(self):
		from elfdump import *
		
		if printme: print("adding elf record")

		# determine endian
		file = open(self.file, 'rb')
		file.seek(EI_DATA)
		if ord(file.read(1)) == ELFDATA2MSB:
			endian = BigEndianStructure
		else:
			endian = LittleEndianStructure

		# elf header
		elf = elfHeader(endian)
		file.seek(EI_MAG0)
		file.readinto(elf)
	
		if elf.ident[EI_MAG0:EI_CLASS] != map(ord, [ELFMAG0, ELFMAG1, ELFMAG2, ELFMAG3]):
			error('Not an elf file')
			return

		if elf.type != ET_EXEC:
			error('Not an executable file')
			return

		self.entry = int(elf.entry)

		# program headers
		ph = programHeader(endian)
	
		for i in range(elf.phnum):
			file.seek(elf.phoff + i * sizeof(ph))
			file.readinto(ph)
			# image
			if ph.p_filesz:
				address = int(ph.p_paddr)
				file.seek(ph.p_offset)
				data = file.read(ph.p_filesz).encode("hex")
				self.records.append((address,data))
				self.start = min(self.start, address)
				self.end = max(self.end, address+len(data)/2)
				if printme: print("address: %x  start: %x  end: %x"%(address, self.start, self.end))
				
		file.close()

# unit test code: convert srec and hex file to images and compare checksums