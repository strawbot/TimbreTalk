 # S-Record parser  Rob Chapman  Jan 27, 2011

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
	[-2:] checksum

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

from message import *

class Srecord():
	import sys

	MAX_IMAGE_SIZE = 1024 * 1024 # 1MB
	HOLE_FILL = 0xFF
	records = []
	check = 0

	def __init__(self, file):
		del self.records[:]
		self.records = []
		self.start = 0xFFFFFFFF
		self.end = 0
		self.size = 0
		self.entry = -1
		self.text = ''
		self.addSrecord(file)

	def createImage(self): # direct memory image from hex strings with holes as 0xFF
		if self.size > self.MAX_IMAGE_SIZE:
			error('image is too large! %d'%self.size)
			image = [0]
		else:
			image = [self.HOLE_FILL]*self.size
			for record in self.records:
				a = record[0] - self.start
				data = record[1]
				for i in range(0,len(data),2):
					if image[a+i/2] != 0xFF:
						warning('\nsrecord.createImage: Overwrite data at %x'%(self.start + a + i/2))
					image[a+i/2] = int(data[i:i+2], 16)
		return image
	
	def sRecordImage(self): # return built image, checksum
		from checksum import fletcher32
		image = self.createImage()
		check = fletcher32(image, len(image))
		return image, check
	
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
							for i in range(0,len(data),2):
								n = int(data[i:i+2], 16)
								if n:
									self.text += chr(n)
						elif   s == '5':
							pass
						elif s == '7':
							self.entry = int(line[4:12], 16)
						elif s == '8':
							self.entry = int(line[4:10], 16)
						elif s == '9':
							self.entry = int(line[4:8], 16)
						else:
							#error('Unknown s record:%s'%line)
							raise Exception('Unknown s record:%s'%line)
						continue
					self.records.append((address,data))
					self.start = min(self.start, address)
					self.end = max(self.end, address+len(data)/2)
		except:
			error('Error parsing s-record file! Unknown format')
		if self.start == 0xffffffff:
			self.start = 0
		self.size = self.end - self.start
'''
	def genSrecord(self, file, length=80, address=-1):
		out = open(file, 'w')
		if address == -1:
			address = self.start
		image = self.createImage()
		start = 0
		end = len(image)
		while start < end:
			l = end - start
			if l > length:
				l = length
			
'''			
		
# test
if __name__ == '__main__':
	import sys
	import time
	s = time.time()
	srec = Srecord('debug/test.S19')
	image,check = srec.sRecordImage()
	if srec.text:
		print >>sys.stderr, 'Title:'+srec.text
	print >>sys.stderr, 'start=0x%X  end=0x%X  size=%i  entry=0x%X'%(srec.start,srec.end,srec.size,srec.entry)
	print >>sys.stderr, 'number of lines: %i'%len(srec.records)
	print >>sys.stderr, 'image checksum: 0x%X'%check
	e = time.time()
	print >>sys.stderr, 'elapsed time: %.3f seconds'%(e-s)