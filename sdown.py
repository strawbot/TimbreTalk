#!/usr/bin/env python

help = '''command line program to download srecords. Usage:
 sdown (port=xxx | mqRecv=xxx mqSend=xxx) [rate=xxx] (file=xxx|fwDbOp=<firmware DB operation>) [from=<HOST>] [to=<CPU>] [recover=n] [type=<TYPE>] [side=<SIDE>] [fileop=<OPER>] [guid=<GUID> value=<VALUE>] [dereg=<GUID>]
 sdown list
 sdown version
 sdown help
  <HOST> = main, display, display_cpu, backplane, slota, slotb; default: main
  <CPU> = main, slota, slotb; default: main
  <TYPE> = app, boot, hiboot, launcher, uboot, ioapp, biguboot; default: app
  <SIDE> = left, right; default: left
  <firmware DB Operation> = version, invalid, rebuild, setboot, reboot, ismain
  <OPER> = send, verify; default: send
  <GUID> = numerical value of a guid
  <VALUE> = to send with a guid
'''
 
''' todo:
handle error cases from transfer and abort reset
accept quit command like ^c
'''

version = 'sdown V.8'

printme = 0	# set to 1 to print >>sys.stderr, debug statements

from pyqtapi2 import *

import sys, traceback
import listports, pids, serialio, sfsp
from message import *
from cpuids import *
import recover, srecordTransfer
import sfpMessageQueue
from targets import *
import os
import fwdb
from signalcatch import initSignalCatcher
import guidsend
import pids

BOOT, APP, HIBOOT, LAUNCHER, UBOOT, IOAPP, SWBAPP, BIGUBOOT= 'boot','app','hiboot','launcher','uboot','ioapp','swbapp', 'biguboot'
LEFT, RIGHT = 0,1
SEND, VERIFY = 'send','verify'

class sdownload(QObject):
	result = 0
	shutDown = Signal()
	finished = Signal()

	def __init__(self, argv, app):
		QObject.__init__(self) # needed for signals to work!!
		self.argv = argv
		self.coreapp = app
		sys.excepthook = lambda *args: None
		initSignalCatcher(self.sigAbort)
	
	def sigAbort(self):
		if printme: print >>sys.stderr, 'sigAbort'
		self.abort()
		self.coreapp.aboutToQuit.emit()

	def abort(self):
		if printme: print >>sys.stderr, 'abort'
		self.quit(-1)
	
	def quit(self, result = 0):
		if printme: print >>sys.stderr, 'quit'
		if self.result == 0:
			self.result = result
		self.finished.emit()	

	def run(self):
		# defaults
		self.parameters = {
		'port':'',
		'mqRecv':'',
		'mqSend':'',
		'rate':115200,
		'file':'',
		'fwDbOp':'',
		'to':MAIN_CPU,
		'from':MAIN_HOST,
		'target':0x100000,
		'recover':0,
		'header':1,
		'type':APP,
		'side':LEFT,
		'fileop':SEND,
		'guid':'0',
		'value':'0',
		'dereg':0
		}
		self.parseArgs(self.argv) # alter parameters
		self.whoto = DIRECT
		self.whofrom = self.parameters['from']

		# reverse who
		links = ['']*(ROUTING_POINTS+1)
		for key in whoDict.keys():
			links[whoDict[key]] = key

		# check for what to do
		if self.parameters['recover'] or self.parameters['file'] or self.parameters['fwDbOp'] or self.parameters['guid'] or self.parameters['dereg']:
			# protocol
			self.protocol = sfsp.sfspProtocol()
			self.protocol.packetSource(pids.ALT, self.nullPacketHandler)
			self.protocol.packetSource(pids.GUID, self.nullPacketHandler)

			# serial port
			if self.parameters['port'] != '':
				self.serialPort = serialio.serialPort()
				self.prefix, self.ports = listports.listports()
				if self.parameters['port']:
					self.portname = self.parameters['port']
				else:
					self.portname = ''
					if self.ports:
						self.portname = self.ports[0]
				if self.parameters['rate']:
					self.serialPort.rate = self.parameters['rate']
				else:
					self.serialPort.rate = 115200
				self.selectPort()
			elif self.parameters['mqRecv'] and self.parameters['mqSend']:
				self.mqRecvName = self.parameters['mqRecv']
				self.mqSendName = self.parameters['mqSend']
				self.setupMessageQueues(self.mqRecvName, self.mqSendName)
			else:
				print >>sys.stderr, 'No portname. No message queues specified.  Exiting'
				self.abort()
				return

		if self.parameters['recover']:
			print >>sys.stderr, 'Reset unit using the reset button or power cycling.'
			recovery = recover.recover(self, self.parameters['recover'])
			recovery.failed.connect(self.abort)
			if self.parameters['file']:
				recovery.recovered.connect(self.downloadSrecord)
			else:
				recovery.recovered.connect(self.quit)
			recovery.startRecovery()
		elif self.parameters['file']:
			print >>sys.stderr, 'beginning file download'
			self.whoto = self.parameters['to']
			self.selectTarget()
			self.downloadSrecord()
		elif self.parameters['fwDbOp']:
			print >>sys.stderr, 'sending firware DB operation'
			self.whoto = self.parameters['to']
			self.selectTarget()
			self.fwDbOpRun()
		elif self.parameters['guid']:
			self.guidmgr = guidsend.guidManager(self)
			self.guidmgr.sendGuid(self.parameters['guid'], self.parameters['value'])
			if self.parameters['port'] != '':
				self.serialPort.close()
			self.quit()
		elif self.parameters['dereg']:
			self.guidmgr = guidsend.guidManager(self)
			self.guidmgr.deregisterGuid(self.parameters['dereg'])
			if self.parameters['port'] != '':
				self.serialPort.close()
			self.quit()
		else:
			self.quit()

	def downloadSrecord(self):
		# srecord
		file = self.parameters['file']
		target = self.parameters['target']
		header = self.parameters['header']
		if self.parameters['type'] in [UBOOT, BIGUBOOT]:
			srecord = srecordTransfer.ubootTransfer(self, file, target, header)
		else:
			srecord = srecordTransfer.sRecordTransfer(self, file, target, header)

		def progress(n):
			sys.stdout.write('.')
			sys.stdout.flush()
		srecord.progress.connect(progress)
		srecord.done.connect(self.quit)
		srecord.aborted.connect(self.abort)
		srecord.verifyFail.connect(self.abort)
		srecord.eraseFail.connect(self.abort)
		srecord.transferFail.connect(self.abort)

		print >>sys.stderr, ''
		print >>sys.stderr, 'name:',srecord.filename
		print >>sys.stderr, 'start: 0x%X'%srecord.start
		print >>sys.stderr, 'size:',srecord.size
		print >>sys.stderr, 'entry: 0x%X'%srecord.entry
		print >>sys.stderr, 'target: 0x%X'%srecord.target
		print >>sys.stderr, 'checksum: 0x%X'%srecord.checksum
		print >>sys.stderr, 'header:',srecord.headerFlag
		print >>sys.stderr, 'side:', self.parameters['side']
		print >>sys.stderr, 'fileop:', self.parameters['fileop']

		if self.parameters['fileop'] == VERIFY:
			srecord.startVerify()
		else:
			srecord.startSending()

		# shutdown signals
		def shutdownAll():
			if printme: print >>sys.stderr, 'shudown all'
			self.protocol.shutdown()
			srecord.shutdown()
			self.serialPort.shutdown()
			self.shutdown()
		self.coreapp.aboutToQuit.connect(shutdownAll)
		
	def fwDbOpRun(self):
		target = self.parameters['target']
		fwdbInst = fwdb.fwdb(self, target)

		def progress(n):
			sys.stdout.write('.')
			sys.stdout.flush()
		fwdbInst.progress.connect(progress)
		fwdbInst.doneFail.connect(lambda: self.coreapp.exit(-1))
		fwdbInst.donePass.connect(lambda: self.coreapp.exit(0))

		print >>sys.stderr, ''
		print >>sys.stderr, 'target: 0x%X'%fwdbInst.target
		print >>sys.stderr, 'side:', self.parameters['side']

		fwdbInst.sendOp(self.parameters['fwDbOp'], self.parameters['side'])

		# shutdown signals
		def shutdownAll():
			self.protocol.shutdown()
			self.serialPort.shutdown()
			self.shutdown()
		self.coreapp.aboutToQuit.connect(shutdownAll)

	def selectTarget(self): # determine target parameters
		# given the target cpu app, select target address and header
		header = 1 # default
		target = None	# none

		to = self.parameters['to']
		type = self.parameters['type']
		side = self.parameters['side']

		if to == MAIN_CPU:
			if side == LEFT:
				if type == BOOT:		target, header = MAIN_BOOT, 0
				elif type == LAUNCHER:	target = LAUNCHER_LEFT
				elif type == APP:		target = MAIN_APP_LEFT
				elif type == UBOOT:		target = UBOOT_LEFT
				elif type == BIGUBOOT:	target = BIG_UBOOT_LEFT
				elif type == IOAPP:		target = IO_APP_LEFT
				elif type == SWBAPP:		target = SWB_APP_LEFT
				else: error('Illegal firmware type %s for %s on %s.'%(type,to,side))
			else:
				if type == BOOT:		target, header = MAIN_BOOT, 0
				elif type == LAUNCHER:	target = LAUNCHER_RIGHT
				elif type == APP:		target = MAIN_APP_RIGHT
				elif type == UBOOT:		target = UBOOT_RIGHT
				elif type == BIGUBOOT:	target = BIG_UBOOT_RIGHT
				elif type == IOAPP:		target = IO_APP_RIGHT
				elif type == SWBAPP:		target = SWB_APP_RIGHT
				else: error('Illegal firmware type %s for %s on %s.'%(type,to,side))

		elif to in [SLOTA_CPU, SLOTB_CPU]:
			if type == BOOT:		target, header = IO_BOOT, 0
			elif type == HIBOOT:	target = IO_HIGH_BOOT
			elif type == APP:		target = IO_APP
			else: error('Illegal firmware type %s for %s.'%(type,to))

		else: error('Illegal firmware type %s for %s on %s.'%(type,to,side))

		self.parameters['header'] = header
		self.parameters['target'] = target
		
	def shutdown(self):
		if printme: print >>sys.stderr, 'shutindown'

	def who(self):
		return [self.whoto, self.whofrom]

	def parseArgs(self, argv): # put args into parameters
		if len(argv) == 0:
			print >>sys.stderr, help
			self.quit()
			return

		for arg in argv:
			arg = arg.split('=')
			if arg[0] in self.parameters:
				if arg[0] == 'to':
					self.parameters['to'] = {
						'main':MAIN_CPU, 'slota':SLOTA_CPU, 'slotb':SLOTB_CPU}[arg[1]]
				elif arg[0] == 'from':
					self.parameters['from'] = {
						'main':MAIN_HOST, 'display':DISPLAY_HOST, 'display_cpu':DISPLAY_CPU, 'backplane':DISPLAY_HOST,
						'slota':SLOTA_HOST, 'slotb':SLOTB_HOST}[arg[1]]
				elif arg[0] == 'type':
					if arg[1] in ['APP', 'app']:
						self.parameters['type'] = APP
					elif arg[1] in ['BOOT', 'boot']:
						self.parameters['type'] = BOOT
					elif arg[1] in ['HIBOOT', 'hiboot']:
						self.parameters['type'] = HIBOOT
					elif arg[1] in ['LAUNCHER', 'launcher']:
						self.parameters['type'] = LAUNCHER
					elif arg[1] in ['UBOOT', 'uboot']:
						self.parameters['type'] = UBOOT
					elif arg[1] in ['BIGUBOOT', 'biguboot']:
						self.parameters['type'] = BIGUBOOT
					elif arg[1] in ['IOAPP', 'ioapp']:
						self.parameters['type'] = IOAPP
					elif arg[1] in ['SWBAPP', 'swbapp']:
						self.parameters['type'] = SWBAPP
					else:
						print >>sys.stderr, 'Unkown app={0}'.format(arg[1]) 
				elif arg[0] == 'side':
					if arg[1] in ['LEFT', 'left']:
						self.parameters['side'] = LEFT
					elif arg[1] in ['RIGHT', 'right']:
						self.parameters['side'] = RIGHT
					else:
						print >>sys.stderr, 'Unkown side={0}'.format(arg[1])
				elif arg[0] == 'fileop':
					if arg[1] == VERIFY:
						self.parameters['fileop'] = VERIFY
					elif arg[1] == SEND:
						pass
					else:
						print >>sys.stderr, 'Unknow file operation={0}'.format(arg[1])
				elif (len(arg) > 1):
					if type(self.parameters[arg[0]]) == type(''):
						self.parameters[arg[0]] = arg[1]
					else:
						self.parameters[arg[0]] = int(arg[1], 0)
				else:
					self.parameters[arg[0]] = 1
			elif arg[0] == 'test':
				self.parameters['file'] = 'test/test.s19'
				self.q = quitter(self.coreapp)
				self.q.start()
			elif arg[0] in ['listports','list']:
				print >>sys.stderr, 'List of available ports:'
				for port in listports.listports()[1]:
					print >>sys.stderr, port
				self.quit()
				return
			elif arg[0] == 'version':
				print >>sys.stderr, version
				self.quit()
				return
			elif arg[0] == 'help':
				print >>sys.stderr, help
				self.quit()
				return
		print >>sys.stderr, 'Parameters:'
		for item in sorted(self.parameters.items()):
			print >>sys.stderr, item[0],'=',item[1]

	def setupMessageQueues(self, mqRecvName, mqSendName):
		self.mqSend = sfpMessageQueue.sfpMessageQueSend(mqSendName)
		self.protocol.source.connect(self.mqSend.sink)
		
		self.mqRecv = sfpMessageQueue.sfpMessageQueRecv(mqRecvName, self.protocol.packetq)
		self.mqRecv.start()
		
	def selectPort(self, port=None, rate=None):
		if self.serialPort.isOpen():
			self.serialPort.close()
		if port:
			self.portname = port
		if rate:
			self.serialPort.rate = rate
		self.serialPort.open(self.prefix, self.portname, self.serialPort.rate)
		if self.serialPort.isOpen():
			self.serialPort.closed.connect(self.serialDone)
			self.serialPort.ioError.connect(self.ioError)
			self.serialPort.ioException.connect(self.ioError)
			# connections
			self.protocol.source.connect(self.serialPort.sink)
			self.serialPort.source.connect(self.protocol.sink)
		else:
			self.portname = None

	def ioError(self, message):
		error(message)
		self.serialPort.close()

	def serialDone(self):
		note('Serial thread finished')

	def sink(self, s, style=''):
		message(s)

	# test
	def test(self):
		q = quitter(self.coreapp)
		q.start()
		self.protocol.packetSource(pids.PING_BACK, s.pingBack)
		self.sendPing()

	# ping test
	def sendPing(self):
		self.protocol.sendNPS(pids.PING, [])

	def pingBack(self, packet):
		note('received PING_BACK')
#		self.quit()

	def nullPacketHandler(self, packet):
		pass # dump packets

class quitter(QThread):
	def __init__(self, app):
		QThread.__init__(self) # needed for signals to work!!
		self.app = app
		
	def run(self):
		print('\n press <esc><return> to quit ')
		while self.getKey() != chr(0x1b):
			pass
		
		self.app.quit()

	if sys.platform == 'win32':
		def getKey(self):
			import msvcrt
			return msvcrt.getch()
	else:
		def getKey(self):
			return sys.stdin.read(1)

if __name__ == "__main__":
	try:
		app = QCoreApplication([])
		worker = sdownload(sys.argv[1:], app)		
		worker.finished.connect(lambda: app.exit(worker.result), Qt.QueuedConnection)
		worker.run()
		os._exit(app.exec_())
	except Exception, e:
		print >>sys.stderr, ' got an excpeption '
		print >>sys.stderr, e
		traceback.print_exc(file=sys.stderr)
		os._exit(-1)
