# Generic File Transfer  Robert Chapman III  May 11, 2016

from pyqtapi2 import *

import sys, traceback	
from endian import *
from protocols.interface.message import *
from checksum import fletcher32
import image
from transfer import *
import protocols.pids as pids

class imageTransfer(image.imageRecord):
    setProgress = Signal(object)
    setAction = Signal(object)
    # perhaps the following parameters should be in the children files which use SFP
    # or bring pids into this module and have it as an SFP transfer but make a super
    # class which is protocol independant
    chunk = 240 # default size to transfer; should derive from MAX_FRAME_LENGTH
    transferPid = pids.FILES # pid for transfer operations
    transferType = BINARY_TRANSFER # type of file if needed
    maxRetries = 5 # maximum number of retries for transferring chunks

    def __init__(self, parent):
        super(imageTransfer, self).__init__(parent)

        # timing
        self.transferTimer = QTimer()
        self.transferTimer.timeout.connect(self.timedOut)
        self.transferTimer.setSingleShot(True)
        self.transferDelay = 2000

        # shortcuts
        self.protocol = self.parent.protocol


    def who(self):
        return self.parent.parent.who() # packet routing

    def abortButton(self):
        self.setAction.emit(' Abort  ')

    def transferButton(self):
        self.setAction.emit('Transfer')

    # states
    # upload
    def requestFile(self, file):
        self.startTransferTime = time.time()
        self.name = file
        payload = self.who() + [TRANSFER_FILE] + list(map(ord, self.name)) + [0]
        self.protocol.sendNPS(self.transferPid, payload)

    # download
    def sendFile(self):
        if self.transferTimer.isActive():
            self.abort()
        else:
            if self.image:
                self.checkUpdates()
                self.startTransferTime = time.time()
                self.setProgress.emit(0)
                self.setupTransfer()
                self.transferTimer.timeout.disconnect()
                self.transferTimer.timeout.connect(self.timedOut)
                self.transferTimer.start(5000)
                self.abortButton()
                self.requestTransfer()
            else:
                error(" Host: No image for downloading")

    def setupTransfer(self):
        pass

    def requestTransfer(self):
        size = longList(self.size)
        name = list(map(ord, self.name)) + [0]
        type = [self.transferType]
        payload = self.who() + [TRANSFER_REQUEST] + size + type + name
        self.protocol.sendNPS(self.transferPid, payload)

    def startTransfer(self):
        self.i = 0
        self.pointer = 0
        self.left = self.size

        self.transferTimer.timeout.disconnect()
        self.transferTimer.timeout.connect(self.resendChunk)
        self.transferTimer.start(self.transferDelay)
        self.retries = self.maxRetries
        self.transferChunk()

    def transferChunk(self):
        if self.left:
            if self.left > self.chunk:
                sendsize = self.chunk
                self.left -= self.chunk
            else:
                sendsize = self.left
                self.left = 0
            self.transferData(self.image[self.pointer:self.pointer+sendsize])
            self.setProgress.emit((self.size - self.left)/self.size)
            self.i += 1
            self.pointer += sendsize
            self.transferTimer.start(self.transferDelay)
        else:
            self.transferDone()
            self.transferTimer.timeout.disconnect()
            self.transferTimer.timeout.connect(self.timedOut)
            self.transferTimer.start(20000)

    def resendChunk(self):
        if self.retries:
            note(" Host: timed out - resending last chunk")
            self.protocol.sendNPS(self.transferPid, self.lastPayload)
            self.retries -= 1
        else:
            error(' Host: timed out - no more retries left; transfer aborted')
            self.abort()

        '''
        typedef struct {
            Byte pid;
            who_t who;
            Byte spid;
            long_t address;
            Byte data[];
        } dataPacket_t;
        '''
    def transferData(self, data):
        self.lastPayload = self.who() + [TRANSFER_DATA] + longList(self.i) + data
        self.protocol.sendNPS(self.transferPid, self.lastPayload)

    def transferDone(self):
        payload = self.who() + [TRANSFER_DONE] + longList(self.checksum)
        self.protocol.sendNPS(self.transferPid, payload)

    def transferResponse(self, packet):
        spid = cast('BBB', packet)[2]
        if spid == TRANSFER_REPLY:
            if packet[3] == REQUEST_OK:
                note(' Host: Request approved. Starting data transfer...')
                self.startTransfer()
            else:
                error(' Host: Request denied:'+resultText.get(packet[3],'Unknown'))
                self.abort()
        elif spid == TRANSFER_RESULT:
            if packet[3] == TRANSFER_OK:
                self.transferChunk()
            elif packet[3] == TRANSFER_COMPLETE:
                note(' Host: Transfer complete')
                self.finish()
            else:
                error(' Host: Transfer failed. '+resultText.get(result,'Unknown'))
                self.abort()
        elif spid == TRANSFER_DATA:
            data = packet[4:]
            note(" Host: got data ")
            payload = self.who() + [TRANSFER_RESULT, TRANSFER_OK]
            self.protocol.sendNPS(self.transferPid, payload)
        elif spid == TRANSFER_DONE:
            note(" Host: Transfer done")
        elif spid == TRANSFER_COMPLETE:
            note(" Host: transfer complete")
            self.finish()
        elif spid == FILE_UNAVAILABLE:
            note(" Host: file unavailable")
            self.abort()
        else:
            error(' Host: Unknown spid:'+hex(spid))
            self.abort()

    # possible end sequences
    def timedOut(self):
        error(' Host: Timed out')
        self.abort()

    def abort(self):
        error(' Host: Transfer aborted.')
        self.finish()

    def finish(self):
        self.transferTimer.stop()
        self.transferButton()
        elapsed = time.time() - self.startTransferTime
        message(' Host:  finished in %.1f seconds'%elapsed,'note')
