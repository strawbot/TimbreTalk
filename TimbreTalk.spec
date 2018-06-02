# -*- mode: python -*-

block_cipher = None

import sys
sys.modules['FixTk'] = None


a = Analysis(['tt.py'],
             pathex=['Z:\\Projects\\TimbreTalk','/Users/RobertChapman/anaconda/envs/py2qt4/bin/python'],
             binaries=[],
             datas=[],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=['./rthook_pyqt4.py'],
             excludes=['FixTk', 'tcl', 'tk', '_tkinter', 'tkinter', 'Tkinter'],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='TimbreTalk',
          debug=False,
          strip=False,
          upx=True,
          runtime_tmpdir=None,
          console=False , icon='timbretalk.ico')

if sys.platform == 'darwin':
    app = BUNDLE(exe,
             name='TimbreTalk.app',
             icon='timbretalk.ico',
             bundle_identifier=None)
