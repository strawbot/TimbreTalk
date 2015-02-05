# for intercepting reads and write on a serial port  Robert Chapman III  Jun 10, 2013

outfile = ""

def tohex(string):
	string = map(ord, string)
	string = ' '.join(map (lambda i:hex(i)[2:].upper().zfill(2), string))
	return string

def appendwrite(string):
	global outfile
	if outfile:
		s = 'tx:'+tohex(string)+'\n'
		open(outfile, 'a').write(s)

def appendread(string):
	global outfile
	if outfile:
		s = 'rx:'+tohex(string)+'\n'
		open(outfile, 'a').write(s)

def appendline(string):
	global outfile
	if outfile:
		string = string.strip()
		s = 'rl:'+string+'\n'
		open(outfile, 'a').write(s)

'''
import serial

class Serialx(serial.Serial):
	def writex(self, string):
		super(Serial, self).write(string)
		s = 'tx:'+tohex(string)+'\n'
		self.output.write(s)

	def readx(self, length):
		string = super(Serial, self).read(length)
		s = 'rx:'+tohex(string)+'\n'
		self.output.write(s)
		return string

	def readlinex(self):
		string = super(Serial, self).readline()
		s = 'rl:'+tohex(string)+'\n'
		self.output.write(s)
		return string

	def openx(self):
		super(Serial, self).open()
		print 'open port?',self.isOpen()
		self.output = open(outfile, 'w')
	
	def closex(self):
		super(Serial, self).close()
		print 'close port?',not self.isOpen()
		self.output.close()
'''