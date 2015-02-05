#!/bin/sh
# Test suite for sdown

side=right
serialPort=cu.usbserial-FTB3N788
#serialPort=cu.usbserial-FTFK0G7C
fileName=../../release/src/Launcher.elf.S19

sdown() {
#	./sdown.py side=$side port=$serialPort file=$fileName fileop=verify
	./sdown.py side=$side port=$serialPort file=$fileName fileop=send
#	./testthreadtimer.py 
#	./testtimerapp.py 
}

# run and check output
sdown
if [ $? != 0 ]; then
	echo "sdown failed"
else
	echo "sdown passed"
fi
