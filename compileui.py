# translate .ui into .py file if out of date

from PyQt5.uic import compileUi

import time, os

def fileModTime(file): # return file modified date
    try:
        return time.localtime(os.path.getmtime(file))
    except:
        return 0

def updateUi(qt): # input file root name to be updated
    mwui = qt+".ui"
    mwpy = qt+".py"
    if  fileModTime(mwpy) < fileModTime(mwui):
        file = open(mwpy, "w")
        compileUi(mwui, file, execute=True)
        file.close()

if __name__ == '__main__':
    updateUi('terminal')