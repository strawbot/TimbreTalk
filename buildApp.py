#!/usr/bin/env python
# create binary image on whatever platform
# use: python buildApp.py

'''
Notes for windows
 compile on XP for now with python 2.7 and pyinstaller 2.1
 
Mac OSX
 compile on Lion with python 2.7 and pyinstaller 3.2
 !test before build.
 from command line use pyinstaller
  to get to that point the following was done: 
   Not sure about this but also export MACOSX_DEPLOYMENT_TARGET=10.6 was set in .bash_profile
 
 download and install XCode development tools from developer's site
 download and install brew
 download and install Python 2.7.12
 reboot
 sudo easy_install pip
 download and make sip
   on El Capitan: sudo chown -R $(whoami):admin /usr/local
 brew install PyQt
 sudo pip install pyinstaller
 sudo pip install pyserial
 
 pyinstaller --clean --runtime-hook rthook_pyqt4.py -w -F -i timbretalk.icns  --noupx -p . --osx-bundle-identifier="TimbreTalk" tt.py
 still no version number is displayed in Finder
 
 to run from command line to catch errors: ./dist/tt.app/Contents/MacOS/tt
'''
import sys, os, shutil

if sys.platform == 'win32':
	print("Building app for Windows")
	os.system('python PyInstaller\pyinstaller.py --runtime-hook rthook_pyqt4.py -w -F -i timbretalk.ico --noupx -p . tt.py')
elif sys.platform == 'darwin':
	print ("Building app for Mac OSX")
	shutil.rmtree('dist/tt.app') # save a step for builder by removing previous build
	os.system('pyinstaller --clean --runtime-hook rthook_pyqt4.py -w -F -i timbretalk.icns  --noupx -p . --osx-bundle-identifier="TimbreTalk" tt.py')
elif sys.platform[:5] == 'linux':
	"Building app for Linux"
	os.system('PyInstaller/pyinstaller.py --runtime-hook rthook_pyqt4.py -w -F -i timbretalk.ico -p . tt.py')
else:
	print ('unknown system platform: %s'%sys.platform, file=sys.stderr)
	sys.exit()

print ('Your application image is available in "dist/"')
