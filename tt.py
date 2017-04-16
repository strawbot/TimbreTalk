#!/usr/bin/env python

# GUI for serial transactions using Qt	Robert Chapman III	Sep 28, 2012

version = '2.0'

from pyqtapi2 import *
from pids import MAIN_HOST
import sfp

# update GUI from designer
from compileui import updateUi

updateUi('mainWindow')
updateUi('tabs')

from message import *
import qterm, serialPane, transferPane
import infopane
import utilitypane, pids

class sfpQt(QObject, sfp.sfpProtocol):
    source = Signal(object)

    def __init__(self):
        QObject.__init__(self)
        sfp.sfpProtocol.__init__(self)

    def sink(self, bytelist):
        self.rxBytes(bytelist)

    def newFrame(self):
        self.source.emit(self.txBytes())

    def newPacket(self):
        self.distributer()

    def error(self, code=0, string=""):
        self.result = code
        error(string)

    def warning(self, code=0, string=""):
        self.result = code
        warning(string)

    def note(self, code=0, string=""):
        self.result = code
        note(string)

    def dump(self, tag, bytebuffer):
        messageDump(tag, bytebuffer)


class timbreTalk(qterm.terminal):
    def __init__(self):
        qterm.terminal.__init__(self)
        self.protocol = sfpQt()
        self.whoto = self.whofrom = 0
        self.serialPane = serialPane.serialPane(self)
        transferPane.srecordPane(self)
        utilitypane.utilityPane(self)
        infopane.infoPane(self)
        self.listRoutes()

        # default
        self.whofrom = MAIN_HOST
        self.ui.whoFrom.setCurrentIndex(self.whofrom)
        QErrorMessage().qtHandler()

        # to handle warnings about tablets when running under a VM
        # http://stackoverflow.com/questions/25660597/hide-critical-pyqt-warning-when-clicking-a-checkboc
        def handler(msg_type, msg_string):
            pass

        qInstallMsgHandler(handler)

    # overrides
    def UiAdjust(self):
        # tab defines
        # tab defines
        SerialTab, \
        SrecordTab, \
        ReleaseTab, \
        TestTab, \
        PhraseTab = range(5)
        # adjustments for terminal app
        self.ui.Controls.setCurrentIndex(SerialTab)

    def banner(self):
        self.setWindowTitle('Timbre Talk ' + version)

    def connectPort(self):
        self.serialPane.connectPort()

    def disconnectPort(self):
        self.serialPane.disconnectFlows()

    # Routing
    def listRoutes(self):
        points = ['Direct']
        d = pids.whoDict  # use simpler name for comprehension
        points += [k for k in sorted(d, key=d.get) if d[k]][:-1]  # skip 0's and last point
        self.ui.whoTo.clear()
        self.ui.whoTo.insertItems(0, points)
        self.ui.whoFrom.clear()
        self.ui.whoFrom.insertItems(0, points)
        self.ui.whoTo.activated.connect(self.selectWhoTo)
        self.ui.whoFrom.activated.connect(self.selectWhoFrom)

    def selectWhoTo(self, index):
        self.whoto = index
        note('changed target to ' + self.ui.whoTo.currentText())

    def selectWhoFrom(self, index):
        self.whofrom = index
        note('changed source to ' + self.ui.whoFrom.currentText())

    def who(self):  # return latest who list
        return [self.whoto, self.whofrom]


if __name__ == "__main__":
    import sys, traceback

    app = QApplication([])
    try:
        timbreTalk = timbreTalk()
        sys.exit(app.exec_())
    except Exception as e:
        print(e)
        traceback.print_exc(file=sys.stderr)
    timbreTalk.close()
