from PyQt4 import QtGui

app = QtGui.QApplication([])

menu = QtGui.QMenu()

sub_menu = QtGui.QMenu("Sub Menu")

for i in ["a", "b", "c"]: #or your dict
    sub_menu.addAction(i) #it is just a regular QMenu

menu.addMenu(sub_menu)

menu.show()

app.exec_()