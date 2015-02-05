import Queue, threading, sockets

class echoServer(sockets.serialSocket):
	name = 'echo'
	def __init__(self):
		sockets.serialSocket.__init__(self, self.name)

		# echo server
		def qrx(q):
			while 1:
				q.put(self.receive)
		
		def qtx(q):
			while 1:
				self.send(q.get())

		def echoer():
			self.connectWait()
	
			q = Queue.Queue()
	
			t = threading.Thread(target=qtx, args=(q,))
			t.daemon(True)
			t.start()
	
			t = threading.Thread(target=qrx, args=(q,))
			t.daemon(True)
			t.start()

		threading.Thread(target=echoer).start()

echoServer()


