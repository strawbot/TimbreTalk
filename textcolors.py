# demo windows for all common text colors  Robert Chapman III  May 12, 2015

from PyQt4 import QtCore, QtGui

try:
	_fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
	_fromUtf8 = lambda s: s

class Ui_MainWindow(object):
	def setupUi(self, MainWindow):
		MainWindow.setObjectName(_fromUtf8("MainWindow"))
		MainWindow.resize(640, 480)
		self.centralwidget = QtGui.QWidget(MainWindow)
		self.centralwidget.setObjectName(_fromUtf8("centralwidget"))
		self.blackbg = QtGui.QPlainTextEdit(self.centralwidget)
		self.blackbg.setGeometry(QtCore.QRect(330, 10, 301, 421))
		self.blackbg.setStyleSheet(_fromUtf8("background-color: rgb(0, 0, 0);"))
		self.blackbg.setObjectName(_fromUtf8("blackbg"))
		self.whitebg = QtGui.QPlainTextEdit(self.centralwidget)
		self.whitebg.setGeometry(QtCore.QRect(10, 10, 301, 421))
		self.whitebg.setObjectName(_fromUtf8("whitebg"))
		MainWindow.setCentralWidget(self.centralwidget)

		def text(pane, color):
			f = pane.currentCharFormat()
			f.setForeground(QtGui.QColor(color))
			pane.setCurrentCharFormat(f)
			pane.appendPlainText('\nSample Color: '+color)

		for color in QtGui.QColor.colorNames():
			text(self.whitebg, color)
			text(self.blackbg, color)

if __name__ == "__main__":
	import sys
	app = QtGui.QApplication(sys.argv)
	MainWindow = QtGui.QMainWindow()
	ui = Ui_MainWindow()
	ui.setupUi(MainWindow)
	MainWindow.show()
	sys.exit(app.exec_())

