# LED for GUI objects  Robert Chapman  Dec 7, 2012

# blinkOn/blinkOff colors; default green/grey
# blink period in ms, on interval as percent
# green, amber, red, blue, grey, white

from pyqtapi2 import *

white = "border:none;background-color:white"
blue = "border:none;background-color:blue"
green = "border:none;background-color:green"
amber = "border:none;background-color:rgb(255, 204, 102)"
red = "border:none;background-color:red"
grey = "border:none;background-color:rgb(0, 0, 0,25)"

class LED(QObject):
	INIT,ON,OFF,BLINK,ERROR = range(5)
	def __init__(self, guiObject):
		QObject.__init__(self) # needed for signals to work!!
		self.led = guiObject
		self.timer = QTimer()
		self.onColor = green
		self.offColor = grey
		self.errorColor = red
		self.blinkOn = green
		self.blinkOff = grey
		self.blinkPeriod = 250
		self.onTime = 50
		self.onoff = 0
		self.timer.timeout.connect(self.blinker)
	
	def on(self):
#		print 'led on'
		self.timer.stop()
		self.led.setStyleSheet(self.onColor)
	
	def off(self):
#		print 'led off'
		self.timer.stop()
		self.led.setStyleSheet(self.offColor)
			
	def blink(self):
#		print 'led blink'
		self.timer.setInterval(self.blinkPeriod)
		self.timer.start()
		
	def blinker(self):
#		print ' blinker '
		if self.onoff:
			self.onoff = 0
			self.led.setStyleSheet(self.blinkOff)
		else:
			self.onoff = 1
			self.led.setStyleSheet(self.blinkOn)

	def error(self):
#		print 'led error'
		self.off()
		self.led.setStyleSheet(self.errorColor)
