from unittest import TestCase

from sfp import sfpProtocol
from sfpErrors import *
from pids import MAX_FRAME_LENGTH
import pids

class sfpPlus(sfpProtocol):
    def newPacket(self):
        self.gotPacket = True

    def newFrame(self):
        self.gotFrame = True

sp = sfpPlus()

# build a test frame
payload =  list(range(50))
packet = [pids.MEMORY] + payload
length = 1 + len(packet) + 2
frame = [length, ~length&0xFF] + packet
sum = sumsum = 0
for byte in frame:
    sum += byte
    sumsum += sum
frame += [sum&0xFF, sumsum&0xFF]
reference = [0x07, 0xF8, 0x07, 0x00, 0x02, 0x6A, 0x72, 0x8C]
spsframe = [0x06, 0xF9, 0x82, 0x00, 0x01, 0x82, 0x89]

class TestSfpProtocol(TestCase):
    def setUp(self):
        sp.resetRx()
        sp.result = NO_ERROR
        sp.message = ""
        sp.VERBOSE = True
        sp.receivedPool.queue.clear()
        sp.transmitPool.queue.clear()
        sp.handler.clear()
        sp.gotFrame = False
        sp.gotPacket = False

    def test_rxBytes(self):
        self.assertEqual(sp.receivedPool.qsize(), 0)
        sp.rxBytes(frame)
        self.assertEqual(sp.receivedPool.qsize(), 1)
        sp.rxBytes(reference)
        self.assertEqual(sp.receivedPool.qsize(), 2)

    def test_hunting(self):
        self.assertFalse(sp.hunting())

        sp.frame.extend([0])
        self.assertTrue(sp.hunting())
        self.assertEqual(sp.result, LENGTH_IGNORE)
        self.assertEqual(sp.sfpState, sp.hunting)
        self.assertFalse(sp.hunting())

        sp.resetRx()
        sp.frame.extend([1])
        sp.hunting()
        self.assertEqual(sp.result, LENGTH_SHORT)
        self.assertEqual(sp.sfpState, sp.hunting)

        self.setUp()
        sp.frame.extend([MAX_FRAME_LENGTH])
        sp.hunting()
        self.assertEqual(sp.result, LENGTH_OK)
        self.assertEqual(sp.sfpState, sp.syncing)

        if 254 > MAX_FRAME_LENGTH:
            self.setUp()
            sp.frame.extend([254])
            sp.hunting()
            self.assertEqual(sp.result, LENGTH_LONG)
            self.assertEqual(sp.sfpState, sp.hunting)

    def test_syncing(self):
        sp.length = 100
        self.assertFalse(sp.syncing())
        self.assertEqual(sp.sfpState, sp.hunting)

        self.setUp()
        sp.frame.extend([sp.length])
        self.assertTrue(sp.syncing())
        self.assertEqual(sp.result, NOT_SYNCED)
        self.assertEqual(sp.sfpState, sp.hunting)

        self.setUp()
        sp.frame.extend([~sp.length&0xFF])
        self.assertTrue(sp.syncing())
        self.assertEqual(sp.result, FRAME_SYNCED)
        self.assertEqual(sp.sfpState, sp.receiving)

    def test_receiving(self):
        sp.length = frame[0]
        self.assertFalse(sp.receiving())

        sp.frame.extend(frame[1:-1] + [~frame[-1]&0xFF])
        self.assertTrue(sp.receiving())
        self.assertEqual(sp.result, BAD_CHECKSUM)

        self.setUp()
        sp.length = frame[0]
        sp.frame.extend(frame[1:])
        self.assertTrue(sp.receiving())
        self.assertEqual(sp.result, GOOD_FRAME)

        self.setUp()
        sp.length = spsframe[0]
        sp.frame.extend(spsframe[1:])
        self.assertTrue(sp.receiving())
        self.assertEqual(sp.result, IGNORE_FRAME)

    def test_resetRx(self):
        sp.sfpState = None
        sp.frame.extend([254])
        sp.resetRx()
        self.assertEqual(sp.sfpState, sp.hunting)
        self.assertEqual(len(sp.frame), 0)

    def test_initRx(self):
        sp.initRx()
        self.assertEqual(sp.result, RX_RESET)

    def test_checkLength(self):
        sp.length = 0
        self.assertEqual(sp.checkLength(), LENGTH_IGNORE)
        sp.length = 3
        self.assertEqual(sp.checkLength(), LENGTH_SHORT)
        sp.length = MAX_FRAME_LENGTH + 1
        self.assertEqual(sp.checkLength(), LENGTH_LONG)
        sp.length = MAX_FRAME_LENGTH
        self.assertEqual(sp.checkLength(), LENGTH_OK)

    def test_checkSync(self):
        sp.length =100
        for sync in range(256):
            if sync == ~sp.length&0xFF:
                self.assertTrue(sp.checkSync(sync))
            else:
                self.assertFalse(sp.checkSync(sync))

    def test_frameOk(self):
        sp.length = frame[0]
        sp.frame.extend(frame[1:])
        self.assertTrue(sp.frameOk())

    def test_checkSum(self):
        self.assertEqual(sp.checkSum(frame[:-2]), (frame[-2], frame[-1]))

    def test_setHandler(self):
        self.assertEqual(sp.handler.get(pids.MEMORY), None)
        sp.setHandler(pids.MEMORY, 1)
        self.assertEqual(sp.handler[pids.MEMORY], 1)

    def test_removeHandler(self):
        sp.setHandler(pids.MEMORY, 1)
        sp.removeHandler(pids.MEMORY)
        self.assertEqual(sp.handler.get(pids.MEMORY), None)

    def test_distributer(self):
        def handler(packet):
            self.assertEqual(packet, payload)
            self.handled = True
        sp.setHandler(pids.MEMORY, handler)

        self.handled = False
        sp.rxBytes(frame)
        sp.distributer()
        self.assertTrue(self.handled)
        self.assertEqual(sp.result, GOOD_FRAME)
        self.assertEqual(sp.gotPacket, True)

        self.setUp()
        self.handled = False
        sp.rxBytes(spsframe)
        sp.distributer()
        self.assertFalse(self.handled)
        self.assertEqual(sp.result, IGNORE_FRAME)
        self.assertEqual(sp.gotPacket, False)

    def test_sendNPS(self):
        sp.sendNPS(pids.MEMORY, packet[1:])
        self.assertEqual(sp.transmitPool.qsize(), 1)
        self.assertEqual(sp.transmitPool.get(), frame)
        self.assertEqual(sp.gotFrame, True)

    def test_txBytes(self):
        sp.sendNPS(pids.MEMORY, packet[1:])
        self.assertEqual(sp.txBytes(), frame)