# endian mixup prevention  Rob Chapman  Jan 27, 2011
# big endian format is default

printme = 0

# string of hex to list of hex, must start with 0x
def hexList (string, endian='big'):
	l = [int(string[i:i+2],16)  for i in range(2,len(string),2)]
	if endian == "big":
		return l
	else:
		return l[::-1]

# numbers to lists of bytes
def byteList (integer, length, endian="big"): # turn an integer into a list of values
	if printme: print ('endian:',endian)
	n = length - 1
	l = [(integer/(2**((n-i)*8)) & 0xFF) for i in range(length)]
	if endian == "big":
		return l
	else:
		return l[::-1]

def shortList (integer, endian="big"): # turn a 2 byte integer into a list of values
	return byteList(integer, 2, endian)

def longList (integer, endian="big"): # turn a 4 byte integer into a list of values
	return byteList(integer, 4, endian)

def longlongList (integer, endian="big"): # turn a 8 byte integer into a list of values
	return byteList(integer, 8, endian)

# lists of bytes back to numbers
def toInteger(bytes, length, endian="big"):
	n = length - 1
	if endian == "big":
		return sum((bytes[i]<<(8*(n-i))) for i in range(length))
	else:
		return sum((bytes[i]<<(8*(i))) for i in range(length))

def short(bytes, endian="big"):
	return toInteger(bytes, 2, endian)

def long(bytes, endian="big"):
	return toInteger(bytes, 4, endian)

def longlong(bytes, endian="big"):
	return toInteger(bytes, 8, endian)

# conversion between strings and lists
def s2l(s): # string to list of bytes
	return [ord(s[i]) for i in range(len(s))]

def l2s(l): # list of bytes to string
	if type(l[0]) == type(' '):
		return l
	return ''.join(list(map(chr,l[:])))

# convert list of bytes to a structure given format
'''
A format character may be preceded by an integral repeat count. For
example, the format string '4h' means exactly the same as 'hhhh'.

Whitespace characters between formats are ignored; a count and its
format must not contain whitespace though.

For the 's' format character, the count is interpreted as the size of
the string, not a repeat count like for the other format characters; for
example, '10s' means a single 10-byte string, while '10c' means 10
characters. If a count is not given, it defaults to 1. For packing, the
string is truncated or padded with null bytes as appropriate to make it
fit. For unpacking, the resulting string always has exactly the
specified number of bytes. As a special case, '0s' means a single, empty
string (while '0c' means 0 characters).
x	pad byte	no value	 	 
c	char	string of length 1	1	 
b	signed char	integer	1	(3)
B	unsigned char	integer	1	(3)
?	_Bool	bool	1	(1)
h	short	integer	2	(3)
H	unsigned short	integer	2	(3)
i	int	integer	4	(3)
I	unsigned int	integer	4	(3)
l	long	integer	4	(3)
L	unsigned long	integer	4	(3)
q	long long	integer	8	(2), (3)
Q	unsigned long long	integer	8	(2), (3)
f	float	float	4	(4)
d	double	float	8	(4)
s	char[]	string	 	 
p	char[]	string	 	 
P	void *	integer	 	(5), (3)
Notes:
1. The '?' conversion code corresponds to the _Bool type defined by C99. If
this type is not available, it is simulated using a char. In standard
mode, it is always represented by one byte.

2. The 'q' and 'Q' conversion codes are available in native mode only if
the platform C compiler supports C long long, or, on Windows, __int64.
They are always available in standard modes.

3. When attempting to pack a non-integer using any of the integer
conversion codes, if the non-integer has a __index__() method then that
method is called to convert the argument to an integer before packing.
If no __index__() method exists, or the call to __index__() raises
TypeError, then the __int__() method is tried. However, the use of
__int__() is deprecated, and will raise DeprecationWarning.
'''

import struct
import sys
def cast(format, list, endian="big"):
	if endian == "big":
		format = '>'+format
	else:
		format = '<'+format
	listsize = len(list)
	fmtsize = struct.calcsize(format)
	if fmtsize > listsize:
		print('error: structure bigger than list: str=%i list=%i' % (fmtsize, listsize))
		return [0 for i in range(fmtsize)]
	return struct.unpack(format, l2s(list[0:fmtsize]))
