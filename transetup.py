# setup utility for packaging Tran program for XP  Rob Chapman  Jul 7, 2011
# run: python transetup.py py2exe

from distutils.core import setup
import py2exe
import os

manifest = """
</xml version="1.0" encoding="UTF-8" standalone="yes"/>
<assembly xmlns="urn:schemas-microsoft-com:asm.v1"
manifestVersion="1.0">
<assemblyIdentity
    version="0.64.1.0"
    processorArchitecture="x86"
    name="Controls"
    type="win32"
/>
<description>nexus</description>
<dependency>
    <dependentAssembly>
        <assemblyIdentity
            type="win32"
            name="Microsoft.Windows.Common-Controls"
            version="6.0.0.0"
            processorArchitecture="X86"
            publicKeyToken="6595b64144ccf1df"
            language="*"
        />
    </dependentAssembly>
</dependency>
</assembly>
"""
import sys
#sys.path.append("../../Common/Who")
from cpuids import *
#sys.path.append("../../Common/SFAP")
from pids import *


data_files=[
			(".",		  ['readme.txt']),
			(".",		  ['LightCycle.ico'])
		   ]

windows= [
          {
            "script": 'qtran.py',
            "icon_resources": [(0, 'LightCycle.ico')]
          }
         ]

setup(
      windows=windows,
      data_files=data_files,
	  options = {"py2exe":{
                         "bundle_files": 3,
                         "compressed": 1,
                          "optimize": 2,
                          "ascii": 1,
    }},
         zipfile = None , # or none
      )
