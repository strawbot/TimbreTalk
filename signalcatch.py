# Signal module for dealing with signals from os  Robert Chapman III  Nov 13, 2013

# factored to one module because windows uses only a subset

import os, signal, sys


def doNothing():
	pass

beforeIdie = 0

def initSignalCatcher(hook=doNothing):
	global beforeIdie
	beforeIdie = hook

	def die(signum=0, stack=0):
		print >>sys.stderr, 'got signal:', signum
		beforeIdie()
		os._exit(-1)

	signal.signal(signal.SIGTERM, die)
	signal.signal(signal.SIGABRT, die)
	signal.signal(signal.SIGINT, die)
	if sys.platform != 'win32':
		signal.signal(signal.SIGBUS, die)
		signal.signal(signal.SIGQUIT, die)
