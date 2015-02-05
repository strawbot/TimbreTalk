# event filters

class PostDialog(QtGui.QDialog):
    def __init__(self, parent=None):
        QtGui.QDialog.__init__(self, parent)
        self.ui = Ui_Dialog() #code from designer!!
        self.ui.setupUi(self)

        self.ui.plainTextEdit.installEventFilter(self)

    def eventFilter(self, event):
        if event.type() == QtCore.QEvent.KeyPress:
            # do some stuff ...
            return True # means stop event propagation
        else:
            return QtGui.QDialog.eventFilter(self, event)

