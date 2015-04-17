# Image header and memory map  Robert Chapman III  Aug 26, 2013

import struct

# taken from copyrun.h and memorymaps.h
MAIN_BOOT		= 0x08000000
MAIN_APP_LEFT	= 0x08080000
MAIN_APP_RIGHT	= 0x08180000

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
