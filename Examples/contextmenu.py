import sys
from PyQt4 import QtGui, QtCore

class MainForm(QtGui.QMainWindow):
	def __init__(self, parent=None):
		super(MainForm, self).__init__(parent)

		# create button
		self.button = QtGui.QPushButton("test button", self)	   
		self.button.resize(100, 30)

		# set button context menu policy
		self.button.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
		self.connect(self.button, QtCore.SIGNAL('customContextMenuRequested(const QPoint&)'), self.on_context_menu)

		# create context menu
		self.popMenu = QtGui.QMenu(self)
		self.popMenu.addAction(QtGui.QAction('test0', self))
		self.popMenu.addAction(QtGui.QAction('test1', self))
		self.popMenu.addSeparator()
		self.popMenu.addAction(QtGui.QAction('test2', self))		

		self.sub_menu = QtGui.QMenu("Sub Menu")
		for i in ["a", "b", "c"]: #or your dict
			self.sub_menu.addAction(i) #it is just a regular QMenu
		self.popMenu.addMenu(self.sub_menu)

	def on_context_menu(self, point):
		# show context menu
		self.popMenu.exec_(self.button.mapToGlobal(point))		  

def main():
	app = QtGui.QApplication(sys.argv)
	form = MainForm()
	form.show()
	app.exec_()

if __name__ == '__main__':
    main()

