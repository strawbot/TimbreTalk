import sys
from PyQt4 import QtGui, QtCore


class QtStandalone:
    def __init__(self, mainfunction):
        app = QtGui.QApplication(sys.argv)
        alive = mainfunction()
        app.exec_()


class Widget(QtGui.QWidget):
    widgetSignal = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)

    def emitWidgetSignal(self):
        Widget.emitSignal(self)

    def emitSignal(self):
        self.widgetSignal.emit()


class Frame(QtGui.QFrame):
    frameSignal = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        QtGui.QFrame.__init__(self, parent)

    def emitFrameSignal(self):
        Frame.emitSignal(self)

    def emitSignal(self):
        self.frameSignal.emit()


class Child(Frame, Widget):
    widgetSignal = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super(Child, self).__init__(parent)

        self.frameSignal.connect(self.printframe)
        self.widgetSignal.connect(self.printwidget)

        self.emitFrameSignal()
        self.emitWidgetSignal()

    def printframe(self):
        print("frame")

    def printwidget(self):
        print("widget")


class QtStandalone:
    def __init__(self, mainfunction):
        app = QtGui.QApplication(sys.argv)
        alive = mainfunction()
        app.exec_()

def main():
    w = Child()
    w.show()
    return w


QtStandalone(main)