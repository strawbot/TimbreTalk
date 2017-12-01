# bootloader file transfer  Robert Chapman III  Aug 25, 2015

from pyqtapi2 import *

import sys, traceback	
from endian import *
from message import *
from imageTransfer import imageTransfer
import xmodem

printme = 0

class microTransfer(imageTransfer):
    ACK = chr(0x79)
    NACK = chr(0x1F)

    def __init__(self, parent):
        super(microTransfer, self).__init__(parent)
        # extra parameters
        self.address = ""
        self.version = 0
        self.verbose = 0
        self.run = 0
        self.serialPort = self.parent.parent.serialPort

    def setParam(self, sp, parity, bytesize, stopbits):
        if sp.port:
            sp.port.parity = parity
            sp.port.bytesize = bytesize
            sp.port.stopbits = stopbits

    def send(self, tx):
        self.serialPort.sink(tx)

    def disconnectPort(self):
        self.parent.parent.disconnectPort()

    def listenBoot(self):
        note('Redirecting serial port to boot listener')
        self.disconnectPort()

        def showRx(rx):
            note('Rx:%s' % ''.join(map(lambda x: ' ' + hex(ord(x))[2:], rx)))

        self.serialPort.source.connect(showRx)
        self.setSerialPort()

    def noListenBoot(self):
        self.parent.parent.connectPort()
        note('Serial port reconnected')

    def abortBoot(self):
        self.noListenBoot()

    def reconnectSerial(self):
        self.setProgress.emit(1)
        if self.startTransferTime:
            self.finish()
        self.finishBoot()

    def finishBoot(self):
        self.transferTimer.stop()
        self.noListenBoot()
        self.setAction.emit('Transfer')

    # variable setting
    def setVerbose(self, value):
        self.verbose = value

    def setRun(self, value):
        self.run = value

# for STM micros from factory
class stmTransfer(microTransfer):
    def __init__(self, parent):
        super(stmTransfer, self).__init__(parent)

    def setSerialPort(self):
        self.setParam(self.serialPort, 'E', 8, 1)

    # Boot downloader
    def requestTransfer(self):
        if not self.serialPort.isOpen():
            error("No serial port open")
            return
        note('Acquiring serial port for boot loader')
        self.setProgress.emit(0)
        self.disconnectPort()
        self.setSerialPort()
        message("Switching to STM32F4 bootloader protocol")
        self.serialPort.source.connect(self.nextSuccessor)
        note('Connecting with boot loader... ')
        self.onAck([0x7F], self.eraseBoot)
        self.setProgress.emit(.025)

    # support for sequencing off of replies
    def fail(self):
        error('NACK:')
        self.abortBoot()

    def onAck(self, sequence, successor, failure=0): # setup callback for next step
        if self.verbose:
            note('Tx:%s'%''.join(map(lambda x: ' '+hex(x)[2:],  sequence)))
        self.serialPort.sink(sequence)
        self.nextState = successor
        self.failState = failure if failure else self.fail

    def nextSuccessor(self,ack): # invoke callback if acked
        if self.verbose:
            note('Rx: %s'% hex(ord(ack[0]))[2:])
        if ack == self.ACK:
            self.nextState()
        elif ack == self.NACK:
            self.failState()
        else:
            error('NACK:'+ack)
            self.abortBoot()

    # STM32 Boot Loader
    def sendHex(self, bytes):
        try:
            note('sending: ' + reduce(lambda a, b: a + b, map(hex, bytes)))
            self.parent.serialPort.sink(bytes)
        except Exception, e:
            print >> sys.stderr, e
            traceback.print_exc(file=sys.stderr)

    def checksummed(self, bytes):
        bytes.append(reduce(lambda a, b: a ^ b, bytes))
        return bytes

    def checked(self, byte):
        return (byte, ~byte & 0xFF)

    # states
    def eraseBoot(self):
        message('connected')
        note('Erasing...')
        self.transferTimer.start(20000)
        self.onAck(self.checked(0x44), self.erasePages)
        self.setProgress.emit(.05)

    def erasePages(self):  # erase pages not supported; erase all
        self.onAck(self.checksummed([0xFF, 0xFF]), self.downloadBoot)

    def downloadBoot(self):
        elapsed = time.time() - self.startTransferTime
        message(' flash erased in %.1f seconds' % elapsed, 'note')

        note('Download image ')
        self.pointer = self.start
        self.writeCommand()
        self.chunk = 256

    def writeCommand(self):  # progress bar from .1 to .9
        self.transferTimer.start(2000)
        self.setProgress.emit(.1 + (.8 * (self.pointer - self.start) / self.size))
        if self.pointer < self.end:
            self.onAck(self.checked(0x31), self.writeAddress)
        else:
            self.verifyBoot()

    def writeAddress(self):
        address = self.checksummed(longList(self.pointer))
        self.onAck(address, self.writeData)

    def writeData(self):
        if not self.verbose:
            message('.', "note")
        self.chunk = min(self.chunk, self.end - self.pointer)
        if self.chunk % 4:
            error('Transfer size not a multiple of 4: %d' % self.chunk)
            note('Image size: %d' % self.size)
        index = self.pointer - self.start
        self.pointer += self.chunk
        data = self.image[index:index + self.chunk]
        self.onAck(self.checksummed([self.chunk - 1] + data), self.writeCommand)

    def verifyBoot(self):  # not verified, just trusted
        # note('\nverify image')
        if self.run:
            self.goCommand()
        else:
            self.reconnectSerial()

    def goButton(self):
        self.listenBoot()
        self.serialPort.source.connect(self.nextSuccessor)
        self.startTransferTime = 0
        self.onAck([0x7F], self.goCommand, self.goCommand)

    def goCommand(self):
        self.onAck(self.checked(0x21), self.goAddress)

    def goAddress(self):
        if not self.address:
            self.address = "0x8000000"
        self.echoTx(self.checksummed(longList(int(self.address, 0))))
        self.reconnectSerial()

    def echoTx(self, tx):
        note('Tx:%s' % ''.join(map(lambda x: ' ' + hex(x)[2:], tx)))
        self.send(tx)

# for silicon labs from the factory
class efmTransfer(microTransfer):
    def __init__(self, parent):
        super(efmTransfer, self).__init__(parent)

    def xmodemStatus(self, total_packets, success_count, error_count):
        self.setProgress.emit(success_count/total_packets)
        # total sent so far. Need total to be sent to be useful!

    def requestTransfer(self):
        import logging
        logging.basicConfig(level=logging.DEBUG)

        if not self.serialPort.isOpen():
            error("No serial port open")
            return

        rate = self.serialPort.port.baudrate

        self.serialPort.close()
        self.transferTimer.start(20000)
        message('\nAcquiring serial port for binary transfer...')
        self.serialPort.openBlocking(self.parent.parent.prefix,
                                     self.parent.parent.portname,
                                     rate=rate)

        message("\nSwitching to EFM32 bootloader protocol")
        # def xmoden (thread)...
        xm = xmodem.XMODEM(self.serialPort.getc, self.serialPort.putc)
        self.send('u')
        self.serialPort.getc(9, 1) # pull out <d><a>Ready<d><a> reply
        filename = self.file.rsplit(".", 1)[0] + ".bin" # xmodem works with binary image
        stream = file(filename, 'rb')
        if not xm.send(stream): #, callback=self.xmodemStatus):
            error("file transfer failed")
        self.finish()

    def finish(self):
        self.serialPort.close()
        super(efmTransfer, self).finish()
        self.parent.parent.selectPort()

    def goButton(self):
        pass
