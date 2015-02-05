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
guidnames = []

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
				guidnames.append(line)

unknownguids = sorted(list(set([739,293,3002,3003,3005,2999,2997,2998,3000,2994,2992,2993,2995,3044,3042,3043,3045,3034,3032,3033,3035,2989,2987,2988,2990,2984,2982,2983,2985,273,273,261,284,285,285,268,268,267,266,265,265,264,263,262,294,294,292,292,292,292,292,270,270,270,270,270,270,270,271,271,271,271,271,298,283,282,282,282,258,258,259,259,293,293,280,278,277,260,256,257,401,400,399,397,410,409,408,406,353,352,351,350,348,347,362,361,360,378,363,269,269])))
#print unknownguids
#exit()
# print guidnames
parseGuids()
for guid in unknownguids:
#	print guid
	print "%d: %s"%(guid, guidnames[guid])
