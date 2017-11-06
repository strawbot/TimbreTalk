# serial port object  Rob Chapman  Jan 26, 2011

# create a serial port object which can be opened to a serial port
# input and output are done through signals and slots
# a default rate can be set
# port can be opened and closed

from pyqtapi2 import *
import sys, traceback, serial, time
from message import warning, error, note, message
from signalcatch import initSignalCatcher

class serialPort(QThread):
	# define signals
	source = pyqtSignal(object)
	ioError = pyqtSignal(object)
	ioException = pyqtSignal(object)
	closed = pyqtSignal()
	opened = pyqtSignal()
	stopbits = serial.STOPBITS_ONE
	noparity, evenparity, oddparity = serial.PARITY_NONE, serial.PARITY_EVEN, serial.PARITY_ODD
	parity = noparity
	bytesize = serial.EIGHTBITS

	def __init__(self, rate=9600):
		QThread.__init__(self) # needed for signals to work!!
		self.port = None
		self.rate = self.default = rate
		self.inputs = 0
		self.outputs = 0
		
#		initSignalCatcher()

	# shutdown signal
	def shutdown(self):
#		note('shutting down serial port\n\r')
		self.closePort()
		self.quit()

	def run(self): # perhaps open read and close are all in this thread
		while self.port:
			try:
				c = self.port.read(1) # figure out why it doesn't block!!!
				c += self.port.read(self.port.inWaiting()) # get rest of chars
				self.inputs += len(c)
				if c:
					self.source.emit(c)
			except IOError:
				self.closePort()
				note('Alert: device removed while open ')
			except Exception, e:
				self.closePort()
				#error("run - serial port exception: %s" % e)
		self.closed.emit()

	def open(self, prefix, port, rate=None):
		if self.isOpen():
			error("Already opened!")
		else:
			if rate == None:
				self.rate = self.default
			else:
				self.rate = rate
			self.prefix = prefix
			self.name = port
			portname = prefix+port
			try:
				self.port = serial.Serial(portname,
										  self.rate,
										  timeout=.01, # time to accumulate characters: 10 ms @ 115200, thats up to 115.2 chars
										  parity=self.parity,
										  stopbits=self.stopbits,
										  xonxoff=0,
										  rtscts=0, # hw flow control
										  bytesize=self.bytesize)
				note('opened %s at %d' % (port, self.rate))
				self.start() # run serial in thread
				self.opened.emit()
			except Exception, e:
				if self.port:
					self.port.close()
				self.port = None
#				error('open port failed for '+prefix+port)
				raise Exception('open port failed for '+prefix+port)

	def closePort(self):
		if self.isOpen():
			port = self.port
			self.port = None
			try:
				port.flush()
				port.close()
			except:
				pass
			note('closed %s'%self.name)
		else:
			self.port = None

	def close(self):
		self.ioError.disconnect()
		self.ioException.disconnect()
		self.closed.disconnect()
		self.source.disconnect()
		self.closePort()
		self.wait(1000)

	def sink(self, s):
		if self.isOpen():
			try:
				self.port.write(s)
				self.outputs += len(s)
			except IOError:
				self.ioError.emit('Alert: device closed while writing ')
			except Exception, e:
				if self.port:
					self.ioException.emit("Error: sink - serial port exception: %s" % e)

	def setRate(self, rate):
		if self.rate != rate:
			note('Baudrate changed to %d'%rate)
			self.rate = rate
		if self.isOpen():
			self.port.baudrate = rate

	def isOpen(self):
		if self.port:
			return self.port.isOpen()
		return False
