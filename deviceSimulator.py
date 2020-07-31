import socket
from sfpLayer import SfpLayer, pids
from interface import Interface, Layer, Port
import traceback, sys
from threading import Thread, Lock
import time
from serialHub import SerialPort
from Queue import Queue

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
        except Exception as e:
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
            except Exception as e:
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
rcv = "+KUDP_DATA: "

class AtPort(Layer):
    def __init__(self, name):
        Layer.__init__(self, 'AtPort')
        self.port = SerialPort(name)
        self.plugin(self.port)
        self.inner.input.connect(self.receive_data)
        self.input.connect(self.send_data)
        self.reply = ''
        self.dualStream = ''
        self.frameq = Queue()
        t = Thread(target=self.frameRunner)
        t.setDaemon(True)
        t.start()

    def at(self, cmd, expect="OK", timeout=2, retries=1):
        while retries >=0:
            self.reply = ''
            self.inner.output.emit(cmd + '\r')
            self.port.port.timeout = timeout
            if self.wait_for(expect, timeout):
                return
            retries -= 1
        raise Exception("Unexpected reply {} for command {}".format(cmd, self.reply))

    def wait_for(self, expect="OK", timeout=2):
        start = time.time()
        while time.time() - start < timeout:
            if expect in self.reply:
                return True
        return False

    def frameRunner(self):
        while True:
            frame = self.frameq.get()
            self.output.emit(frame)

    # +KUDP_DATA: 1,8,"216.123.208.82",1337,<7><f8><7><0><4><d><17>3<d><a>
    def split_reply_and_receive_streams(self):
        index = 0
        try:
            while index < len(self.dualStream):
                if self.dualStream[index] == rcv[index]:
                    index += 1
                    if index != len(rcv):
                        continue

                    if self.dualStream.count(',') < 4:
                        return

                    fields = self.dualStream.split(',', 4)
                    if len(fields) < 5:
                        return

                    length = int(fields[1])
                    if len(fields[4]) < length:
                        return

                    self.dualStream = fields[4][length:]
                    frame = fields[4][:length]
                    self.frameq.put(frame)
                else:
                    self.reply += self.dualStream[:1]
                    self.dualStream = self.dualStream[1:]
                index = 0
        except Exception as e:
            print >> sys.stderr, e
            traceback.print_exc(file=sys.stderr)
            print index
            print self.dualStream
            sys.exit(0)

    def receive_data(self, data):
        self.dualStream += data
        self.split_reply_and_receive_streams()

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
        at("AT+CREG?",  expect="+CREG: 1", timeout=2, retries=10)
        at("ATE0")
        at("AT+KSREP=0")
        at("AT+CREG=1")
        at('AT+CGDCONT=1,"IP","{}"'.format(apn))
        at('AT+CGATT?', expect='+CGATT: 1', retries=10)
        at('AT&K3')
        at('AT+KCNXCFG=1,"GPRS",{}'.format(apn))

    def udp_open(self):
        '''UDP open sequence
        send: AT+KCNXTIMER=1,60,1,60
        send: AT+KUDPCFG=1,0,,1  expect: +KUDP_IND: sid
        '''
        self.startup()
        self.at('AT+KCNXTIMER=1,60,1,60')
        self.at('AT+KUDPCFG=1,0,,1',  expect='+KUDP_IND: 1,1', timeout=5)
        reply = self.reply.splitlines()[-1]
        self.sid = reply.split(' ')[-1][0]

    def open(self):
        self.port.open()
        if self.port.is_open():
            self.udp_open()
        else:
            raise Exception("Failed to open port {}".format(self.port.name))

    def is_open(self):
        return self.port.is_open()

    def send_data(self, data):
        '''send sequence
        send: AT+KUDPSND=sid,destip,destport,size  expect: CONNECT
        send: data
        send: EOF  expect: OK
        '''
        self.at('AT+KUDPSND={},{},{},{}'.format(self.sid, ip, sfp_udp_port,len(data)),
                expect=CONNECT, timeout=5, retries=0)
        self.inner.output.emit(data)
        self.inner.output.emit(EOF)
        self.wait_for(timeout=5)

    def close_udp(self):
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

        self.top.plugin(self.sfp)
        self.sfp.plugin(self.bottom)
        self.top.input.connect(self.command)

        self.sfp.setHandler(pids.EVAL_PID, self.talkInHandler)

        self.bottom.open()

        # run keep aliver in thread
        self.connected = False
        t = Thread(name='DeviceSimulator', target=self.keepalive)
        t.setDaemon(True)
        t.start()

        # run CLI in thread
        self.commands = Queue()
        t = Thread(name='CLI', target=self.cli)
        t.setDaemon(True)
        t.start()
        t.join()

    def command(self, data):
        self.commands.put(data)

    def talkInHandler(self, packet):
        self.sfp.output.emit(packet[2:])

    def sendHelo(self):
        self.bottom.send_data('helo')

    def keepalive(self):
        while self.bottom.is_open():
            if self.connected:
                self.connected = False
            else:
                self.bottom.send_data(chr(0))
            time.sleep(5)

    def cli(self):
        while True:
            text = ''.join(map(chr, self.commands.get()))
            self.connected = True
            if 'exit' in text:
                self.bottom.close()
                sys.exit(0)
            else:
                self.sfp.sendNPS(pids.TALK_OUT, [self.sfp.whoto, self.sfp.whofrom]+map(ord,'devsim: '))


d = DeviceSimulator("/dev/cu.usbserial-FT9S9VC1")
# d = DeviceSimulator()
sys.exit(0)