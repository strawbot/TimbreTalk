import os.path

files = []

def parseList(file):
	file = file+'.py'
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

parseList('tt')
files.sort()
for file in files:
	if file:
		print file