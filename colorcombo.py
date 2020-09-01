from qt import QtWidgets

class ColorCombo(QtWidgets.QComboBox):
    def __init__(self, parent):
        QtWidgets.QComboBox.__init__(self, parent)
