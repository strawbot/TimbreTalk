import sockets
import sys, traceback	

class listener(sockets.serialSocket):
	name = 'echo11'
	def __init__(self):
		sockets.serialSocket.__init__(self, self.name)
		self.connectWait()
		while 1:
			x = self.receive()
			if x: print x

listener()



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

