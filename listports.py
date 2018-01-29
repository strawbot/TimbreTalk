# list ports on platform  Rob Chapman  Jan 26, 2010

import sys

jlink = 'jlink-'

def module_exists(module_name):
    try:
        __import__(module_name)
    except ImportError:
        return False
    else:
        return True

def jlinkPorts():
    if not module_exists('pylink'):
        return []

    import pylink
    return [jlink+str(p.SerialNumber) for p in pylink.JLink().connected_emulators()]

def listports():
	ports = []
	if sys.platform == 'win32':
		# port lister for windows
		# http://eli.thegreenplace.net/2009/07/31/listing-all-serial-ports-on-windows-with-python/
		# modified to suit needs of the few if not the 1
		
		import _winreg as winreg
		import itertools
		
		""" Uses the Win32 registry to return an
			iterator of serial (COM) ports
			existing on this computer.
		"""
		path = 'HARDWARE\\DEVICEMAP\\SERIALCOMM'
		try:
			key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path)
		except WindowsError:
			return ports
	
		for i in itertools.count():
			try:
				val = winreg.EnumValue(key, i)
				ports.append(str(val[1]))
			except EnvironmentError:
				break
		
	elif sys.platform == 'darwin':
		import os, re

		prefix = '/dev/'
		usb = re.compile('cu.*(serial*|USA*)', re.IGNORECASE)
		ports = [prefix+p for p in os.listdir(prefix) if usb.search(p)]

	elif sys.platform[:5] == 'linux':
		import os, re
		
		prefix = '/dev/'
		usb = re.compile('ttyusb', re.IGNORECASE)
		acm = re.compile('ttyacm', re.IGNORECASE)
		ports = [p for p in os.listdir(prefix) if usb.search(p)]
		portsextra = [prefix+p for p in os.listdir(prefix) if acm.search(p)]
		ports.extend(portsextra)

	else:
		print >>sys.stderr, 'unknown system platform: %s'%sys.platform

	return ports + jlinkPorts()

if __name__ == '__main__':
	print >>sys.stderr, listports()  #enumerate_serial_ports()
