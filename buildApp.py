#!/usr/bin/env python
# create binary image on whatever platform
# use: python buildApp.py

import sys, os

if sys.platform == 'win32':
	os.system('python PyInstaller-2.1\pyinstaller.py --runtime-hook rthook_pyqt4.py -w -F -i timbretalk.ico --noupx -p . tt.py')
elif sys.platform == 'darwin':
#this doesn't work:	subprocess.call('PyInstaller-2.1/pyinstaller.py --runtime-hook rthook_pyqt4.py -w -F -i timbretalk.icns -p .  tt.py')
	os.system('PyInstaller-2.1/pyinstaller.py --runtime-hook rthook_pyqt4.py -w -F -i timbretalk.icns -p .  tt.py')
elif sys.platform[:5] == 'linux':
	os.system('PyInstaller-2.1/pyinstaller.py --runtime-hook rthook_pyqt4.py -w -F -i timbretalk.ico -p . tt.py')
else:
	print >>sys.stderr, 'unknown system platform: %s'%sys.platform
	sys.exit()

print 'Your application image is available in "dist/"'