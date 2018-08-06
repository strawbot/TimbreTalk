import socket
from sfpLayer import SfpLayer, pids
from hub import Port
from interface import Interface, Layer
import traceback, sys
from threading import Thread
import time
from serialHub import SerialPort

sfp_udp_port = 1337
ip = '216.123.208.82'
udp_check = 2

class IpPort(Port):
    def open(self):
        Port.open(self)
        try:
            t = Thread(name=self.name, target=self.receiver)
            t.setDaemon(True)
            t.start()  # run port in thread
            self.wait(100)
        except Exception, e:
            print >> sys.stderr, e
            traceback.print_exc(file=sys.stderr)
            print('Unknown exception, not opening socket')
            Port.close(self)

    def close(self):
        Port.close(self)

    def receiver(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.sendto('', self.address) # initial send will bind to a socket and notify host
        self.sock.settimeout(udp_check)
        while self.is_open():
            try:
                data, address = self.sock.recvfrom(256)  # buffer size is 256 bytes
                self.output.emit(data)
            except socket.timeout:
                pass
            except Exception, e:
                print >> sys.stderr, e
                traceback.print_exc(file=sys.stderr)
                print('Unknown exception, quitting IpPort')
        self.sock.close()

    def send_data(self, data):
        if self.is_open():
            self.sock.sendto(data, self.address)
        else:
            print >> sys.stderr, "Error: can't send - socket is not open"


CONNECT = 'CONNECT'
EOF = '--EOF--Pattern--'
apn = "m2m-east.telus.iot"


class AtPort(Port):
    def __init__(self, name):
        Port.__init__(self)
        self.port = SerialPort(name)
        self.port.output.connect(self.receiveData)

    def at(self, cmd, expect="OK", timeout=1):
        self.reply = ''
        self.port.input.emit(cmd+'\r')
        self.port.port.timeout = timeout
        start = time.time()
        while time.time() - start < timeout:
            if expect in self.reply:
                return
        raise Exception("Unexpected reply {} for command {}".format(cmd, self.reply))

    def receiveData(self, data):
        self.reply += data

    def startup(self):
        '''startup sequence for cell modem:
        send: AT+CREG?  expect: +CREG: 1,1
        send: ATE0
        send: AT+KSREP=0
        send: AT+CREG=1
        send: AT+CGREG=0
        send: AT+CGDCONT=1,"IP","m2m-east.telus.iot"
        send: AT+CGATT? expect: +CGATT: 1
        send: AT&K3
        send: AT+KCNXCFG=1,"GPRS",m2m-east.telus.iot
        '''
        at = self.at
        at("AT+CREG?",  expect="+CREG: 1,1", timeout=20)
        at("ATE0")
        at("AT+KSREP=0")
        at("AT+CREG=1")
        at('AT+CGDCONT=1,"IP","{}"'.format(apn))
        at('AT+CGATT?', expect='+CGATT: 1')
        at('AT&K3')
        at('AT+KCNXCFG=1,"GPRS",{}'.format(apn))

    def udpOpen(self):
        '''UDP open sequence
        send: AT+KCNXTIMER=1,60,1,60
        send: AT+KUDPCFG=1,0  expect: +KUDP_IND: sid
        '''
        self.startup()
        self.at('AT+KCNXTIMER=1,60,1,60')
        self.at('AT+KUDPCFG=1,0',  expect='+KUDP_IND: 1,1', timeout=5)
        reply = self.reply.splitlines()[-1]
        self.sid = reply.split(' ')[-1][0]

    def open(self):
        self.port.open()
        if self.port.is_open():
            self.udpOpen()

    def is_open(self):
        return self.port.is_open()

    def send_data(self, data):
        '''send sequence
        send: AT+KUDPSND=sid,destip,destport,size  expect: CONNECT
        send: data
        send: EOF
        '''
        self.at('AT+KUDPSND={},{},{},{}'.format(self.sid, ip, sfp_udp_port,len(data)),
                expect=CONNECT, timeout=5)
        self.port.input.emit(data)
        self.port.input.emit(EOF)

    def recUdp(self):
        '''receive sequence
        expect: +KUDP_RCV:
        send: AT+KUDPRCV=sid,size  expect: CONNECT
        expect: data
        expect: EOF
        '''
        self.at('', expect='+KUDP_RCV:', timeout=5)
        size = self.reply.split(',')[-1]
        self.at('AT+KUDPRCV={},{}'.format(self.sid, size), expect=EOF)

    def closeUdp(self):
        '''UDP close sequence
        send: AT+KUDPCLOSE=sid
        '''
        self.at('AT+KUDPCLOSE={}'.format(self.sid))


class DeviceSimulator(object):
    def __init__(self, port=None):
        self.top = Interface('DeviceSimulator')
        self.sfp = SfpLayer()
        if port:
            self.bottom = AtPort('/dev/cu.usbserial-FT9S9VC1')
        else:
            self.bottom = IpPort((ip, sfp_udp_port), 'SfpLayer')

        self.top.plugin(self.sfp.upper)
        self.sfp.lower.plugin(self.bottom)
        self.top.input.connect(self.cli)

        self.sfp.setHandler(pids.TALK_IN, self.talkInHandler)

        self.bottom.open()

        # run keep aliver in thread
        Thread(name='DeviceSimulator', target=self.keepalive).start()

    def talkInHandler(self, packet):
        self.sfp.upper.output.emit(packet[2:])

    def sendHelo(self):
        self.bottom.send_data('helo')

    def keepalive(self):
        while self.bottom.is_open():
            self.bottom.send_data(' ')
            time.sleep(5)

    def cli(self, data):
        text = ''.join(map(chr, data))
        if 'exit' in text:
            self.bottom.close()
        else:
            print(text)
            self.sfp.sendNPS(pids.TALK_OUT, [self.sfp.whoto, self.sfp.whofrom]+map(ord,'\ndevsim: '))


d = DeviceSimulator("/dev/cu.usbserial-FT9S9VC1")
