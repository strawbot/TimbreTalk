# version and build date for internal use  Robert Chapman III  Aug 28, 2013

# build dates are unique and sequential. The build date is used to create a version
# number in the form of major.minor.build where major is the year, minor is the month
# and build is the number of minutes into the month based on day, hour and minute.
# seconds are ignored. The version number can be passed around as a 32 bit number.
# Example: Aug 23 2013 - 21:48:33  becomes: 13.8.32988
# note: month is 1 based. Day is changed to 0 based for build number calculation.

'''
uImage header format - 64 bytes
#define IH_MAGIC    0x27051956    /* Image Magic Number     */
#define IH_NMLEN    32            /* Image Name Length      */

typedef struct image_header {
    uint32_t    ih_magic;         /* Image Header Magic Number */
    uint32_t    ih_hcrc;          /* Image Header CRC Checksum */
    uint32_t    ih_time;          /* Image Creation Timestamp  */
    uint32_t    ih_size;          /* Image Data Size           */
    uint32_t    ih_load;          /* Data     Load  Address    */
    uint32_t    ih_ep;            /* Entry Point Address       */
    uint32_t    ih_dcrc;          /* Image Data CRC Checksum   */
    uint8_t     ih_os;            /* Operating System          */
    uint8_t     ih_arch;          /* CPU architecture          */
    uint8_t     ih_type;          /* Image Type                */
    uint8_t     ih_comp;          /* Compression Type          */
    uint8_t     ih_name[IH_NMLEN];    /* Image Name            */
} image_header_t;
'''
import struct
import datetime
import endian
import sys, traceback
from targets import RELEASE_DATE_LENGTH, APP_NAME_LENGTH

ubootTag = 'U-Boot'
uimageTag = 'uImage'
versionTag = 0xB11DDA7E # build date

def dumpUimage(file):
	image = map(ord, open(file, 'rb').read(64)) # header is 64 bytes
	print >>sys.stderr, 'magic: %X'%endian.long(image[0:4])
	print >>sys.stderr, 'hcrc: %X'%endian.long(image[4:8])
	print >>sys.stderr, 'time: %X'%endian.long(image[8:12])
	print >>sys.stderr, 'size: %X'%endian.long(image[12:16]) # size of image following header
	print >>sys.stderr, 'load: %X'%endian.long(image[16:20])
	print >>sys.stderr, 'ep: %X'%endian.long(image[20:24])
	print >>sys.stderr, 'dcrc: %X'%endian.long(image[24:28])
	print >>sys.stderr, 'os: %X'%image[28]
	print >>sys.stderr, 'arch: %X'%image[29]
	print >>sys.stderr, 'type: %X'%image[30]
	print >>sys.stderr, 'comp: %X'%image[31]
	print >>sys.stderr, 'name: %s'%''.join(map(chr, image[32:])).strip()

def listfind(source, match): # find string match in output list
	m = map(ord, match)
	offset = [i for i in range(len(source)) if source[i:i+len(m)] == m]
	if offset:
		return offset[0]
	return -1

# Version and date relationships
YMDHMS = "%Y-%m-%d %H:%M:%S"	# metric format
MDY_HMS = "%b %d %Y - %H:%M:%S"	# uboot format
MDYHMS = "%b %d %Y %H:%M:%S"	# boot and app format

def dateString(year,month,day,hour,minute,second):
	return '%d-%02d-%02d %02d:%02d:%02d'%(year,month,day,hour,minute,second)

def dateTuple(date):
	try:
		d = datetime.datetime.strptime(date, YMDHMS)
		return d.year, d.month, d.day, d.hour, d.minute, d.second
	except:
		return 2000, 0, 1, 0, 0, 0

def packMMB(year, month, build): # return 32 bit packed version
	return (year%100)<<24 | month<<16 | build

def unpackMMB(version): # return major, minor, build
	return (version>>24, version>>16 & 0xFF, version &0xFFFF)

def buildNumber(day, hour, minute): # derive build number from day, hour, minute
	return ((day-1)*24 + hour)*60 + minute

def dayHourMinute(build):
	day = ((build/60)/24)+1
	hour = (build/60)%24
	minute = build%60
	return day, hour, minute

def buildDate(version): # derive year, month day, hour, minute from build number
	major, minor, build = unpackMMB(version)
	day, hour, minute = dayHourMinute(build)
	return (major+2000,minor,day,hour,minute)

def buildVersion(date): # date string to 32 bit version
	year, month, day, hour, minute, second = dateTuple(date)
	build = buildNumber(day, hour, minute)
	return packMMB(year, month, build)

def currentDate():
	d = datetime.datetime.now()
	return dateString(d.year, d.month, d.day, d.hour, d.minute, d.second)

# uboot and uimage date to version
def extractUbootDate(image): # must find string inside binary and convert
	offset = listfind(image, ubootTag+' 2')
	if offset != -1:
		imgdate = image[offset:]
		openParen = listfind(imgdate, '(')
		closeParen = listfind(imgdate, ')')
		date = ''.join(map(chr,imgdate[openParen+1:closeParen]))
		d = datetime.datetime.strptime(date, MDY_HMS)
		return dateString(d.year, d.month, d.day, d.hour, d.minute, d.second)
	return dateString(*(buildDate(0)+(0,)))

def extractUimageDate(image): # grab and convert timestamp from header
	timestamp = endian.long(image[8:12])
	d = datetime.fromtimestamp(1367899411)
	return dateString(d.year, d.month, d.day, d.hour, d.minute, d.second)

# utilities
def printVersionDate(version):
	year,month,day,hour,minute = buildDate(version)
	print >>sys.stderr, dateString(year,month,day,hour,minute,0)

def printVersion(version):
	major, minor, build = unpackMMB(version)
	print >>sys.stderr, '%d.%d.%d'%(major,minor,build)

# boot and apps version, name and date
'''
#define RELEASE_DATE_LENGTH 32
#define APP_NAME_LENGTH 16

// version segment buried in boots, launcher and apps
typedef struct {
	unsigned long headerTag;
	char buildName[16];
	char buildDate[32];
} version_t;
'''
printme = 0

# common offset to version information for all images
IMAGE_HEADER_ID = 0xB11DDA7E # BILDDATE

VERSION_MAGIC_OFFSET = 0x600
versionStruct = "L16s32s"

def versionNumber(image):
	if endian.long(image[VERSION_MAGIC_OFFSET:]) == IMAGE_HEADER_ID:
		if printme: print 'Build Version:', buildVersion(versionDate(image))
		return buildVersion(versionDate(image))
	if printme: print 'No version because magic number is wrong', endian.long(image[VERSION_MAGIC_OFFSET:])
	return 0
	
def versionName(image):
	return endian.cast(versionStruct, image[VERSION_MAGIC_OFFSET:])[1]

def MDYHMSasYMDHMS(date): # string to string date format converter
	d = datetime.datetime.strptime(date, MDYHMS)
	return dateString(d.year, d.month, d.day, d.hour, d.minute, d.second)

def versionDate(image):
	result = ' '
	try:
		string = endian.cast(versionStruct, image[VERSION_MAGIC_OFFSET:])[2].rstrip('\0')
		if string:
			if printme: print 'input string:', string, '  converted to:', MDYHMSasYMDHMS(string)
			result = MDYHMSasYMDHMS(string)
	except Exception as e:
		print >>sys.stderr, e
		traceback.print_exc(file=sys.stderr)
	finally:
		return result

# application version name and date
def extractNameDateVersion(image, endianness='big'):
	name, date, version = 'naname','2000-01-01 00:00:00',0
	tag = map(chr, endian.byteList(versionTag,4,endianness))
	offset = listfind(image, tag)
	if offset != -1:
		offset += len(tag)
		name = endian.l2s(image[offset:][:16])
		date = MDYHMSasYMDHMS(endian.l2s(image[offset+16:][:20]))
		version = buildVersion(date)
	name = map(ord, name) + [0]*(APP_NAME_LENGTH - len(name))
	date = map(ord, date) + [0]*(RELEASE_DATE_LENGTH - len(date))
	return (name, date, version)

# test
def testAppVD():
	import image
	srec = image.imageRecord('Test/testApp.srec')
	name, date, version = extractNameDateVersion(srec.image, 'little')
	print 'image name: ', name, ' and date: ', date, ' version:', version

if __name__ == '__main__':
	testAppVD()
	exit()
	date = "Aug 23 2013 - 21:48:33"
	d = datetime.datetime.strptime(date, MDY_HMS)
	build = buildNumber(d.day, d.hour, d.minute)
	version = packMMB(d.year, d.month, build)
	print >>sys.stderr, 'version:',
	printVersion(version)
	print >>sys.stderr, 'Dates should be same except seconds: ',date,' == ',
	printVersionDate(version)
	s = currentDate()
	if s != dateString(*dateTuple(s)):
		print >>sys.stderr, 'conversion failed: currentDate, dateString, dateTuple'
	print 'Version Date:', MDYHMSasYMDHMS('Jan 19 2015 17:02:09')