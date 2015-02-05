# Parsing GUID Header file to get guid names  Robert Chapman III  Jan 8, 2013

import re

inpath = "../../Main/App/__database_manager/"
guipath = "../../display/gui/"
guidlist = inpath+"DatabaseManager_GUID.h"
bidlist = guipath+'qtgui/guiconnect/'+'generatedbackendenum.h'
bidmap = guipath+'/GUI/src/'+'guiDBMapGenerated.cpp'

outpath = "./"
guidsout = outpath+'guidlist'
bidsout = outpath+'backendids'
bids2guidsout = outpath+'bid2guids'

guids = {}	# dictionary of guids and guid number
bids = {} # dictionary of bids
bid2guids = {} # map of bids to guids

# utilities
def cleanLine(line):
	line = re.sub(r'//.*','',line)		# remove comments to end of line
	line = re.sub(r'/\*.*\*/','',line)	# remove inline comments
	line = re.sub(r' ','',line)					# remove white space
	return line.strip() # remove eol

# inputs
def parseGuids():
	state = 0
	for line in open(guidlist, 'r').readlines():
		if state == 0:						# hunt for start
			if -1 != line.find('enum GUID_REGISTERS'):
				state = 1
		elif state == 1:					# skip a line
			state = 2
		else:								# parse guids
			if -1 != line.find('// always add new GUIDs above this line'):
				break
			line = re.sub(r'=0','',cleanLine(line).strip(',')) # remove initial setting
			if line:
				guids[line] = len(guids)

def parseBids():
	state = 0
	bid = 0
	for line in open(bidlist, 'r').readlines():
		if state == 0:						# hunt for start
			if -1 != line.find('enum MetaType {'):
				state = 1
		else:								# parse bids
			if -1 != line.find('};'):
				break
			line = cleanLine(line).strip(',')

			if line:
				line = line.split('=')
				if len(line) == 1:
					bid += 1
				bids[line[0]] = bid

def mapBids2Guids():
	state = 0
	for line in open(bidmap, 'r').readlines():
		if state == 0:						# hunt for start
			if -1 != line.find('guiDBMap_t guiDBMap[] = {'):
				state = 1
		else:								# parse map
			if -1 != line.find('};'):
				break
			line = re.sub(r'{DataBackend::','',cleanLine(line).strip(',').strip('}'))
			if line:
				line = line.split(',')
				if line[1] != '0':
					bid2guids[line[0]] = line[1]

# outputs
def outputIds(ids, out, comment):
	output = open(out, 'w')
	output.write(comment)
	for key in sorted(ids):
		output.write('%s = %i\n' % (key, ids[key]) )
	output.close()

def outputBidMap():
	map = {}
	for key in bid2guids:
		bid = key
		bidn = bids[bid]
		guid = bid2guids[key].strip('"')
		guidn = guids[guid]
		map[bidn] = (guidn,bid,guid)

	comment = '# bid guid map from '+bidmap+'\n'
	output = open(bids2guidsout, 'w')
	output.write(comment)
	for entry in sorted(map):
		output.write('%i => %i : %s => %s\n' % (entry,map[entry][0],map[entry][1],map[entry][2]) )
	output.close()

parseGuids()
parseBids()
mapBids2Guids()

outputIds(guids, guidsout, '# guid list generated file from '+guidlist+'\n')
outputIds(bids, bidsout, '# bid list generated from '+bidlist+'\n')
outputBidMap()