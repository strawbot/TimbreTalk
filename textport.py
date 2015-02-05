# textport  Robert Chapman III  Sep 28, 2012

# imports
import pids

class textport():
	def __init__(self, parent=None, source=None):
		if source:
			self.source = source
		else:
			self.source = self.sink
		self.echo = False
		self.crNew = '\x0d'
		self.lfNew = ''
		self.linebuffer = []

	def newCrLf(self, s):
		t = s
		s = ''
		for c in t:
			if c == '\x0a':
				c = self.lfNew
			elif c == '\x0d':
				c = self.crNew
			s += c
		return s

	# input selection
	def multipleKeys(self):
		self.single = False

	def singleKey(self):
		self.single = True

	def buffered(self, event):
		self.multipleKeys()

	def rawMinusEcho(self, event):
		self.echo = False
		self.singleKey()

	def rawPlusEcho(self, event):
		self.echo = True
		self.singleKey()

	def keyin(self, key): # input is a qstring
		character = str(key)[0]

		if self.source:
			character = self.newCrLf(character)
			if not character: return
			
			# detect and change delete key to backspace
			if  character == chr(0x7F):
				character = chr(0x8)

			if self.single:
				self.source(character)
				if self.linebuffer:
					del self.linebuffer[:]
				if self.echo:
					self.write(character)
			else:
				if character == '\x0d' or character == '\x0a':
					self.write('\x0a')
					self.source(''.join(self.linebuffer[:]))
					del self.linebuffer[:]
				elif character == chr(8):
					if self.linebuffer:
						self.linebuffer.pop()
						self.write(character)
				else:
					self.linebuffer.append(character)
					self.write(character)

	def write(self, s, style=''):
		if style:
			s = '\n'+s
		self.sink(s)

	def sink(self, s):
		if s:
			if type(s[0]) == type(0):
				s = ''.join(map(chr, s))
			for c in s:
				if ord(c) == 8:
					self.backSpace()
				else:
					self.text(c)
			self.textdone()

	def backSpace(self):
		print chr(0x8),
		
	def text(self, c):
		print c,

	def textdone(self):
		pass
