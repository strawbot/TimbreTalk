# list files used by an App  Robert Chapman III  May 7, 2015
# usage: python applist.py tt sdown
import os.path
import sys

files = []

def parseList(thisfile):
	file = thisfile+'.py'
	if file not in files:
		if os.path.isfile(file):
			files.append(file)
			for line in open(file,'r').readlines():
				line = line.rsplit('#')[0]
				if line:
					words = line.replace(',',' ').split()
					if words:
						if words[0] == 'import':
							for file in words[1:]:
								parseList(file)
						elif words[0] == 'from':
							parseList(words[1])

for app in sys.argv[1:]:
	print ('Files used in %s.py:'%app)
	del files[:]
	parseList(app)
	files.sort()
	for file in files:
		if file:
			print ('  ',file)
