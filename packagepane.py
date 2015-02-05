# panel for working with packages  Robert Chapman III  Jul 4, 2013

from pyqtapi2 import *
import packagedatabase
import sys, traceback	

printme = 0

class packagePane(QWidget):
	def __init__(self, parent):
		QWidget.__init__(self, parent)
		self.parent = parent
		self.ui = parent.ui
		self.fdb = packagedatabase.firmwareDatabase(parent)
		
		self.fdb.fdbupdate.connect(self.displayVersions)
		self.ui.Refresh.clicked.connect(self.fdb.readFirmwareDatabase)
		self.ui.Rebuild.clicked.connect(self.fdb.rebuildDatabase)

# GUI
	def displayVersions(self):
		try:
			if printme: print >>sys.stderr, 'magic: 0x%X'%self.fdb.magic
			if printme: print >>sys.stderr, 'checksum: 0x%X'%self.fdb.checksum
			if printme: print >>sys.stderr, 'size: %d'%self.fdb.size

			self.ui.magicStatus.setText(self.fdb.magicStatus())
			self.ui.checksumStatus.setText(self.fdb.checksumStatus())
			
			self.ui.runningChoiceStatus.setText(self.fdb.runningChoice())
			self.ui.pendingChoiceStatus.setText(self.fdb.pendingChoice())

			table = self.ui.PackageTable
			table.item(0,0).setText(self.fdb.version(self.fdb.packageLeft))
			table.item(0,1).setText(self.fdb.version(self.fdb.packageRight))
			table.item(1,0).setText(self.fdb.version(self.fdb.launcherLeft))
			table.item(1,1).setText(self.fdb.version(self.fdb.launcherRight))
			table.item(2,0).setText(self.fdb.version(self.fdb.mainappLeft))
			table.item(2,1).setText(self.fdb.version(self.fdb.mainappRight))
			table.item(3,0).setText(self.fdb.version(self.fdb.ubootLeft))
			table.item(3,1).setText(self.fdb.version(self.fdb.ubootRight))
			table.item(4,0).setText(self.fdb.version(self.fdb.linuxLeft))
			table.item(4,1).setText(self.fdb.version(self.fdb.linuxRight))
			table.item(5,0).setText(self.fdb.version(self.fdb.displayappLeft))
			table.item(5,1).setText(self.fdb.version(self.fdb.displayappRight))
			table.item(6,0).setText(self.fdb.version(self.fdb.ioappLeft))
			table.item(6,1).setText(self.fdb.version(self.fdb.ioappRight))
			table.item(7,0).setText(self.fdb.version(self.fdb.swbappLeft))
			table.item(7,1).setText(self.fdb.version(self.fdb.swbappRight))
		
			self.ui.MainbootTable.item(0,0).setText(self.fdb.version(self.fdb.mainboot))

			table = self.ui.SlotTable		
			table.item(0,0).setText(self.fdb.slotType(self.fdb.slotaType))
			table.item(0,1).setText(self.fdb.version(self.fdb.slotaBoot))
			table.item(0,2).setText(self.fdb.version(self.fdb.slotaHiboot))
			table.item(0,3).setText(self.fdb.version(self.fdb.slotaApp))

			table.item(1,0).setText(self.fdb.slotType(self.fdb.slotbType))
			table.item(1,1).setText(self.fdb.version(self.fdb.slotbBoot))
			table.item(1,2).setText(self.fdb.version(self.fdb.slotbHiboot))
			table.item(1,3).setText(self.fdb.version(self.fdb.slotbApp))
		
			self.ui.DatabaseTable.item(0,0).setText(self.fdb.version(self.fdb.database))

		except Exception, e:
			print >>sys.stderr, e
			traceback.print_exc(file=sys.stderr)
