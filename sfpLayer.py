#  wrapper around sfp

from protocols import sfp, pids
from message import *
from interface import Layer

class SfpLayer (Layer, sfp.sfpProtocol):
    def __init__(self):
        Layer.__init__(self, 'sfpLayer')
        sfp.sfpProtocol.__init__(self)
        self.lower.input.connect(self.send_data)
        self.upper.input.connect(self.talkOut)
        self.setHandler(pids.TALK_OUT, self.talkPacket)

    def send_data(self, bytes):
        self.rxBytes(map(ord, bytes))

    def newFrame(self):
        data = self.txBytes()
        string = ''.join(map(chr, data))
        self.lower.output.emit(string)

    def newBytes(self, data):
        self.rxBytes(map(ord, data))

    def newPacket(self):
        self.distributer()

    def error(self, code = 0, string = ""):
        self.result = code
        error(string)

    def warning(self, code = 0, string = ""):
        self.result = code
        warning(string)

    def note(self, code = 0, string = ""):
        self.result = code
        note(string)

    def dump(self, tag, buffer):
        messageDump(tag, buffer)

    def talkPacket(self, packet):  # handle text packets
        data = ''.join(map(chr, packet[2:]))
        self.upper.output.emit(data)


if __name__ == '__main__':
    from PyQt4.QtCore import QCoreApplication, QTimer
    from serialPort import SerialPortal
    from portal import *
    import sys
    from protocols import pids
    import traceback

    class app(QCoreApplication):
        def __init__(self):
            QCoreApplication.__init__(self, [])
            self.timer = QTimer()
            self.timer.timeout.connect(self.test)
            self.timer.start(0)

        def didopen(self):
            print("port '{}' at address '{}' is open".format(self.port.name, self.port.address))

        def didclose(self):
            print("port '{}' closed".format(self.port.name))

        def got_data(self, data):
            print("Rx'd:[{}]".format(data))

        def test(self):
            try:
                self.portal = SerialPortal()
                self.port = self.portal.get_port('/dev/cu.usbserial-FT9S9VC1')
                self.layer = SfpLayer()
                self.app = Interface('test')
                # build comm stack
                self.app.plugin(self.layer.upper)
                self.layer.lower.plugin(self.port)

                self.app.input.connect(self.got_data)
                self.layer.upper.input.connect(self.layer.send_text)
                self.layer.lower.input.connect(self.layer.newBytes)
                self.port.opened.connect(self.didopen)
                self.port.closed.connect(self.didclose)

                self.port.open()
                if self.port.is_open():
                    print("yes its open")
                else:
                    print("port not found")

                self.app.output.emit('\r')
                self.port.wait(1000)
                self.portal.close()
            except Exception, e:
                print >> sys.stderr, e
                traceback.print_exc(file=sys.stderr)
            finally:
                self.quit()

    sys.exit(app().exec_())
