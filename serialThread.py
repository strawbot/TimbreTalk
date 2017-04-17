# serial port thread  Robert Chapman  Apr 17, 2017

# create a serial port object which can be opened to a serial port
# a default rate can be set
# port can be opened and closed

from threading import Thread
from serialPort import serialPort

class serialThread(serialPort, Thread):

	def __init__(self, *args, **kwargs):
		serialPort.__init__(self, *args, **kwargs)

	# overlords
	def openedPort(self):
		self.start()  # run serial in thread

	def close(self):
		self.closePort()
		self.join(1.000)
