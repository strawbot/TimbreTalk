#!/usr/bin/env python

import sys, traceback	
from socket import *
import struct

class serialSocket:
	def __init__(self, name):
		self.name = name
		self.sock = socket(AF_UNIX, SOCK_DGRAM)
#		self.sock = socket(AF_UNIX, SOCK_STREAM)
		l_onoff = 1                                                                                                                                                           
		l_linger = 1                                                                                                                                                          
		self.sock.setsockopt(SOL_SOCKET, SO_LINGER,                                                                                                                     
                 struct.pack('ii', l_onoff, l_linger))
		self.sock.setsockopt(SOL_SOCKET, SO_REUSEADDR,
			self.sock.getsockopt(SOL_SOCKET, SO_REUSEADDR) | 1) # limit socket unavailability

	def connectWait(self):
		try:
			self.sock.bind(self.name)
			self.sock.listen(1)
			self.connection, address = self.sock.accept()
		except Exception, e:
			print e
			traceback.print_exc(file=sys.stderr)
			self.close()
			raise

	def connect(self):
		self.sock.connect(self.name)
	
	def send(self, data):
		self.sock.sendall(data)
	
	def receive(self, length=1024):
		data = self.connection.recv(length)
		return data

	def close(self):
		self.sock.close()


'''
# socket example
# Q? can a socket to both receive and transmit simultaneously with two threads?
# end 1: s.accept() blocks until s.connect()
from socket import *

s = socket(AF_UNIX, SOCK_STREAM)

# wait for connection
s.bind('sfp')
s.listen(1)
c, a = s.accept()

# test
c.recv(1024)
s.sendall('hello moon')

# close both
s.close()


# end 2
from socket import *

s = socket(AF_UNIX, SOCK_STREAM)

# initiate connection
s.connect('sfp')

# test
s.sendall('Hello, world')
s.recv(1024)

# close both
s.close()
'''

