# test panel for qtran  Robert Chapman III  Oct 24, 2012

from pyqtapi2 import *
import time
from message import *
import sfsp, pids
from modbusRequests import requests
from endian import *
import guidTest
from random import randrange

(NXFILE_OPEN_REQUEST,
NXFILE_OPEN_RESPONSE,
NXFILE_CLOSE_REQUEST,
NXFILE_CLOSE_RESPONSE,
NXFILE_READ_REQUEST,
NXFILE_READ_RESPONSE,
NXFILE_WRITE_REQUEST,
NXFILE_WRITE_RESPONSE) = range(8)

NXO_RDONLY, NXO_WRONLY = range(1,3)

class testPane(QWidget):
	def __init__(self, parent):
		QWidget.__init__(self, parent)
		self.parent = parent
		self.ui = parent.ui
		self.protocol = parent.protocol
		
		self.transfer = 0

		# modbus
		self.ui.modbusRequests.activated.connect(self.modbusRequest)
		for m in range(len(requests)):
			self.ui.modbusRequests.addItem('%d (%d)'%(m,len(requests[m])))

		# guids
		self.guids = guidTest.guidTest(parent)
		
		# nx
		self.readrepeat = 0
		self.ui.openFile.clicked.connect(self.nxOpen)
		self.ui.readFile.clicked.connect(self.nxRead)
		self.ui.closeFile.clicked.connect(self.nxClose)
		self.ui.readAll.clicked.connect(self.nxReadAll)
		self.protocol.packetSource(pids.NXFILE, self.nxfilePacket)
		
		
		# alt
		self.protocol.packetSource(pids.ALT, self.altHandler)
		
		# load
		self.loadTimer = QTimer()
		self.loadTimer.timeout.connect(self.loadFrame)
		self.loadFrames = 0
		self.ui.loadRun.clicked.connect(self.loadRun)
		
		# stats
		self.ui.clearStats.clicked.connect(self.clearStats)
		self.ui.getStats.clicked.connect(self.getStats)
		self.protocol.packetSource(pids.STATS, self.showStats)

		# power
		self.ui.setPower.clicked.connect(self.sendPower)
		
		# imx53
		self.ui.loadImage.clicked.connect(self.loadUimage)
		self.ui.loadUboot.clicked.connect(self.loadUboot)
		self.ui.bootLinux.clicked.connect(self.bootLinux)

	# alt
	def altHandler(self, packet):
		note('ALT: '+''.join(map(chr, packet[5:])))

	# nx file
	def cfd(self):
		return shortList(int(self.ui.cfd.text()))

	def sfd(self):
		return shortList(int(self.ui.sfd.text()))
	
	def setCfd(self, i):
		self.ui.cfd.setText(str(i))
		
	def setSfd(self, i):
		self.ui.sfd.setText(str(i))
		
	def nxFile(self):
		note( 'nxFile')
		if self.transfer == 0:
			self.transfer = 1
			self.ui.getfile.setText("Abort")
		else:
			self.transfer = 0
			self.ui.getfile.setText("Get File")

#typedef struct {
#	Byte pid;
#	who_t who;
#	tid_t tid;
#	Byte spid;
#	Byte payload[];
#} filePacket_t;
	
	def nxfilePacket(self, packet):
		size = 0
		if self.ui.readText.isChecked():
			messageDump( 'nxfilepacket: ', packet, 1)
		elif self.ui.readHex.isChecked():
			messageDump( 'nxfilepacket: ', packet)
		spid = cast('BBBBB', packet)[4]
		payload = packet[5:]
		[cfd, sfd, err] = cast('HHB', payload)
		self.setCfd(cfd)
		self.setSfd(sfd)
		if spid == NXFILE_OPEN_RESPONSE:
			note('open response: %d, cfd: %d  sfd: %d'%(err, cfd, sfd))
		elif spid == NXFILE_CLOSE_RESPONSE:
			note('close response: %d, cfd: %d  sfd: %d'%(err, cfd, sfd))
		elif spid == NXFILE_READ_RESPONSE:
			size = len (payload) - 5
			note('read response: %d, cfd: %d  sfd: %d  len: %d'%(err, cfd, sfd, size))
		if self.readrepeat and size != 0:
			self.readrepeat -= 1
			self.nxReadLine()

	def nxOpen(self):
		self.readrepeat = 0
		tid = [0, 0]
		spid = [NXFILE_OPEN_REQUEST]
		flags = [self.ui.access.currentIndex() + 1]
		filename = map(ord, self.ui.transferfile.currentText()) + [0]
		payload = self.cfd() + self.sfd() + flags + filename
		packet = self.parent.who() + tid + spid + payload
		self.protocol.sendNPS(pids.NXFILE, packet)
	
	def nxRead(self):
		self.readrepeat = int(self.ui.numberLines.text()) - 1
		self.nxReadLine()

	def nxReadAll(self):
		self.readrepeat = 1000
		self.nxReadLine()

	def nxReadLine(self):
		tid = [0, 0]
		spid = [NXFILE_READ_REQUEST]
		size = [int(self.ui.readSize.text())]
		payload = self.cfd() + self.sfd() + size
		packet = self.parent.who() + tid + spid + payload
		self.protocol.sendNPS(pids.NXFILE, packet)
	
	def nxClose(self):
		tid = [0, 0]
		spid = [NXFILE_CLOSE_REQUEST]
		cfd = [0,0]
		sfd = [0,1]
		payload = self.cfd() + self.sfd()
		packet = self.parent.who() + tid + spid + payload
		self.protocol.sendNPS(pids.NXFILE, packet)
	
	# modbus
	def modbusRequest(self, i):
		payload = requests[i]
		tid = [0, 0]
		while payload:
			length = len(payload)
			if length > sfsp.MAX_SPID_PACKET_PAYLOAD:
				length = sfsp.MAX_SPID_PACKET_PAYLOAD				
				spid = [1] # should set to 1 for partial payload
			else:
				spid = [0] # should set to 0 for last payload
			packet = self.parent.who() + tid + spid + payload[0:length]
			self.protocol.sendNPS(pids.MODBUS, packet)
			payload = payload[length::]
	
	# load test
	def loadRun(self):
		if self.loadFrames:
			self.ui.loadRun.setText('Run')
			self.loadTimer.stop()
		else:
			self.ui.loadRun.setText('Abort')
			self.loadFrames = int(self.ui.loadFrames.text())
			delay = int(self.ui.loadDelay.text())
			self.loadTimer.setInterval(delay)
			self.loadTimer.start()
	
	def loadFrame(self):
		if self.loadFrames:
			self.loadFrames -= 1
			packet = [randrange(0,255) for i in range(int(self.ui.loadSize.text()))]
			self.protocol.sendNPS(pids.TEST_FRAME, packet)
		else:
			self.ui.loadRun.setText('Run')
			self.loadTimer.stop()

	# stats
	def getStats(self):
		self.protocol.sendNPS(pids.GET_STATS, self.parent.who())
		
	def clearStats(self):
		self.protocol.sendNPS(pids.CLEAR_STATS, self.parent.who())
		
	def showStats(self, packet):
		statnames = [
			'long_frame',
			'short_frame',
			'tossed',
			'good_frame',
			'bad_checksum',
			'timeouts',
			'resends',
			'rx_overflow',
			'sent_frames',
			'unknown_packets',
			'unrouted']
		stats = cast('BB11L', packet)[2:]
		for i in range(len(stats)):
			if stats[i]:
				note('%s: %i'%(statnames[i],stats[i]))
	
	# Power
	def sendPower(self):
		power = 0xFF # nothing on
		if self.ui.displayPower.isChecked(): power &= ~0x40
		if self.ui.slotaPower.isChecked(): power &= ~0x20
		if self.ui.slotbPower.isChecked(): power &= ~0x10
		if self.ui.slot1Power.isChecked(): power &= ~0x08
		if self.ui.slot2Power.isChecked(): power &= ~0x04
		if self.ui.slot3Power.isChecked(): power &= ~0x02
		if self.ui.slot4Power.isChecked(): power &= ~0x01
		self.parent.sendPhrase("reseti2c 0x%x bpower"%power)

	# imx53
	def loadUboot(self):
		self.thread = uboot(self)
		self.thread.setTerminationEnabled()
		self.thread.start()
		return
		self.ui.loadUboot.setText('Abort')
		def abortLoadUboot():
			self.parent.selectPort()
			self.thread.terminate()
			self.thread.wait()
			self.ui.loadUboot.setText('Load Uboot')
			self.ui.loadUboot.clicked.connect(self.loadUboot)
		self.ui.loadUboot.clicked.connect(abortLoadUboot)


	def loadUimage(self): # for writing uImage from host1 usb stick to NAND
		try:
			filename = self.ui.uimageFile.text()
			bootsize = int(self.ui.uimageSize.text(), 0)
			bootfrom = self.uimageAddress()
			bootPhrase = 'setenv koffset 0x%x; setenv ksize 0x%x; usb start; fatload usb 0:1 0x70800000 %s; run nandkernargs; ${ekern}; ${wkern}'%(bootfrom, bootsize, filename)
			self.parent.sendPhrase(bootPhrase)
		except Exception, e:
			print e
			traceback.print_exc(file=sys.stderr)

	def bootLinux(self): # run an uImage from NAND
		def send(phrase):
			self.parent.sendPhrase(phrase+'\r')
			time.sleep (0.3)

		bootsize = int(self.ui.uimageSize.text(), 0)
		dramsize = 0x10000000
		bootfrom = self.uimageAddress()
		nexusbin = '/home/nexus/bin'
		startup = 'startup'
		usbmount = 'usbmount'
		if self.ui.left.isChecked():
			choice = 'left'
		else:
			choice = 'right'
		console = 'ttymxc0'
		mtdparts = 'mtdparts=mxc_nandv2_flash:16M(boot),48M(uImageLeft),48M(uImageRight),-(ubi)'

		send("setenv cbootargs startup=%s/%s"%(nexusbin, startup))
		send("setenv cbootargs ${cbootargs} usbmount=%s/%s "%(nexusbin, usbmount))
		send("setenv cbootargs ${cbootargs} imageselect=%s "%choice)
		send("setenv cbootargs ${cbootargs} video=mxcdi0fb:RGB666,VGA2 ")
		send("setenv cbootargs ${cbootargs} di0_primary ")
		send("setenv cbootargs ${cbootargs} ip=10.0.0.10 ")
		send("setenv cbootargs ${cbootargs} consoleblank=0 ")
		send("setenv cbootargs ${cbootargs} mem=%#x "%dramsize)
		send("setenv mtdparts %s"%mtdparts)
		send("setenv koffset %#x"%bootfrom)
		send("setenv ksize %#x"%bootsize)
		if self.ui.ubifs.checkState():
			send("run ubifsboot")
			pass
		else: # 128MB
			send("run nandboot")

	def uimageAddress(self):
		if self.ui.left.isChecked():
			return 0x1000000
		return 0x4000000

class uboot(QThread):
	def __init__(self, parent):
		QThread.__init__(self) # needed for signals to work!!
		self.parent = parent.parent
		self.ui = parent.ui

	def run(self):
		try:
			from iMX_Display_Serial_Download_Protocol import main
			import sys

			self.parent.serialPort.close()
			file = str(self.ui.ubootFile.text())
			portname = str(self.parent.prefix+self.parent.portname)
			speed = ''
			if self.ui.passthru.checkState():
				speed = 'same'
			sys.argv = ['serial_command', portname, 'exec%s'%speed, '0x777ffc00', file]
			oldout, olderr = sys.stdout, sys.stderr
			sys.stdout = sys.stderr = stdMessage
			self.ui.loadUboot.setDisabled(True)
			main()
		except Exception, e:
			print e
			traceback.print_exc(file=sys.stderr)
		finally:
			self.ui.loadUboot.setEnabled(True)
			self.parent.selectPort()
			sys.stdout, sys.stderr = oldout, olderr
			self.parent.sendPhrase(' \n')
	