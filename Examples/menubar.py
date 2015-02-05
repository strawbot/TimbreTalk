import sys
from PyQt4 import QtGui, QtCore

app = QtGui.QApplication(sys.argv)
main = QtGui.QMainWindow()
menubar = QtGui.QMenuBar()

menus = []
submenus = {}
for x in range(10):
    # top menus
    menu = QtGui.QMenu('Top %d' % x)
    menus.append(menu)

    # set direction
    menu.setLayoutDirection(QtCore.Qt.RightToLeft)

    # add to menubar
    menubar.addMenu(menu)

    for y in range(5):
        # a sub-menu
        submenu = QtGui.QMenu('Level 1 - %d' % y)

        # some dummy actions
        submenu.addAction('Level 2 - 1')
        submenu.addAction('Level 2 - 2')

        # keep reference
        submenus[(x,y)] = submenu
        # add to the top menu
        menu.addMenu(submenu)

main.setMenuBar(menubar)
main.show()

sys.exit(app.exec_())
