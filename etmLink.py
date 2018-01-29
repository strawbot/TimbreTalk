# Classes for dealing with data flow using an ETM link  Robert Chapman  Jan 29, 2018

# serial IO supported through memory interfaced to by J-Link device using ETM
# memory in RAM has a data structure of:
# etm id: 0xFACEDEAF
#  ->txq: points to micros byte transmit queue; must read from here
#  ->rxq: points to mciros byte receive queue; must write to here

class byteq(): #IRE
    def __init__(self, etm, a):
        self.q = a
        self.etm = etm
        self.e = self.etm.memory_read32(a+8,1)[0]

    def ir(self):
        self.i, self.r = self.etm.memory_read32(self.q, 2)

    def push(self,n):
        self.ir()
        self.etm.memory_write8(self.q + 12 + self.i, [n])
        if self.i:
            self.i -= 1
        else:
            self.i = self.e
        self.etm.memory_write32(self.q,[self.i])

    def pull(self):
        self.ir()
        n = self.etm.memory_read8(self.q + 12 + self.r, 1)[0]
        if self.r:
            self.r -= 1
        else:
            self.r = self.e
        self.etm.memory_write32(self.q + 4,[self.r])
        return n

    def notEmpty(self):
        self.ir()
        return self.i != self.r

    def query(self):
        self.ir()
        n = self.r - self.i
        if n < 0:
            n += self.e + 1
        return n

class etmLink():
    micro = 'EFM32GG980F1024'
    etmid = 0xFACEDEAF

    link = 0
    baudrate = 0
    timeout = 0

    def __init__(self, sn):
        import pylink
        self.link = pylink.JLink()
        self.link.open(sn)
        self.link.connect(etmLink.micro)

    def findEtm(self):
        n = 256
        for a in range(0x20000000, 0x20020000, n):
            for b in self.link.memory_read32(a,n):
                if b == etmLink.etmid:
                    self.inq, self.outq = [byteq(self.link, q) for q in self.link.memory_read32(a+4, 2)]
                    return True
                a += 4
        return False

    def read(self, n):
        s = []
        while n:
            n -= 1
            if self.inq.notEmpty():
                s.append(chr(self.inq.pull()))
            else:
                break
        return s

    def inWaiting(self):
        return self.inq.query()

    def write(self, s):
        for c in s:
            self.outq.push(ord(c))

    def isOpen(self):
        return self.link != None

    def close(self):
        if self.link:
            self.link.close()
            self.link = None