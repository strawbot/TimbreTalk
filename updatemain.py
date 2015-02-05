#!/usr/bin/env python

# script to update all firmware on main

from sdown import sdown

IMAGE_PATH = 'file=../../release/src'
PORT = 'port=cu.usbserial-FTB3N788'

sdown(['version'])
sdown([PORT, IMAGE_PATH+'/MAIN_BOOT.elf.S19','boot'])
sdown([PORT, IMAGE_PATH+'/IO_APP.elf.S19','ioapp' ])
sdown([PORT, IMAGE_PATH+'/Launcher.elf.S19','launcher' ])
sdown([PORT, IMAGE_PATH+'/MAIN_APP.elf.S19','app' ])
sdown([PORT, IMAGE_PATH+'/u-boot.imx.serial','uboot' ])
sdown([PORT, IMAGE_PATH+'/IO_APP.elf.S19','ioapp','right' ])
sdown([PORT, IMAGE_PATH+'/Launcher.elf.S19','launcher','right' ])
sdown([PORT, IMAGE_PATH+'/MAIN_APP.elf.S19','app','right' ])
sdown([PORT, IMAGE_PATH+'/u-boot.imx.serial','uboot','right' ])
