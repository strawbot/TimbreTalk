# generic device and portal classes for TT to connect to  Robert Chapman  Jul 24, 2018

import threading
import time

class device(object):
    nodata = ''

    def __init__(self, address, name, port):
        self.address = address
        self.data = self.nodata
        self.name = name
        self.port = port
        self.timestamp = time.time()

    def last_timestamp(self):
        return self.timestamp

    def hold_data(self, data):
        self.data += data
        self.timestamp = time.time()

    def get_data(self):
        data = self.data
        self.data = self.nodata
        return data

    def send_data(self, data):
        self.port.send_data(self.address, data)


class portal(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.__devices = {}
        self.start()

    def devices(self):
        return self.__devices.values()

    def add_device(self, device):
        self.__devices[device.name] = device

    def remove_device(self, device):
        self.__devices.pop(device.name)

    def get_device(self, name):
        return self.__devices.get(name)
