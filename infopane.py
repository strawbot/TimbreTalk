# panel for working with packages  Robert Chapman III  Jul 4, 2013

from pyqtapi2 import *
import sys, traceback	

printme = 0

class infoPane(QWidget):
	def __init__(self, parent):
		QWidget.__init__(self, parent)
		self.parent = parent
		self.ui = parent.ui
