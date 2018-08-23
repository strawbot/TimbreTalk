# config file transfer  Robert Chapman III  May 10, 2017

from pyqtapi2 import *
from imageTransfer import imageTransfer
from transfer import *
from protocols import pids
from protocols.interface.message import *

class configTransfer(imageTransfer):

    def __init__(self, parent=0):
        imageTransfer.__init__(self, parent)
        self.protocol.setHandler(pids.FILES, self.transferResponse)
        self.transferPid = pids.FILES
        self.transferType = BINARY_TRANSFER
