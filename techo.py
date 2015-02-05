import Queue, threading, sockets

class test():
	name = 'echo'
	def __init__:
		
		# client tester
		def tester():
			strings = ['a', 'b', 'c','d']
			self.tsock = socket(AF_UNIX, SOCK_STREAM)
			self.tsock.connect(self.name)
			for s in strings:
				self.tsock.sendall(s)
			
		
		def printer():
			self.rsock = serialSocket(self.name)
			self.rsock.connectWait()
			while 1:
				print 'new:',self.rsock.recv(1024)
		
		t = threading.Thread(target=printer)
		t.setDaemon(True)
		t.start()
			
		threading.Thread(target=tester).start()
