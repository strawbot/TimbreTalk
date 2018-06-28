# messages  Rob Chapman  Jan 30, 2011

import Queue, time
maxMessages = 1000 # maximum queue size before blocking input

def defaultWrite(string, style=''): # default output is to std out
	import sys
	print(string)

textout = defaultWrite

def messageQueue(): # output to message queue for isolation
	global textout
	messageq = Queue.Queue(maxMessages)
	def writeq(string, style=''):
		messageq.put((string, style))
	textout = writeq
	return messageq

def setTextOutput(f): # output can be redirected to a different place
	textout = f

# messages
def note(string):
	textout('\n'+string, style='note')

def warning(string): # mark a message for formatting
	textout('\n'+string, style='warning')

def error(string):
	textout('\n'+string, style='error')

def message(string, style=''): # mark a message for formatting
#	string = ''.join(x+hex(x) for x in string)
	textout(string, style)

def write(text): # route the message to file or window
	message(text)
	
def messageDump(who,s=[], text=0): # dump message in hex or text to terminal
	# s could be a string, character or integer
	framedump = ''
	if s:
		# note(type(s))
		if type(s) == type(0):
			s = [s]
		elif type(s[0]) == type('a'):
			if type(s) == type([]):
				s = map(ord, s[0])
			else:
				s = map(ord, s)
		if text:
			framedump = ''.join(map(lambda i: chr(i) if i >= ord(' ') and i <= ord('~')  else ' ', s))
		else:
			framedump = ' '.join(map (lambda i:hex(i)[2:].upper().zfill(2), s))
	note(who + framedump)

class stdMessage(object): # for redirecting standard out
	@classmethod
	def write(cls, string):
		textout(string)
