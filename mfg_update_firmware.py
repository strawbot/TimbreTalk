#!/usr/bin/env python

import os
import subprocess
import sys
import getopt

failed = 0
mfgDir = ''
port = ''

def usage():
	print >>sys.stderr, 'mfg_update_firmware.py -p <serial_port> -f <firmare_directory>'

def parseArgs(argv):
	global port
	global mfgDir
	try:
		opts, args = getopt.getopt(argv,"hp:f:",["port=", "fw="])
	except getopt.GetoptError:
		usage()
		os._exit(1)
	
	for opt, arg in opts:
		if opt == '-h':
			print >>sys.stderr, 'mfg_update_firmware.py -p <serial_port>'
			os._exit(0)
		elif opt in ("-p", "--port"):
			port = arg
		elif opt in ("-f", "--fw"):
			mfgDir = arg

	if (not port) or (not mfgDir):
		usage()
		os._exit(1)

	print >>sys.stderr, "firmware directory {0}".format(mfgDir)
	print >>sys.stderr, "port {0}".format(port)

def updateFwFile(port, fileName, fileType, side):
	op = "file={0}".format(fileName)
	updateFw(port, op, fileType, side)

def updateFw(port, op, fileType, side):
	if not port:
		usage()
		os._exit(1)

	cmd = "./sdown.py port={0} {1} from=main type={2} side={3}".format(port, op, fileType, side)
	try:
		retcode = subprocess.call(cmd, shell=True)
		if retcode < 0:
			failed = 1
	    		print >>sys.stderr, "Child was terminated by signal", -retcode
			os._exit(1)
		elif retcode != 0:
			failed = 1
	    		print >>sys.stderr, "Child returned", retcode
			os._exit(1)

	except OSError as e:
		print >>sys.stderr, "Execution failed:", e
		os._exit(1)

if __name__ == "__main__":
	parseArgs(sys.argv[1:])
	
	updateFw(port, "recover=1000000000", "boot", "left")

	updateFwFile(port, "{0}/MAIN_BOOT.elf.S19".format(mfgDir), "boot", "left")

	for side in ("left", "right"):
		side = "left"
		updateFwFile(port, "{0}/Launcher.elf.S19".format(mfgDir), "launcher", side)
		updateFwFile(port, "{0}/MAIN_APP.elf.S19".format(mfgDir), "app", side)
		#updateFwFile(port, "{0}/IO_HIBOOT.elf.S19".format(mfgDir), "hiboot", side)
		#updateFwFile(port, "{0}/IO_APP.elf.S19".format(mfgDir), "ioapp", side)
		updateFwFile(port, "{0}/u-boot.imx.serial".format(mfgDir), "uboot", side)

	# Set to boot the left image.
	updateFw(port, "fwDbOp=setboot", "boot", "left")
	
	if failed:
		print >>sys.stderr, "Update failed"
		os._exit(-1)
	else:
		print >>sys.stderr, "Update passed"
		os._exit(0)

