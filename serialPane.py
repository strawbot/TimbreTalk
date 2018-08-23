# serial panel for qtran  Robert Chapman III  Oct 20, 2012

from pyqtapi2 import *
from protocols.interface.message import *
from protocols import pids
import sys, traceback	
from protocols.interface import jlinkHub

CRETURN = 0xD

class serialPane(QWidget):
    def __init__(self, parent):
        QWidget.__init__(self, parent)
        self.parent = parent
        self.protocol = parent.protocol
        self.ui = parent.ui

        self.portParametersMenu()

        # signals
        self.ui.SFP.clicked.connect(self.selectSfp)
        self.ui.Serial1.clicked.connect(self.selectSerial)
        self.ui.ATwifi.clicked.connect(self.selectAt)
        self.ui.Ping.clicked.connect(self.sendPing)
        self.ui.ResetRcvr.clicked.connect(self.resetRcvr)
        self.ui.ProtocolDump.stateChanged.connect(self.protocolDump)
        self.ui.sendHex.clicked.connect(self.sendHex)
        self.ui.ignoreUnknowns.stateChanged.connect(self.blockUnknownPackets)

        self.parent.talkPort.opened.connect(self.setParamButtonText)

        # setup
        self.ui.SFP.click()
        # self.protocol.setHandler(pids.TALK_OUT, self.talkPacket)
        self.protocol.send_data = self.talkSink

    def portParametersMenu(self):
        # menu for serial port parameters
        paramenu = QMenu(self)
        paramenu.addAction("N 8 1", lambda: self.setParam('N', 8, 1))
        paramenu.addAction("E 8 1", lambda: self.setParam('E', 8, 1))

        paritymenu = paramenu.addMenu('Parity')
        paritymenu.addAction('None', lambda: self.setParam('N',0,0))
        paritymenu.addAction('Even', lambda: self.setParam('E',0,0))
        paritymenu.addAction('Odd', lambda: self.setParam('O',0,0))

        bytesizemenu = paramenu.addMenu('Byte size')
        bytesizemenu.addAction('8', lambda: self.setParam(0,8,0))
        bytesizemenu.addAction('7', lambda: self.setParam(0,7,0))
        bytesizemenu.addAction('6', lambda: self.setParam(0,6,0))
        bytesizemenu.addAction('5', lambda: self.setParam(0,5,0))

        stopmenu = paramenu.addMenu('Stopbits')
        stopmenu.addAction('1', lambda: self.setParam(0,0,1))
        stopmenu.addAction('1.5', lambda: self.setParam(0,0,1.5))
        stopmenu.addAction('2', lambda: self.setParam(0,0,2))

        self.ui.toolButton.setMenu(paramenu)

        self.setParamButtonText()

    def setWhoFrom(self, host):
        for name, value in pids.whoDict.iteritems():
            if value == host:
                index = self.ui.whoFrom.findText(name)
                if index != -1:
                    self.ui.whoFrom.setCurrentIndex(index)
                break

    def setParamButtonText(self):
        ### TODO: Fix
        # if jlinkHub.isPort(str(self.ui.PortSelect.currentText())):
        #     self.setWhoFrom(pids.ETM_HOST)
        #     return

        self.setWhoFrom(pids.MAIN_HOST)
        return
        ### TODO: Fix
        sp = self.parent.talkPort
        if sp.stopbits == 1.5:
            self.ui.toolButton.setText("%s %i %0.1f"%(sp.parity,sp.bytesize,sp.stopbits))
        else:
            self.ui.toolButton.setText("%s %i %i"%(sp.parity,sp.bytesize,sp.stopbits))

    def setParam(self, parity, bytesize, stopbits):
        try:
            sp = self.parent.talkPort
            if parity: sp.parity = parity
            if bytesize: sp.bytesize = bytesize
            if stopbits: sp.stopbits = stopbits
            self.setParamButtonText()

            if sp.port:
                sp.port.parity = sp.parity
                sp.port.bytesize = sp.bytesize
                sp.port.stopbits = sp.stopbits
                note('Changed port settings to %s%d%d'%(sp.port.parity,sp.port.bytesize,sp.port.stopbits))
        except Exception, e:
            print >>sys.stderr, e
            traceback.print_exc(file=sys.stderr)
            error("can't set Params")

    def sendHex(self):
        try:
            self.parent.talkPort.input.emit(bytearray.fromhex(self.ui.hexNum.text()))
        except Exception, e:
            print >>sys.stderr, e
            traceback.print_exc(file=sys.stderr)
            error("can't set Params")

    def disconnectFlows(self):
        self.parent.lower.unplug()
        self.protocol.unplug()
        self.parent.talkPort.unplug()

    def connectPort(self):
        if self.ui.SFP.isChecked():
            self.selectSfp()
        elif self.ui.Serial1.isChecked():
            self.selectSerial()
        else:
            self.selectAt()

    def selectSerial(self):
        if not self.ui.Serial1.isChecked():
            note('changed to no-protocol serial')
        self.disconnectFlows()
        self.parent.plugin(self.parent.talkPort)
        if self.ui.LoopBack.isChecked():
            self.parent.talkPort.loopback()
        else:
            self.parent.talkPort.normal()

    def selectSfp(self):
        if not self.ui.SFP.isChecked():
            note('changed to SFP')
            self.resetRcvr()
        self.disconnectFlows()
        self.parent.lower.plugin(self.parent.protocol)
        self.parent.protocol.plugin(self.parent.talkPort)
        if self.ui.LoopBack.isChecked():
            self.parent.talkPort.loopback()

    def selectAt(self):
        if not self.ui.ATwifi.isChecked():
            note('changed to AT')
        self.disconnectFlows()
        self.parent.plugin(self.parent.protocol)
        self.parent.protocol.plugin(self.parent.talkPort)
        if self.ui.LoopBack.isChecked():
            self.parent.talkPort.loopback()
        self.parent.lower.output.connect(self.ATSink)

    def protocolDump(self, flag):
        self.protocol.VERBOSE = flag
        note('protocol dump ')

    # talk connections
    def talkPacket(self, packet): # handle text packets
        data = ''.join(map(chr, packet[2:]))
        self.parent.lower.input.emit(data)

    def talkSink(self, s): # have a text port
        s = str(s)
        if self.ui.InBuffered.isChecked():
            talkout = pids.EVAL_PID
            s = s.strip()
            payload = map(ord,s)+[CRETURN]
        else:
            talkout = pids.TALK_IN
            payload = map(ord,s)
        self.protocol.sendNPS(talkout, self.parent.who()+payload)

    def ATSink(self, s): # sent through as AT PID
        s = str(s)
        if self.ui.InBuffered.isChecked():
            s = s.strip()
            payload = map(ord,s)+[CRETURN]
        else:
            payload = map(ord,s)
        self.protocol.sendNPS(pids.AT_CMD, self.parent.who()+payload)

    def sendPing(self):
        self.protocol.sendNPS(pids.PING, [self.parent.whoto, self.parent.whofrom])

    def resetRcvr(self):
        try:
            self.protocol.initRx()
        except Exception, e:
            print >>sys.stderr, e
            traceback.print_exc(file=sys.stderr)
            error("can't reset receiver")

    def blockUnknownPackets(self, flag):
        self.protocol.displayUnknowns = not flag