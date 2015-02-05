import Queue, threading, sockets

class talker():
	name = 'echo1'
	def __init__(self):
		# client tester
		strings = ['a', 'b', 'c','d']
		self.tsock = sockets.serialSocket(self.name)
		self.tsock.connect()
		for s in strings:
			self.tsock.sendall(s)
		self.tsock.close()

talker()


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

