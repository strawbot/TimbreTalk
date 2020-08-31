import sys

if 'PyQt5' in sys.modules:
    # PyQt5
    from PyQt5 import QtGui as QtGui
    from PyQt5 import QtWidgets as QtWidgets
    from PyQt5 import QtCore as QtCore
    from PyQt5.QtCore import pyqtSignal as Signal, pyqtSlot as Slot

else:
    sys.exit(1)
    # PySide2
    from PySide2 import QtGui as QtGui, QtWidgets as QtWidgets, QtCore as QtCore
    from PySide2.QtCore import Signal, Slot
