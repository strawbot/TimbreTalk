#!/usr/bin/env python
# edits for turning guid files into python files  Robert Chapman III  Nov 7, 2012

# run this file to update 'guidsmain.py' with the latest guids and properties
import re

inpath = "../../Main/App/__database_manager/"
guidfile = inpath+"DatabaseManager_GUID.h"
guidprop = inpath+"DatabaseManager_GUID.c"
guiddb = 'guiddb.sql'
guidbout = 'guidb'
outpath = "./"
outfile = outpath+'guidsmain.py'

output = open(outfile, 'w')

output.write('''# generated file from DatabaseManager_GUID.[ch] by guidbuilder.py
# widths
GUIDWIDTH_GUIDPTR = 4
GUIDWIDTH_1BIT = 1
GUIDWIDTH_16BIT = 2
GUIDWIDTH_e16BIT_i32BIT = 2
GUIDWIDTH_e32BIT_i64BIT = 4
GUIDWIDTH_32BIT = 4
GUIDWIDTH_64BIT = 8
GUIDWIDTH_80BIT = 10

# guid list:
''')

guids = []
props = {}

input = open(guidfile, 'r')

state = 0 # separate file sections into states
for line in input:
	if state == 0: # looking for trigger
		if -1 != line.find('enum GUID_REGISTERS'):
			state = 1
	elif state == 1: # line skip
		state = 2
		count = 0
	else:
		if -1 != line.find('// always add new GUIDs above this line'): # end of guids
			output.write(' = range(%d)'%count)
			break
		else:
			line = re.sub(r'//.*','',line) # remove comments to end of line
			line = re.sub(r'/\*.*\*/','',line) # remove embedded comments
			line = re.sub(r' = 0','',line) # remove any equates
			line = line.strip()
			if line:
				guid = line.split(',')[0]
				guids.append(guid)
				props[guid] = []
				
				line = line+'\\'
				count += 1
				output.write(line+'\n')

input.close()

output.write('\n\n# guid properties\n')
input = open(guidprop, 'r')

'''
this:
{GUID_SCRATCH_REG_0,"Scratch Reg 0",GUIDWIDTH_16BIT,GUID_DS_SCRATCH,GUID_STOREPOS(0),GUID_WORDSIG(0),GUIDTYPE_UINT,GUIDUNIT_UNITLESS,GUID_SCALE(1),GUID_LOGLEVEL(2),GUID_STATIC_TAGNAME,5,100,55},
becomes:
GUID_SCRATCH_REG_0:("Scratch Reg 0",GUIDWIDTH_16BIT,"GUID_SCRATCH_REG_0"),
'''

state = 0
for line in input:
	if state == 0:
		if -1 != line.find('//   pure testing registers for now'):
			state = 1
			output.write('guidNamesWidths = {\n')
	else:
		if -1 != line.find('};'):
			output.write('}\n')
			break
		else:
			line = re.sub(r'//.*','',line) # remove comments to end of line
			line = re.sub(r'{','',line)
			line = re.sub(r'}','',line)
			line = re.sub(r'/\*.*\*/','',line) # remove embedded comments
			line = line.strip()
			if line:
				line = line.split(',')
				guid, prop = line[0], (line[1],line[2],line[7],line[6])
				props[guid] = prop
				line = '%s:(%s,%s,"%s"),'%(guid, prop[0], prop[1], guid)
				output.write(line+'\n')

input.close()

output.close()

guiddbsrc = '''-- GUID database information - generated file; don't edit
-- extracted from DatabaseManager_GUID.h
CREATE TABLE guidTypes (id INTEGER PRIMARY KEY, name TEXT);
	INSERT INTO guidTypes (id, name) VALUES (0, "GUIDTYPE_NOTSPECIFIED");
	INSERT INTO guidTypes (name) VALUES ("GUIDTYPE_OBSOLETED");
	INSERT INTO guidTypes (name) VALUES ("GUIDTYPE_DYNAMIC");
	INSERT INTO guidTypes (name) VALUES ("GUIDTYPE_GUIDPTR");
	INSERT INTO guidTypes (name) VALUES ("GUIDTYPE_BIT");
	INSERT INTO guidTypes (name) VALUES ("GUIDTYPE_UINT");
	INSERT INTO guidTypes (name) VALUES ("GUIDTYPE_INT");
	INSERT INTO guidTypes (name) VALUES ("GUIDTYPE_FLOAT");
	INSERT INTO guidTypes (name) VALUES ("GUIDTYPE_DOUBLE");
	INSERT INTO guidTypes (name) VALUES ("GUIDTYPE_DBSTRING");
	INSERT INTO guidTypes (name) VALUES ("GUIDTYPE_ENUM_PORTFUNC");
	INSERT INTO guidTypes (name) VALUES ("GUIDTYPE_ENUM_BAUDRATE");
	INSERT INTO guidTypes (name) VALUES ("GUID_NUM_DATATYPES");

CREATE TABLE guidWidths (id INTEGER PRIMARY KEY, name TEXT, bits INTEGER);
	INSERT INTO guidWidths (id, bits, name) VALUES (0, "RESERVED", 0);
	INSERT INTO guidWidths (bits, name) VALUES ("OBSOLETED", 0);
	INSERT INTO guidWidths (bits, name) VALUES ("GUIDPTR", 32);
	INSERT INTO guidWidths (bits, name) VALUES ("1BIT", 1);
	INSERT INTO guidWidths (bits, name) VALUES ("16BIT", 16);
	INSERT INTO guidWidths (bits, name) VALUES ("e16BIT_i32BIT", 16);
	INSERT INTO guidWidths (bits, name) VALUES ("e32BIT_i64BIT", 32);
	INSERT INTO guidWidths (bits, name) VALUES ("32BIT", 32);
	INSERT INTO guidWidths (bits, name) VALUES ("64BIT", 64);
	INSERT INTO guidWidths (bits, name) VALUES ("80BIT", 80);

CREATE TABLE unitTypes (id INTEGER PRIMARY KEY, name TEXT);
	INSERT INTO unitTypes (id, name) VALUES (0, "GUIDUNIT_NOTSPECIFIED");
	INSERT INTO unitTypes (name) VALUES ("GUIDUNIT_UNITLESS");

	INSERT INTO unitTypes (name) VALUES ("GUIDUNIT_TEMP_DEGC");
	INSERT INTO unitTypes (name) VALUES ("GUIDUNIT_TEMP_DEGF");

	INSERT INTO unitTypes (name) VALUES ("GUIDUNIT_PRES_PSI");
	INSERT INTO unitTypes (name) VALUES ("GUIDUNIT_PRES_BAR");

	INSERT INTO unitTypes (name) VALUES ("GUIDUNIT_FLOW_M3");
	INSERT INTO unitTypes (name) VALUES ("GUIDUNIT_FLOW_BPD");

	INSERT INTO unitTypes (name) VALUES ("GUIDUNIT_VIB_G");

	INSERT INTO unitTypes (name) VALUES ("GUIDUNIT_ELEC_VOLTS");
	INSERT INTO unitTypes (name) VALUES ("GUIDUNIT_ELEC_mVOLTS");
	INSERT INTO unitTypes (name) VALUES ("GUIDUNIT_ELEC_AMPS");
	INSERT INTO unitTypes (name) VALUES ("GUIDUNIT_ELEC_mAMPS");
	INSERT INTO unitTypes (name) VALUES ("GUIDUNIT_ELEC_uAMPS");
	INSERT INTO unitTypes (name) VALUES ("GUIDUNIT_ELEC_kVA");
	INSERT INTO unitTypes (name) VALUES ("GUIDUNIT_ELEC_kW");

	INSERT INTO unitTypes (name) VALUES ("GUIDUNIT_TIME_DAYS");
	INSERT INTO unitTypes (name) VALUES ("GUIDUNIT_TIME_HOURS");
	INSERT INTO unitTypes (name) VALUES ("GUIDUNIT_TIME_MINUTES");
	INSERT INTO unitTypes (name) VALUES ("GUIDUNIT_TIME_SECONDS");
	INSERT INTO unitTypes (name) VALUES ("GUIDUNIT_TIME_mSECONDS");

	INSERT INTO unitTypes (name) VALUES ("GUIDUNIT_FREQ_HZ");
	INSERT INTO unitTypes (name) VALUES ("GUIDUNIT_FREQ_kHZ");

	INSERT INTO unitTypes (name) VALUES ("GUIDUNIT_PERCENT");
	INSERT INTO unitTypes (name) VALUES ("GUID_NUM_UNITTYPES");

CREATE TABLE guids (id INTEGER PRIMARY KEY,name TEXT,desc TEXT,type TEXT,width TEXT,units TEXT);

'''
import sqlite3 as lite
import os

try:
	os.remove(guidbout)
except:
	pass

con = lite.connect(guidbout)

with con:
	cur = con.cursor()
	for line in guiddbsrc.splitlines():
		cur.execute(line)
	prop = props[guid] # start at zero
	cur.execute('INSERT INTO guids (id, name, desc, type, width, units)VALUES (0, "%s", %s, "%s", "%s", "%s");\n'%
	(guids[0], prop[0], prop[1], prop[2], prop[3]))

	for guid in guids[1:]:
		prop = props[guid]
		cur.execute('INSERT INTO guids (name, desc, type, width, units)VALUES ("%s", %s, "%s", "%s", "%s");\n'%
		(guid, prop[0], prop[1], prop[2], prop[3]))
