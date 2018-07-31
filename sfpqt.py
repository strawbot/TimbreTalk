# Qt wrapper around sfp

from protocols import sfp
from message import *
from interface import Layer

class sfpQt (Layer, sfp.sfpProtocol):
    def __init__(self):
        Layer.__init__(self, 'sfpQt')
        sfp.sfpProtocol.__init__(self)
        self.lower.send_data = self.send_data
        self.upper.send_data = self.talkOut

    def send_data(self, bytes):
        self.rxBytes(map(ord, bytes))

    def newFrame(self):
        data = ''.join(map(chr, self.txBytes()))
        self.lower.output.emit(data)

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


if __name__ == '__main__':
    from serialPort import SerialPortal
    from portal import *
    import sys
    from protocols import pids

    class app(QApplication):
        def __init__(self):
            QApplication.__init__(self, [])
            self.timer = QTimer()
            self.timer.timeout.connect(self.test)
            self.timer.start(0)

        def didopen(self):
            print("port '{}' at address '{}' is open".format(self.port.name, self.port.address))

        def didclose(self):
            print("port '{}' closed".format(self.port.name))

        def send_data(self, data):
            print("Rx'd:[{}]".format(data))

        def talkPacket(self, packet):  # handle text packets
            data = ''.join(map(chr, packet[2:]))
            self.layer.upper.output.emit(data)

        def test(self):
            try:
                self.portal = SerialPortal()
                self.port = self.portal.get_port('/dev/cu.usbserial-FT9S9VC1')
                self.layer = sfpQt()
                self.app = Interface('test')

                self.app.plugin(self.layer.upper)
                self.layer.lower.plugin(self.port)

                self.app.send_data = self.send_data
                self.layer.upper.send_data = self.layer.send_text
                self.layer.lower.send_data = self.layer.rxBytes
                self.port.opened.connect(self.didopen)
                self.port.closed.connect(self.didclose)
                self.layer.setHandler(pids.TALK_OUT, self.talkPacket)

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
