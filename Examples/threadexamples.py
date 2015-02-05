# from: http://stackoverflow.com/questions/6783194/background-thread-with-qthread-in-pyqt
from PyQt4 import QtCore
import time
import sys


# Subclassing QThread
# http://doc.qt.nokia.com/latest/qthread.html
class AThread(QtCore.QThread):

    def run(self):
        count = 0
        while count < 5:
            time.sleep(1)
            print "Increasing"
            count += 1

# Subclassing QObject and using moveToThread
# http://labs.qt.nokia.com/2007/07/05/qthreads-no-longer-abstract/
class SomeObject(QtCore.QObject):

    finished = QtCore.pyqtSignal()

    def longRunning(self):
        count = 0
        while count < 5:
            time.sleep(1)
            print "Increasing"
            count += 1
        self.finished.emit()

# Using a QRunnable
# http://doc.qt.nokia.com/latest/qthreadpool.html
# Note that a QRunnable isn't a subclass of QObject and therefore does
# not provide signals and slots.
class Runnable(QtCore.QRunnable):

    def run(self):
        count = 0
        app = QtCore.QCoreApplication.instance()
        while count < 5:
            print "Increasing"
            time.sleep(1)
            count += 1
        app.quit()


def usingQThread():
    app = QtCore.QCoreApplication([])
    thread = AThread()
    thread.finished.connect(app.exit)
    thread.start()
    sys.exit(app.exec_())

def usingMoveToThread():
    app = QtCore.QCoreApplication([])
    objThread = QtCore.QThread()
    obj = SomeObject()
    obj.moveToThread(objThread)
    obj.finished.connect(objThread.quit)
    objThread.started.connect(obj.longRunning)
    objThread.finished.connect(app.exit)
    objThread.start()
    sys.exit(app.exec_())

def usingQRunnable():
    app = QtCore.QCoreApplication([])
    runnable = Runnable()
    QtCore.QThreadPool.globalInstance().start(runnable)
    sys.exit(app.exec_())

if __name__ == "__main__":
    usingQThread()
    #usingMoveToThread()
    #usingQRunnable()