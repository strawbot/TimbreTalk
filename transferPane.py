# panel for srecords  Robert Chapman III  Dec 5, 2012

from pyqtapi2 import *
from message import *
import pids
from endian import *
from srecordTransfer import sRecordTransfer, ubootTransfer
from recover import recover
import led
from cpuids import *
from targets import *
import sys, traceback

printme = 0
SEND,TRANSFER,VERIFY = range(3)

class srecordPane(QWidget):
	def __init__(self, parent):
		if printme: print('__init__')
		QWidget.__init__(self, parent)
		self.parent = parent
		self.ui = parent.ui
		self.protocol = self.parent.protocol
		
		# defaults
		self.sending = 0
		self.eled = led.LED(self.ui.eraseLed)
		self.tled = led.LED(self.ui.transferLed)
		self.vled = led.LED(self.ui.verifyLed)
		self.clearLeds()
		self.lastTarget = None

		# default target addresses and menu setup
			# name, transferObject(parent, filename, target address, header choice, who for)
		self.targets = [
			['Main Boot',	sRecordTransfer(parent, '', MAIN_BOOT,		0, MAIN_CPU, 'little')],
			['Main App L',	sRecordTransfer(parent, '', MAIN_APP_LEFT,	1, MAIN_CPU, 'little')],
			['Main App R',	sRecordTransfer(parent, '', MAIN_APP_RIGHT,	1, MAIN_CPU, 'little')]
			]
		for entry in self.targets:
			self.ui.targetSelect.addItem(entry[0])
			entry[1].progress.connect(self.progress)
			entry[1].done.connect(self.srecordDone)
			entry[1].eraseFail.connect(self.eled.error)
			entry[1].transferFail.connect(self.tled.error)
			entry[1].verifyFail.connect(self.vled.error)
			entry[1].eraseDone.connect(self.eled.on)
			entry[1].transferDone.connect(self.tled.on)
			entry[1].verifyDone.connect(self.vled.on)
			entry[1].eraseStart.connect(self.eled.blink)
			entry[1].transferStart.connect(self.tled.blink)
			entry[1].verifyStart.connect(self.vled.blink)
			entry[1].starting.connect(self.eled.off)
			entry[1].starting.connect(self.tled.off)
			entry[1].starting.connect(self.vled.off)

		self.ui.targetSelect.setCurrentIndex(0)
		self.showSrecordValues()
		
		# recovery setup
		self.recovering = 0
		self.recover = recover(parent)
		self.recover.done.connect(self.recoverDone)
		self.recover.failed.connect(self.recoverDone)

		# connections for UI
		self.ui.sendSrecord.pressed.connect(self.sendSrecord)
		self.ui.fileSelect.pressed.connect(self.selectFile)
		self.ui.Version.pressed.connect(self.getVersion)
		self.ui.Recover.pressed.connect(self.selectRecover)
		self.ui.targetSelect.currentIndexChanged.connect(self.saveSrecordValues)		
		self.ui.reboot.clicked.connect(self.reboot)
		self.ui.Run.clicked.connect(self.runTarget)
		self.ui.verifyLed.clicked.connect(self.runVerify)
		
	def runTarget(self):
		address = self.target().target
		if address:
			command =  hex(address) + " car "
		else:
			command = "4 execute "
		for c in command:
			self.parent.keyin(c)
		self.parent.keyin("\x0d")

	def clearLeds(self):
		if printme: print('clearLeds')
		self.eled.off()
		self.tled.off()
		self.vled.off()

	# target selection; saving and restoring values to gui
	def target(self):
		if printme: print('target')
		return self.targets[self.ui.targetSelect.currentIndex()][1]
		
	def showSrecordValues(self):
		if printme: print('showSrecordValues')
		target = self.target()
		self.lastTarget = target
		self.ui.srecordFile.setText(target.filename)
		self.ui.addressStart.setText(hex(target.start))
		self.ui.targetAddress.setText(hex(target.target))
		self.ui.size.setText(str(target.size))
		self.ui.entryPoint.setText(hex(target.entry))
		self.ui.checkSum.setText("0x%X"%target.checksum) # prevent L suffix
		self.ui.header.setChecked(target.headerFlag)
		self.ui.endian.setChecked(target.endian == 'big')
	
	def saveSrecordValues(self): # this saves values to last target and shows current
		if printme: print('saveSrecordValues')
		if self.lastTarget:
			target = self.lastTarget
			target.filename = self.ui.srecordFile.text()
			target.start = int(self.ui.addressStart.text(), 0)
			target.target = ~1 & int(self.ui.targetAddress.text(), 0) # keep even
			target.size = ~1 & (1 + int(self.ui.size.text(), 0) ) # keep even
			target.entry = int(self.ui.entryPoint.text(), 0)
			target.checksum = int(self.ui.checkSum.text().rstrip('L'), 0)
			target.headerFlag = self.ui.header.checkState()
			target.endian = 'big' if self.ui.endian.checkState() else 'little'
		self.showSrecordValues()
		
	# sending an srecord
		# use the values in the entry boxes; when switching to another target swap the
		# screen values out to self.targets; 
	def sendSrecord(self):
		try:
			self.runCommand(SEND)
		except Exception as e:
			print(e)
			traceback.print_exc(file=sys.stderr)
		
	def selectFile(self):
		if printme: print('selectFile')
		try:
			target = self.target()
			file = QFileDialog().getOpenFileName(directory=target.dir)
			if file:
				target.useFile(file)
			self.showSrecordValues()
		except Exception as e:
			print(e)
			traceback.print_exc(file=sys.stderr)
		
	def progress(self, n):
		if printme: print('progress')
		if n:
			self.ui.progressBar.setValue(n*1000)
		else:
			self.ui.progressBar.reset()
			self.ui.progressBar.setMaximum(1000)

	def srecordDone(self):
		if printme: print('srecordDone')
		self.sending = 0
		self.ui.sendSrecord.setText('Send')
		self.ui.progressBar.reset()
	
	# get version from target
	def getVersion(self):
		if printme: print('getVersion')

		def version(packet):
			payload = cast('BBHB20sB', packet[2:28])
			major = payload[0]
			minor = payload[1]
			build = payload[2]
			date = payload[4]
			n = payload[5]
			name = cast('%ds'%n, packet[28:28+n])[0]
			note('\n%s  %d.%d.%X  %s'%(name, major, minor, build, date))

		who = [self.parent.whoto, self.parent.whofrom]
		self.protocol.setHandler(pids.VERSION_NO, version)
		self.protocol.sendNPS(pids.GET_VERSION, who)
	
	# recover
	def selectRecover(self):
		if printme: print('selectRecover')
		if self.recovering == 0:
			self.recovering = 1
			self.ui.Recover.setText(" Abort ")
			note('changed protocol to SFP and baud rate to 115200')
			warning('Please press the reset button on the main cpu card.')
			self.ui.SFP.click()
			self.ui.BaudRate.setCurrentIndex(self.ui.BaudRate.findText('115200'))
			self.recover.attempts = 30
			self.recover.startRecovery()
		else:
			self.recover.stopRecovery()
	
	def recoverDone(self):
		if printme: print('recoverDone')
		self.recovering = 0
		self.ui.Recover.setText("Recover")

	def reboot(self):
		for c in "4 execute\x0d":
			self.parent.keyin(c)
		if self.ui.recoverOption.isChecked():
			self.ui.recoverOption.setChecked(0)
			self.selectRecover()

	def runVerify(self):
		self.runCommand(VERIFY)
		
	def runCommand(self, command):
		if printme: print(command)
		if self.sending == 0:
			target = self.target()
			if not target.file:
				self.selectFile()
				if not target.file:
					print('no target file')
					return
			self.saveSrecordValues()
			if command == SEND:
				target.startSending()
			elif command == VERIFY:
				target.startVerify()
			else:
				error('No command to run')
			self.sending = 1
			self.ui.sendSrecord.setText('Abort')
		else:
			self.target().stopSending()
