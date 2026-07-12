from PyQt5 import QtWidgets

class PortCombo(QtWidgets.QComboBox):
    def __init__(self, parent):
        QtWidgets.QComboBox.__init__(self, parent)
