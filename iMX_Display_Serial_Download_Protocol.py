#!/usr/bin/env python

#/*******************************************************************************
#*
#*  Copyright (C) 2012, AUGER Florent - All Rights Reserved
#*
#*  DESCRIPTION:
#*  This script helps to exercice the i.MX serial download protocol using a
#*  serial COM port.
#*
#*  The script is provided "as is" with no warranty, and can be freely modified,
#*  enhanced, customized, ...
#*  Please share the interresing improvements.
#*
#*******************************************************************************/
#/*******************************************************************************
#* 
#* Tyler Brandon - 2012
#*    Added functions: get_status, writeAddr, readAddr, writeFile, 
#*        configureDDRAndNAND and setBaud.
#*    Added options:
#        'configDDR' - configures DDR.
#*       'exec' - configures DDR, increases the baud rate from 115200 to 
#*                460800, and uploads a file to DDR memory.
#*******************************************************************************/


import serial
import time
import os.path
import sys
import commands

import serialspy as ss
#ss.outfile = ""
ss.outfile = "seriallog.txt" # set to empty for no logging

# function to display user's help
def user_help():
	script_name = 'iMX_Serial_Download_Protocol.py'
	print "--- That script uses the Serial Download Protocol commands"
	print "    to discuss with the i.MX ROM. ---"
	print "Usage help:"
	print "-1- Get status with:"
	print "  %s get_status" % script_name
	print "-2- Write a file to an address with:"
	print "  %s write_file mem_add file" % script_name
	print "  e.g. : %s write_file 0x78001B00 test.bin" % script_name
	print "-3- Write to a single address with:"
	print "  %s write_mem mem_add access_size data" % script_name
	print "  e.g. : %s write_mem 0x78001B00 -32 0x43" % script_name
	print "-4- Read from a start address with:"
	print "  %s read_mem mem_add access_size size_in_byte [output_file]" % script_name
	print "  e.g. : %s read_mem 0x78001B00 -32 4 out.txt\n" % script_name
	print "Note:\nsize_in_byte should be a multiple of the access_size."
	print "access_size can be 8-bit: -8, 16-bit: -16, 32-bit: -32"
	print "mem_add and data are expected in hexa format 0x1234"
	print "output_file is optional"

# function to send the command on port COM
# default response size is 4 bytes if none are specified
def runcmd(cmd,responselength=4):

	cmds = cmd.split()
	if len(cmds) != 16:
		print "Command format is incorrect!"
		return 'error'
	cmdstring = ''
	for cmd in cmds:
		cmdstring += chr(int(cmd,16))

	uart_port.write(cmdstring)
	ss.appendwrite(cmdstring)
	resp_var = uart_port.read(responselength)
	ss.appendread(resp_var)
	return resp_var

# function to retrieve and print the response on the COM port
def showanswer(resp_var):
	# print as a 32-bit word
	if len(resp_var)==4:
		# resp_var[::-1] parsed the list starting from the end
		#for c in resp_var[::-1]:
		for c in resp_var:
			print "%02X" % ord(c),
		print
	else:
	# print in byte view 
		print "Byte view:"
		for c in resp_var:
			print "%02X" % ord(c),
		print

# function to write the received data to a file
def writetofile(resp_var, o_file):
	# print as a 32-bit word
	if len(resp_var)==4:
		# resp_var[::-1] parsed the list starting from the end
		for c in resp_var[::-1]:
			print >> o_file,"%02X" % ord(c),
		print
	else:
	# print in byte view 
		for c in resp_var:
			print >> o_file,"%02X" % ord(c),"\n",
		print

# function to read data from serial port
def get_serial_data(length):
	# to do a loop with length larger than 4
	print "get_serial_data "+str(length)+"\n"
	resp_var = uart_port.read(length)
	ss.appendread(resp_var)
	return resp_var


# function to get the file size formatted to be sent by the serial port
# quite ugly way of doing this => might surely be smarter than this ;-)
def get_formated_hex(var):
	# create a list of the split hex version of the 32-bit integer
	# if integer is 0x12345678 => ['1','2','3','4','5','6','7','8']
	if type(var) == long:
		hex_list = list("%08X" % var)
	if type(var) == int:
		hex_list = list("%08X" % var)
	if type(var) == str:
		# in case the address is not 4bytes long => add '0's
		var_size = len(var)
		if var_size!=8:
			for i in range(8-var_size):
				var = "".join(['0',var])
		hex_list = list(var)
	# create bytes from 2 elements
	byte1 = "".join(hex_list[0:2]) # ['12']
	byte2 = "".join(hex_list[2:4]) # ['34']
	byte3 = "".join(hex_list[4:6]) # ['56']
	byte4 = "".join(hex_list[6:8]) # ['78']
	hex_fmt = " ".join([byte1,byte2,byte3,byte4]) #  # ['12 34 56 78']
	return hex_fmt

def writeAddr(hexAddrStr, hexValStr, wSize):
	if wSize == 32:
		access_size = WORD_SIZE
	if wSize == 16:
		access_size = HWORD_SIZE
	if wSize == 8:
		access_size = BYTE_SIZE
	if wSize == '':
		access_size = WORD_SIZE

	# provide an address like 0x12784596, and skip '0x' in the string chain
	mem_add = get_formated_hex(hexAddrStr[2:10])
	write_data = get_formated_hex(hexValStr[2:10])
	cmd_to_send = " ".join([WRITE_MEMORY,mem_add,access_size,'00 00 00 00',write_data,'00'])
	answer = runcmd(cmd_to_send)
	if answer == ACK_ENG or answer == ACK_PROD:
		print "Wrote addr %s with %s" % (hexAddrStr,hexValStr)
		# Clear the next 4 bytes.
		resp_var = uart_port.read(4)
		ss.appendread(resp_var)
	else:
		print "Failed to write addr %s with %s" % (hexAddrStr,hexValStr)

def readAddr(hexAddrStr, rSize, rCount):
	if rSize == 32:
		access_size = WORD_SIZE
	if rSize == 16:
		access_size = HWORD_SIZE
	if rSize == 8:
		access_size = BYTE_SIZE
	if rSize == '':
		access_size = WORD_SIZE
	
	transfer_size = get_formated_hex(int(rCount))

	# provide an address like 0x12784596, and skip '0x' in the string chain
	mem_add = get_formated_hex(hexAddrStr[2:10])
	cmd_to_send = " ".join([READ_MEMORY,mem_add,access_size,transfer_size,'00 00 00 00 00'])
	answer = runcmd(cmd_to_send)
	if answer == ACK_ENG or answer == ACK_PROD:
		print "read addr %s, num bytes %d" % (hexAddrStr, (rSize * rCount)>>3)
		rd_data = get_serial_data(int((rSize * rCount)>>3))
		showanswer(rd_data)
	else:
		print "Failed to read addr %s" % (hexAddrStr)
	

def configureDDRAndNAND():
	"""
	Configure the external memory controller to setup DDR
	"""
	# reference ddr_initialization
	 
	# Disable WDOG
	writeAddr("0x53f98000", "0x00000030", 16)
	
	
	# (system development user's guide)
	# Enable all clocks (they are disabled by ROM code) 
	writeAddr("0x53fd4068", "0xffffffff", 32)
	writeAddr("0x53fd406c", "0xffffffff", 32)
	writeAddr("0x53fd4070", "0xffffffff", 32)
	writeAddr("0x53fd4074", "0xffffffff", 32)
	writeAddr("0x53fd4078", "0xffffffff", 32)
	writeAddr("0x53fd407c", "0xffffffff", 32)
	writeAddr("0x53fd4080", "0xffffffff", 32)
	writeAddr("0x53fd4084", "0xffffffff", 32)
	
	# (system development user's guide)
	# DDR3 IOMUX configuration 
	#* Global pad control options */
	#IOMUXC_SW_PAD_CTL_GRP_DDRMODE_CTL for sDQS[3:0], 1=DDR2, 0=CMOS mode
	writeAddr("0x53fa86f4", "0x00000000", 32)
	#IOMUXC_SW_PAD_CTL_GRP_DDRMODE for D[31:0], 1=DDR2, 0=CMOS mode
	writeAddr("0x53fa8714", "0x00000000", 32)
	#IOMUXC_SW_PAD_CTL_GRP_DDRPKE
	writeAddr("0x53fa86fc", "0x00000000", 32)
	#IOMUXC_SW_PAD_CTL_GRP_DDR_TYPE - DDR_SEL=10
	writeAddr("0x53fa8724", "0x04000000", 32)
	#IOMUXC_SW_PAD_CTL_GRP_DDR_TYPE - DDR_SEL=00
	# writeAddr("0x53fa8724", "0x00000000", 32)
	# writeAddr("0x53fa8724", "0x02000000", 32)#IOMUXC_SW_PAD_CTL_GRP_DDR_TYPE - DDR_SEL=01
	# writeAddr("0x53fa8724", "0x06000000", 32)#IOMUXC_SW_PAD_CTL_GRP_DDR_TYPE - DDR_SEL=11
	#* Data bus byte lane pad drive strength control options */
	#IOMUXC_SW_PAD_CTL_GRP_B3DS
	writeAddr("0x53fa872c", "0x00300000", 32)
	#IOMUXC_SW_PAD_CTL_PAD_DRAM_DQM3
	writeAddr("0x53fa8554", "0x00300000", 32)
	#IOMUXC_SW_PAD_CTL_PAD_DRAM_SDQS3
	writeAddr("0x53fa8558", "0x00300040", 32)
	#IOMUXC_SW_PAD_CTL_GRP_B2DS
	writeAddr("0x53fa8728", "0x00300000", 32)
	#IOMUXC_SW_PAD_CTL_PAD_DRAM_DQM2
	writeAddr("0x53fa8560", "0x00300000", 32)
	#IOMUXC_SW_PAD_CTL_PAD_DRAM_SDQS2
	writeAddr("0x53fa8568", "0x00300040", 32)
	#IOMUXC_SW_PAD_CTL_GRP_B1DS
	writeAddr("0x53fa871c", "0x00300000", 32)
	#IOMUXC_SW_PAD_CTL_PAD_DRAM_DQM1
	writeAddr("0x53fa8594", "0x00300000", 32)
	#IOMUXC_SW_PAD_CTL_PAD_DRAM_SDQS1
	writeAddr("0x53fa8590", "0x00300040", 32)
	#IOMUXC_SW_PAD_CTL_GRP_B0DS
	writeAddr("0x53fa8718", "0x00300000", 32)
	#IOMUXC_SW_PAD_CTL_PAD_DRAM_DQM0
	writeAddr("0x53fa8584", "0x00300000", 32)
	#IOMUXC_SW_PAD_CTL_PAD_DRAM_SDQS0
	writeAddr("0x53fa857c", "0x00300040", 32)
	#* SDCLK pad drive strength control options */
	#IOMUXC_SW_PAD_CTL_PAD_DRAM_SDCLK_0
	writeAddr("0x53fa8578", "0x00300000", 32)
	#IOMUXC_SW_PAD_CTL_PAD_DRAM_SDCLK_1
	writeAddr("0x53fa8570", "0x00300000", 32)
	#* Control and addr bus pad drive strength control options */
	#IOMUXC_SW_PAD_CTL_PAD_DRAM_CAS
	writeAddr("0x53fa8574", "0x00300000", 32)
	#IOMUXC_SW_PAD_CTL_PAD_DRAM_RAS
	writeAddr("0x53fa8588", "0x00300000", 32)
	#IOMUXC_SW_PAD_CTL_GRP_ADDDS for DDR addr bus
	writeAddr("0x53fa86f0", "0x00300000", 32)
	#IOMUXC_SW_PAD_CTL_GRP_CTLDS for CSD0, CSD1, SDCKE0, SDCKE1, SDWE
	writeAddr("0x53fa8720", "0x00300000", 32)
	#IOMUXC_SW_PAD_CTL_PAD_DRAM_SDODT1
	writeAddr("0x53fa8564", "0x00300040", 32)
	#IOMUXC_SW_PAD_CTL_PAD_DRAM_SDODT0
	writeAddr("0x53fa8580", "0x00300040", 32)
	
	
	# Micron D9LGQ MT41J128M16HA-15E (external DDR controller registers after u-boot intialization)
	
	#                        0               4               8               C
	#0x63fd9000:	0xc3190000	0x0002002d	0x12273030	0x9f5152e3
	#0x63fd9010:	0xb68e8a63	0x01ff00db	0xc0001740*	0x00000000*
	#0x63fd9020:	0x00005800	0x00000000	0x00000000	0x000026d2
	#0x63fd9030:	0x009f0e21	0x00000000	0x00000000	0x00000000
	#0x63fd9040:	0x04b8abc3-	0x00000000-	0x00000000	0x00000000
	#0x63fd9050:	0x00000000	0x00000000	0x00022227	0x00000000
	#0x63fd9060:	0x00000000	0x00000000	0x00000000	0x00000000
	#0x63fd9070:	0x00000000	0x00000000	0x00000000	0x01370138/
	#0x63fd9080:	0x013b013c/	0x38393435-	0x35343535/	0x33323333-
	#0x63fd9090:	0x4d444c44/	0x49414841-	0x00000000	0x638f018f
	#0x63fd90a0:	0x00000000	0x00000000	0x00000000	0x00000000
	#0x63fd90b0:	0x00000000	0x00000000	0x00000000	0x00000000
	#0x63fd90c0:	0x00000000	0x00000000	0x00000000	0x00000000
	#0x63fd90d0:	0x3d400000-	0x00000000	0xffffffff-	0xffffffff-
	#0x63fd90e0:	0xffffffff-	0xffffffff-	0xffffffff-	0xffffffff-
	#0x63fd90f0:	0xffffffff-	0xffffffff-	0x00f40000*	0x00000000
	
	# Set bit 15 on ESDSCR
	writeAddr("0x63fd901c", "0x00008000", 32)
	
	# ESDCTL_ESDMISC - board setting (note there are some readonly fields; check manual) (same as SDUG)
	writeAddr("0x63FD9018", "0xc0001740", 32)
	
	# Configure registers ESDCTL_ESDCFG0, ESDCTL_ESDCFG1, ESDCTL_ESDCFG2 and ESDCTL_ESDOTC- timing parameters.
	# ESDCTL_ESDCFG0  
	writeAddr("0x63FD900C", "0x9f5152e3", 32)
	# ESDCTL_ESDCFG1  (0xB68E8B63 in system user's guide)
	writeAddr("0x63FD9010", "0xb68e8a63", 32)
	# ESDCTL_ESDCFG2 
	writeAddr("0x63FD9014", "0x01ff00db", 32)
	# ESDCTL_ESDOTC
	writeAddr("0x63FD9008", "0x12273030", 32)
	
	# ESDCTL_ESDOR - out of reset delays
	writeAddr("0x63FD9030", "0x009f0e21", 32)
	
	# ESDCTL_DGCTRL0 - DQS Gating control register0
	writeAddr("0x63FD907C", "0x01370138", 32)
	# ESDCTL_DGCTRL1 - DQS Gating control register1
	writeAddr("0x63FD9080", "0x013b013c", 32)
	
	# ESDCTL - control register (same as system development user guide)
	#writeAddr("0x63FD9000", "0xc3190000", 32) # iMX53 QSB: two chips, 14-bit row addr, 32-bit port
	#writeAddr("0x63FD9000", "0xc2180000", 32) # Display Card: two chip, 13-bit row addr, 16-bit port 
# for 128MB SDRAM
	writeAddr("0x63FD9000", "0x82180000", 32) # Display Card: one chip, 13-bit row addr, 16-bit port
# for 256MB SDRAM
#	writeAddr("0x63FD9000", "0x83180000", 32) # Display Card: one chip, 14-bit row addr, 16-bit port
	# ESDCTL_RDDLCT - PHY Read Delay Lines Configuration Register
	writeAddr("0x63FD9088", "0x35343535", 32)
	# ESDCTL_WRDLCTL - PHY Write Delay Lines Configuration Register
	writeAddr("0x63FD9090", "0x4d444c44", 32)
	
	# ESDCTL_MUR - PHY Measure Unit Register
	writeAddr("0x63FD90F8", "0x00000800", 32)
	
	
	# (SDUG)
	# Enable CSD0 and CSD1, row width = 14, column width = 10, burst length = 8, data width = 32bit
	# *writeAddr("0x63fd9000", "0xc3190000", 32)#Main control register
	# tRFC=64ck;tXS=68;tXP=3;tXPDLL=10;tFAW=15;CAS=6ck
	# *writeAddr("0x63fd900C", "0x555952E3", 32)#timing configuration Reg 0.
	# tRCD=6;tRP=6;tRC=21;tRAS=15;tRPA=1;tWR=6;tMRD=4;tCWL=5ck
	# *writeAddr("0x63fd9010", "0xb68e8b63", 32)#timing configuration Reg 1
	# tDLLK(tXSRD)=512 cycles; tRTP=4;tWTR=4;tRRD=4
	# *writeAddr("0x63fd9014", "0x01ff00db", 32)#timing configuration Reg 2
	#command delay (default)
	writeAddr("0x63fd902c", "0x000026d2", 32)
	#out of reset delays
	writeAddr("0x63fd9030", "0x009f0e21", 32)
	# Keep tAOFPD, tAONPD, tANPD, and tAXPD as default since they are bigger than calc values
	# *writeAddr("0x63fd9008", "0x12273030", 32)#ODT timings
	# tCKE=3; tCKSRX=5; tCKSRE=5
	#Power down control
	writeAddr("0x63fd9004", "0x0002002d", 32)
	
	
	# At this point the controller start counting the required time according to configuration
	# How do we wait for this?
	
	# ESDCTL_ESDSCR - REF, LMR (load mode register), PRE (precharge command)
	#   Check ips_xfr_wait for the completion of the command.
	# (DDR doc)
	#  6. Issue an MRS (LOAD MODE) command to MR2 with the applicable
	#     settings (provide LOW to BA2 and BA0 and HIGH to BA1).
	#  7. Issue an MRS command to MR3 with the applicable settings.
	#  8. Issue an MRS command to MR1 with the applicable settings, including enabling
	#     the DLL and configuring ODT.
	#  9. Issue an MRS command to MR0 with the applicable settings, including a DLL RE-
	#     SET command. tDLLK (512) cycles of clock input are required to lock the DLL.
	# 10. Issue a ZQCL command to calibrate RTT and RON values for the process voltage
	#     temperature (PVT). Prior to normal operation, tZQinit must be satisfied.
	# 11. When tDLLK and tZQinit have been satisfied, the DDR3 SDRAM will be ready for
	#     normal operation.
	
	# (SDUG)
	# CS0:
	#write mode reg MR2 with cs0
	writeAddr("0x63fd901c", "0x00008032", 32)
	# Full array self refresh
	# Rtt_WR disabled (no ODT at IO CMOS operation)
	# Manual self refresh
	# CWS=5
	#write mode reg MR3 with cs0 .
	writeAddr("0x63fd901c", "0x00008033", 32)
	#write mode reg MR1 with cs0. ODS=01: out buff= RZQ/7 
	writeAddr("0x63fd901c", "0x00028031", 32)
	# out impedance = RZQ/7
	# Rtt_nom disabled (no ODT at IO CMOS operation)
	# Aditive latency off
	# write leveling disabled
	# tdqs (differential?) disabled
	#write mode reg MR0 with cs0 , with dll_rst0
	# SDUG 0x092080b0 
	writeAddr("0x63fd901c", "0x052080b0", 32)
	#ZQ calibration with cs0 (A10 high indicates ZQ cal long ZQCL)
	writeAddr("0x63fd901c", "0x04008040", 32)
	
	# CS1:
	#write mode reg MR2 with cs1
	writeAddr("0x63fd901c", "0x0000803a", 32)
	#write mode reg MR3 with cs1
	writeAddr("0x63fd901c", "0x0000803b", 32)
	#write mode reg MR1 with cs1. ODS=01: out buff= RZQ/7
	writeAddr("0x63fd901c", "0x00028039", 32)
	#write mode reg MR0 with cs1
	# SDUG 0x09208138 
	writeAddr("0x63fd901c", "0x05208138", 32)
	#ZQ calibration with cs1 (A10 high indicates ZQ cal long ZQCL)
	writeAddr("0x63fd901c", "0x04008048", 32)
	#
	# *0x00001800 # Refresh control register
	writeAddr("0x63fd9020", "0x00005800", 32)
	# ZQ HW control
	writeAddr("0x63fd9040", "0x04b80003", 32)
	# ODT control register
	writeAddr("0x63fd9058", "0x00022227", 32)
	writeAddr("0x63fd901c", "0x00000000", 32)
	# CLKO muxing (comment out for now till needed to avoid conflicts with intended usage of signals)
	#writeAddr("0x53FA8314", "0", 32)
	#writeAddr("0x53FA8320", "0x4", 32)
	#writeAddr("0x53FD4060", "0x01e900f0", 32)

	# NAND
	writeAddr("0x63FDB000", "0x00000080", 32)
	writeAddr("0x63FDB024", "0x70209d3d", 32)
	writeAddr("0x63FDB028", "0x001a8608", 32)
	writeAddr("0x63FDB034", "0x00000000", 32)

	# LEDs
	
	## LED4 - GPIO1_5 ALT1 - Temperature LED.
	## IOMUXC_SW_MUX_CTL_PAD_GPIO_5
	#writeAddr("0x53FA8330", "0x00000001", 32)
	## IOMUXC_SW_PAD_CTL_PAD_GPIO_5
	##writeAddr(
	#
	## LED5 - GPIO1_7 ALT1
	##writeAddr("0x53FA8334", "0x00000001", 32)
	#
	## LED6 - GPIO1_8 ALT1
	##writeAddr("0x53FA8338", "0x00000001", 32)
	#
	## Set data direction - set bits 5, 7 and 8 as outputs.
	##writeAddr("0x53F84004", "0x000001a0", 32)
	#writeAddr("0x53F84004", "0x00000020", 32)
	## GPIO-1_DR - Data to output.
	## Write bits 5 7 and 8 to one - This should turn off the LEDs.
	##writeAddr("0x53F84000", "0x000001a0", 32)
	#writeAddr("0x53F84000", "0x00000020", 32)

def getStatus():
	cmd_to_send = " ".join([GET_STATUS,'00 00 00 00 00 00 00 00 00 00 00 00 00 00'])
	# print cmd_to_send	# for debug
	answer = runcmd(cmd_to_send)
	print 'Status is:'
	showanswer(answer)
	return answer

def setBaud(baud, remote=True):
	global uart_port
#	readAddr("0x53FBC080", 32, 1)
#	readAddr("0x53FBC084", 32, 1)
#	readAddr("0x53FBC088", 32, 1)
#	readAddr("0x53FBC08C", 32, 1)
	readAddr("0x53FBC090", 32, 1)
	readAddr("0x53FBC0A4", 32, 1)
	readAddr("0x53FBC0A8", 32, 1)
	readAddr("0x53FBC0B0", 32, 1)

	if remote == True:
		# UFCR
		if baud == 115200:
#			writeAddr("0x53FBC090", "0x00000901", 32)
			writeAddr("0x53FBC0A4", "0x00000FA0", 32) # UBIR 1st
			writeAddr("0x53FBC0A8", "0x00002DCA", 32) # UMBR 2nd
		elif baud == 230400:
#			writeAddr("0x53FBC090", "0x00000A01", 32)
			writeAddr("0x53FBC0A4", "0x00000FA0", 32) # UBIR 1st
			writeAddr("0x53FBC0A8", "0x000016E4", 32) # UMBR 2nd
		elif baud == 460800:
#			writeAddr("0x53FBC090", "0x00000A81", 32)
			writeAddr("0x53FBC0A4", "0x00000FA0", 32) # UBIR 1st
			writeAddr("0x53FBC0A8", "0x00000B72", 32) # UMBR 2nd
		elif baud == 57600:
			writeAddr("0x53FBC0A4", "0x00000FA0", 32) # UBIR 1st
			writeAddr("0x53FBC0A8", "0x00005B95", 32) # UMBR 2nd
		elif baud == 1000000:
			writeAddr("0x53FBC090", "0x00000A81", 32) # div by 1
			uart_port.close()
			uart_port.baudrate = 460800
			uart_port.open()
			getStatus()
			readAddr("0x53FBC0A4", 32, 1)
			readAddr("0x53FBC0A8", 32, 1)
			writeAddr("0x53FBC0A4", "0x00001000", 32) # UBIR 1st
			writeAddr("0x53FBC0A8", "0x0000159A", 32) # UMBR 2nd
			uart_port.close()
			uart_port.baudrate = baud
			uart_port.open()
			print "uart port: "+str(uart_port)+"\n"
			return
		else:
			"ERROR baud "+str(baud)+" not supported\n"
			baud = 115200
			writeAddr("0x53FBC090", "0x00000901", 32)

	print "uart port: "+str(uart_port)+"\n"
	#uart_port.flush()
	uart_port.close()
	uart_port.baudrate = baud
	uart_port.open()
#	uart_port.setBaudrate(baud)
	print "uart port: "+str(uart_port)+"\n"
	#print "uart port read: "+str(uart_port.read(100))+"\n"
	
def writeFile(addrHexStr, fileName):
	"""
	Load a file into memory
	addr -- address to load file to.
	fileName -- path to file to load.
	"""
	infile = open(fileName,'rb')
	# get file size with 2 methods
	#print "size: %d" % os.stat(sys.argv[3]).st_size
	#print "size: %d" % os.path.getsize(sys.argv[3])
	f_size_int = os.path.getsize(fileName)
	f_size_hex = get_formated_hex(f_size_int)

	# provide an address like 0x12784596, and skip '0x' in the string chain
	mem_add = get_formated_hex(addrHexStr[2:10])

	cmd_to_send = " ".join([WRITE_FILE,mem_add,'00',f_size_hex,'00 00 00 00',APPS_TYPE])
	answer = runcmd(cmd_to_send)
	if answer == ACK_ENG or answer == ACK_PROD:
		while True:
			tx_data = infile.read(f_size_int)
			print "sending %d bytes \n" % (f_size_int)
			if not tx_data:
				break
			uart_port.write(tx_data)
			ss.appendwrite(tx_data)
	else:
		print "No acknowledge => can't transfer file"
	infile.close()

def verifyFile(addrHexStr, fileName):
	# Verify the contents of memory 
	access_size = WORD_SIZE

	f_size_int = os.path.getsize(fileName)
	f_size_hex = get_formated_hex(f_size_int)

	# provide an address like 0x12784596, and skip '0x' in the string chain
	mem_add = get_formated_hex(addrHexStr[2:10])
	cmd_to_send = " ".join([READ_MEMORY,mem_add,access_size,f_size_hex,'00 00 00 00 00'])
	answer = runcmd(cmd_to_send)
	if answer == ACK_ENG or answer == ACK_PROD:
		# to read the data from serial port
		rd_data = get_serial_data(f_size_int)
		outfile = open(fileName+".mem_read",'wb')
		outfile.write(rd_data)
		outfile.close()
		
		rtn = commands.getstatusoutput("diff "+fileName+" "+fileName+".mem_read")
		if rtn[0] == 0:
			print "Verified "+fileName+" properly loaded to memory"
		else:
			print "Error: "+fileName+" was not properly loaded to memory"

	else:
		print "No acknowledge => can't retrieve the data"

#### list of commands ####
GET_STATUS = '05 05'
READ_MEMORY = '01 01'
WRITE_MEMORY = '02 02'
WRITE_FILE = '04 04'

#### acknowledge ####
ACK_PROD = "".join([chr(18),'4','4',chr(18)]) # <=> '12 34 34 12'
ACK_ENG = 'VxxV' # <=> '56 78 78 56'

#### data size ####
WORD_SIZE = '20'
HWORD_SIZE = '10'
BYTE_SIZE = '08'

#### file type ####
DCD_TYPE = 'EE'
CSF_TYPE = 'CC'
APPS_TYPE = 'AA'

def serial_command(port):
	global uart_port
	global tx_data
	
	print 'running serial_command with',sys.argv
	uart_port = port
	no_valid_arg = 0
	#### get status command ####
	if sys.argv[2]=='get_status':
		cmd_to_send = " ".join([GET_STATUS,'00 00 00 00 00 00 00 00 00 00 00 00 00 00'])
#		print cmd_to_send	# for debug
		answer = runcmd(cmd_to_send)
		print 'Status is:'
		showanswer(answer)

	#### write file command ####
	elif sys.argv[2]=='write_file':
		infile = open(sys.argv[4],'rb')
		# get file size with 2 methods
#		print "size: %d" % os.stat(sys.argv[3]).st_size
#		print "size: %d" % os.path.getsize(sys.argv[3])
		f_size_int = os.path.getsize(sys.argv[4])
		f_size_hex = get_formated_hex(f_size_int)

		# provide an address like 0x12784596, and skip '0x' in the string chain
		mem_add = get_formated_hex(sys.argv[3][2:10])

		cmd_to_send = " ".join([WRITE_FILE,mem_add,'00',f_size_hex,'00 00 00 00',APPS_TYPE])
		answer = runcmd(cmd_to_send)
		if answer == ACK_ENG or answer == ACK_PROD:
			while True:
				tx_data = infile.read(f_size_int)
				if not tx_data:
					break
				uart_port.write(tx_data)
				ss.appendwrite(tx_data)
		else:
			print "No acknowledge => can't transfer file"

		infile.close()

	#### read memory command ####
	elif sys.argv[2]=='read_mem':
		if sys.argv[4]=='-32':
			access_size = WORD_SIZE
		if sys.argv[4]=='-8':
			access_size = BYTE_SIZE
		if sys.argv[4]=='-16':
			access_size = HWORD_SIZE

		# size of the transfer in bytes
		transfer_size = get_formated_hex(int(sys.argv[4]))

		# provide an address like 0x12784596, and skip '0x' in the string chain
		mem_add = get_formated_hex(sys.argv[3][2:10])
		cmd_to_send = " ".join([READ_MEMORY,mem_add,access_size,transfer_size,'00 00 00 00 00'])
		answer = runcmd(cmd_to_send)
		if answer == ACK_ENG or answer == ACK_PROD:
			# to read the data from serial port
			rd_data = get_serial_data(int(sys.argv[5]))
			showanswer(rd_data)
			# need to find a better test than testing length of the argv list !
			if len(sys.argv) == 7:
				outfile = open(sys.argv[6],'w')
				writetofile(rd_data, outfile)
				outfile.close()
		else:
			print "No acknowledge => can't retrieve the data"

	#### write memory command ####
	elif sys.argv[2]=='write_mem':
		if sys.argv[4]=='-32':
			access_size = WORD_SIZE
		if sys.argv[4]=='-8':
			access_size = BYTE_SIZE
		if sys.argv[4]=='-16':
			access_size = HWORD_SIZE

		# provide an address like 0x12784596, and skip '0x' in the string chain
		mem_add = get_formated_hex(sys.argv[3][2:10])
		write_data = get_formated_hex(sys.argv[5][2:10])
		cmd_to_send = " ".join([WRITE_MEMORY,mem_add,access_size,'00 00 00 00',write_data,'00'])
		answer = runcmd(cmd_to_send)
		if answer == ACK_ENG or answer == ACK_PROD:
			print "Write %s at %s done." % (sys.argv[5],sys.argv[2])
		else:
			print "Can't write to that address !!!"

	elif sys.argv[2] == 'configDDR':
		getStatus()
		configureDDRAndNAND()
		getStatus()
	elif sys.argv[2] == 'exec' or sys.argv[2] == 'execsame':
		print "Wait for proper status\n"
		fails = 1
		while 1:
			sys.stderr.write("  Status check: ")
			rtn = getStatus()
			if len(rtn) == 4 and (ord(rtn[0]) == 0xF0) and (ord(rtn[1]) == 0xF0) and (ord(rtn[2]) == 0xF0) and (ord(rtn[3]) == 0xF0):
				sys.stderr.write("pass\n")
				break
			else: 
				sys.stderr.write("failure %d\n"%fails)
				fails += 1
				if fails == 5:
					sys.stderr.write("too many failures - giving up.\n")
					return
			time.sleep(1)
			
		configureDDRAndNAND()
		if sys.argv[2] == 'exec':
			transferrate=1000000 #460800
			setBaud(transferrate)
		else:
			transferrate=115200
		getStatus()
		writeFile(sys.argv[3], sys.argv[4])
		#verifyFile(sys.argv[3], sys.argv[4])
		getStatus() # this will complete the serial download protocol.

		if sys.argv[2] == 'exec':
			setBaud(115200, False)
		rtn = uart_port.readline()
		ss.appendline(rtn)
		while rtn:
			sys.stderr.write(rtn)
			rtn = uart_port.readline()
			ss.appendline(rtn)
	else:
		no_valid_arg = 1

	# because sys.argv[1] is not valid, help message is displayed
	if no_valid_arg == 1:
		user_help()
		sys.exit()

############ main ###############
def main():
	# if nothing is specified, display usage message !
	if len(sys.argv) == 1:
		user_help()
		sys.exit()

	# Start the program
	if os.path.exists(sys.argv[1]):
		sDev = sys.argv[1]
		# for Cygwin or Linux Python
		port = serial.Serial(sDev, 115200, timeout=5)
		serial_command(port)
		uart_port.close()
	else:	
		print "Error: device "+str(sys.argv[1])+" does not exist"
		sys.exit()

if __name__ == '__main__':
	main()
# End the program