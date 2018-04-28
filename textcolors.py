# demo windows for all common text colors  Robert Chapman III  May 12, 2015

#from PyQt4 import QtCore, QtGui
from pyqtapi2 import *

try:
	_fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
	_fromUtf8 = lambda s: s

class Ui_MainWindow(object):
	def setupUi(self, MainWindow):
		MainWindow.setObjectName(_fromUtf8("MainWindow"))
		MainWindow.resize(640, 480)
		self.centralwidget = QWidget(MainWindow)
		self.centralwidget.setObjectName(_fromUtf8("centralwidget"))
		self.blackbg = QPlainTextEdit(self.centralwidget)
		self.blackbg.setGeometry(QRect(330, 10, 301, 421))
		self.blackbg.setStyleSheet(_fromUtf8("background-color: rgb(0, 0, 0);"))
		self.blackbg.setObjectName(_fromUtf8("blackbg"))
		self.whitebg = QPlainTextEdit(self.centralwidget)
		self.whitebg.setGeometry(QRect(10, 10, 301, 421))
		self.whitebg.setObjectName(_fromUtf8("whitebg"))
		MainWindow.setCentralWidget(self.centralwidget)
		font = QFont()
		if sys.platform[:5] == 'linux':
			font.setFamily(_fromUtf8("Andale Mono"))
		else:
			font.setFamily(_fromUtf8("Courier"))
		font.setPointSize(12)
		font.setItalic(False)
		font.setKerning(False)
		self.blackbg.setFont(font)
		self.whitebg.setFont(font)

		def text(pane, color):
			f = pane.currentCharFormat()
			f.setForeground(QColor(color))
			pane.setCurrentCharFormat(f)
			pane.appendPlainText('\nSample Color: '+color)

		for color in QColor.colorNames():
			text(self.whitebg, color)
			text(self.blackbg, color)

if __name__ == "__main__":
	import sys
	app = QApplication(sys.argv)
	MainWindow = QMainWindow()
	ui = Ui_MainWindow()
	ui.setupUi(MainWindow)
	MainWindow.show()
	sys.exit(app.exec_())

