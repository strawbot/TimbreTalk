#!/usr/bin/env python

import sys

print "std out"
print >>sys.stderr, "std err"

try:
	blah
except:
	print 'burp'
	raise Exception('burped')
	print 'no get here'