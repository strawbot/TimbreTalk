from PyQt4.QtCore import QEvent, Qt
from PyQt4.QtGui import QTableWidget, QWidget, QVBoxLayout, QApplication


class MyTableWidget(QTableWidget):
    def __init__(self):
        QTableWidget.__init__(self)

        self.keys = [Qt.Key_Left,
                     Qt.Key_Right]

        # We need this to allow navigating without editing
        self.catch = False 

    def focusInEvent(self, event):
        self.catch = False
        return QTableWidget.focusInEvent(self, event)

    def focusOutEvent(self, event):
        self.catch = True
        return QTableWidget.focusOutEvent(self, event)    

    def event(self, event):
        if self.catch and event.type() == QEvent.KeyRelease and event.key() in self.keys:
            self._moveCursor(event.key())

        return QTableWidget.event(self, event)

    def keyPressEvent(self, event):
        if not self.catch:
            return QTableWidget.keyPressEvent(self, event)

        self._moveCursor(event.key())


    def _moveCursor(self, key):
        row = self.currentRow()
        col = self.currentColumn()

        if key == Qt.Key_Left and col > 0:
            col -= 1

        elif key == Qt.Key_Right and col < self.columnCount():
            col += 1

        elif key == Qt.Key_Up and row > 0:
            row -= 1

        elif key == Qt.Key_Down and row < self.rowCount():
            row += 1

        else:
            return

        self.setCurrentCell(row, col)
        self.edit(self.currentIndex())


class Widget(QWidget): 
    def __init__(self, parent=None): 
        QWidget.__init__(self)            
        tableWidget = MyTableWidget()
        tableWidget.setRowCount(10)
        tableWidget.setColumnCount(10)

        layout = QVBoxLayout() 
        layout.addWidget(tableWidget)  
        self.setLayout(layout) 

app = QApplication([]) 
widget = Widget() 
widget.show() 
app.exec_()