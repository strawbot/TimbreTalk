import sys

if 'PyQt5' in sys.modules:
    # PyQt5
    from PyQt5 import QtGui, QtWidgets, QtCore
    from PyQt5.QtCore import pyqtSignal, pyqtSlot

else:
    sys.exit(1)
    # PySide2
    from PySide2 import QtGui as QtGui, QtWidgets as QtWidgets, QtCore as QtCore
    from PySide2.QtCore import Signal, Slot
