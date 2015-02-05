# Parsing GUID Header file to get guid names  Robert Chapman III  Jan 8, 2013

import re

inpath = "../../Main/App/__database_manager/"
guidfile = inpath+"DatabaseManager_GUID.h"

outpath = "./"
outfile = outpath+'guidlist'

state = 0
guids = []	# list of guids and guid number

for line in open(guidfile, 'r').readlines():
	if state == 0:						# hunt for start
		if -1 != line.find('enum GUID_REGISTERS'):
			state = 1
	elif state == 1:					# skip a line
		state = 2
	else:								# parse guids
		if -1 != line.find('// always add new GUIDs above this line'):
			break
		line = re.sub(r'//.*','',line)		# remove comments to end of line
		line = re.sub(r'/\*.*\*/','',line)	# remove inline comments
		line = re.sub(r' = 0','',line)		# remove initial setting
		line = line.strip()					# remove white space
		line = line.strip(',')				# remove commer
		if line:
			guids.append((line, len(guids)))

guids.sort()

output = open(outfile, 'w')
output.write('# guid list generated file from DatabaseManager_GUID.h\n')

for guid in guids:
	output.write('%s = %i\n' % (guid[0], guid[1]) )

output.close()