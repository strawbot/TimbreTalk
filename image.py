# build image from intel hex or motorola Srecord file  Robert Chapman III  May 7, 2015

from message import *
from checksum import fletcher32

class imageRecord():
	MAX_IMAGE_SIZE = 1024 * 1024 * 2 # 2MB
	HOLE_FILL = 0xFF
	records = []

	def __init__(self, file):
		del self.records[:]
		self.records = []
		self.image = []
		self.addRecord(file)
		self.createImage()

	def addRecord(self, file): # turn file into list of address,data tuples
		self.start = 0xFFFFFFFF
		self.end = self.entry = 0
		del self.records[:]
		self.name = file.rsplit('/', 1)[-1]
		type = self.name.rsplit('.', 1)[-1]
		if type in ['srec', 'S19']:
			self.addSrecord(file)
		elif type in ['hex']:
			self.addHexRecord(file)
		else:
			error('Unknown format. File suffix not .hex, .srec nor .S19: %s'%self.name)
		if self.start == 0xFFFFFFFF:
			self.start = 0
		self.size = self.end - self.start

	def createImage(self): # direct memory image from hex strings with holes as 0xFF
		del self.image[:]
		if self.size > self.MAX_IMAGE_SIZE:
			error('Image is too large! %d'%self.size)
		else:
			self.image = [self.HOLE_FILL]*self.size
			for record in self.records:
				a = record[0] - self.start
				data = record[1]
				for i in range(0,len(data),2):
					if self.image[a+i/2] != 0xFF:
						warning('\nimageRecord.createImage: Overwrite data at %x'%(self.start + a + i/2))
					self.image[a+i/2] = int(data[i:i+2], 16)
		return self.image
	
	def recordImage(self): # return built image, checksum
		check = fletcher32(self.image, len(self.image))
		return self.image, check
	
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
	def addHexRecord(self, file):
		try:
			base = 0
			for line in open(file, 'r').readlines():
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
	def addSrecord(self,file):
		try:
			for line in open(file, 'r').readlines():
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

# unit test code: convert srec and hex file to images and compare checksums