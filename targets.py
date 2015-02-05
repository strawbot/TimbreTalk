# Image header and memory map  Robert Chapman III  Aug 26, 2013

import struct

# taken from copyrun.h and memorymaps.h
MAIN_BOOT		= 0
UBOOT_LEFT		= 0x20000
UBOOT_RIGHT		= 0x90000
LAUNCHER_LEFT	= 0x100000
LAUNCHER_RIGHT	= 0x180000
MAIN_APP_LEFT	= 0x200000
MAIN_APP_RIGHT	= 0x300000
IO_APP_LEFT		= 0x400000
IO_APP_RIGHT	= 0x440000
SWB_APP_LEFT	= 0x480000
SWB_APP_RIGHT	= 0x4C0000
BIG_UBOOT_LEFT	= 0x500000
BIG_UBOOT_RIGHT	= 0x600000

SLOT_BOOT = SWB_BOOT = IO_BOOT			= 0
SLOT_APP = SWB_APP = IO_APP	= 0x10000
IO_HIGH_BOOT	= 0x30000

'''
#define RELEASE_DATE_LENGTH 32
#define APP_NAME_LENGTH 16

// image header
typedef struct {
	struct version {
		unsigned char major;
		unsigned char minor;
		unsigned short build;
	};
	unsigned long start;
	unsigned long dest;
	unsigned long size;
	unsigned long entry;
	unsigned long checksum;
	unsigned long headerSize;
	char releaseDate[RELEASE_DATE_LENGTH];		// address within image
	char appName[APP_NAME_LENGTH];			// ditto
	unsigned long headerChecksum;
}imageHead_t;
'''

imageHeaderStruct = "=BBHLLLLLL32s16sL"
HEADER_SIZE = struct.Struct(imageHeaderStruct).size #bytes
RELEASE_DATE_LENGTH = 32
APP_NAME_LENGTH = 16
