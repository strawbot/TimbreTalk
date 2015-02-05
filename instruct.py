#!/usr/bin/env python
# display/set Instruct parameters
import os.path
import sys
import re
from pymodbus.client.sync import ModbusSerialClient as ModbusClient

# allow setting of port or name from command line arguments of form: x=y
kwargs = dict(x.split('=', 1) for x in sys.argv[1:])

name = kwargs.get('name', '')
port = kwargs.get('port', '/dev/ttyACM0')

if not os.path.exists(port):
	print 'Error:',port,'is not available.'
	os._exit(1)

if os.path.exists('/dev/ttyACM1'):
	print "Warning: /dev/ttyACM1 is present and shouldn't be. Unplug and replug usb cable"
	os._exit(1)

client = ModbusClient(method='rtu', port=port, timeout=1, baudrate=57600)
client.connect()

try:
	if name: # set name as passed in
		name = name.ljust(10)[:10]
		namewords = map(lambda x: (ord(x[0])<<8)+ord(x[1]), re.findall('..',name))
		rq = client.write_registers(1024, namewords, unit=1)

	rr = client.read_input_registers(1024, 5, unit=1) # reg base, number, slave
	name = ''.join(map(lambda x: chr(x/256)+chr(x%256), rr.registers))

	print "Wellname:", name
	rr = client.read_input_registers(0, 8, unit=1)
	print "Serial#", (rr.registers[3]<<16) + rr.registers[4]
	print "Firmware: %x.%xr%03d"%(rr.registers[1]>>12, rr.registers[1]%0x1000, rr.registers[2])
	
except:
	print "No connection to Instruct."
	os._exit(1)

client.close()
