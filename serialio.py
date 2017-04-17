# serial port thread  Robert Chapman  Apr 17, 2017

# create a serial port object which can be opened to a serial port
# input and output are done through signals and slots
# a default rate can be set
# port can be opened and closed

from pyqtapi2 import *
import message
from serialPort import serialPort

class serialThread(serialPort, QThread):
	# define signals
	source = pyqtSignal(object)
	ioError = pyqtSignal(object)
	ioException = pyqtSignal(object)
	closed = pyqtSignal()
	opened = pyqtSignal()

	def __init__(self, *args, **kwargs):
		serialPort.__init__(self, *args, **kwargs)
		QThread.__init__(self) # needed for signals to work!!

	# overlords
	def openedPort(self):
		self.start()  # run serial in thread
		self.opened.emit()

	def rxBytes(self, bytes):
		self.source.emit(bytes)

	def sink(self, bytes):
		self.txBytes(bytes)

	def note(self, s):
		message.note(s)

	def error(self, s):
		message.error(s)

	def ioErrorCall(self, s):
		self.ioError.emit(s)

	def ioExceptionCall(self, s):
		raise Exception(s)

	def closedPort(self):
		self.closed.emit()

	def close(self):
		self.ioError.disconnect()
		self.ioException.disconnect()
		self.closed.disconnect()
		self.source.disconnect()
		self.closePort()
		self.wait(1000)

