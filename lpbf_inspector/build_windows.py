"""Build the self-contained Windows executable. Run with Python on Windows."""
from pathlib import Path
import os
import sys

ROOT=Path(__file__).resolve().parent
if __name__=='__main__':
    os.chdir(ROOT)
    os.environ['PYINSTALLER_CONFIG_DIR']=str(ROOT/'.build-cache/config')
    if (ROOT/'.build-tools').is_dir():sys.path.insert(0,str(ROOT/'.build-tools'))
    import PyInstaller.__main__
    excluded=['matplotlib','pandas','scipy','torch','tensorflow','cv2','IPython','pytest','h5py','sympy','notebook','jupyter','setuptools']
    PyInstaller.__main__.run([
        '--noconfirm','--onedir','--windowed','--noupx','--name','Powder Ranger',
        '--icon',str(ROOT/'web'/'powder-ranger-icon.ico'),
        '--distpath',str(ROOT/'release'),'--workpath',str(ROOT/'.build-cache/work'),
        '--specpath',str(ROOT/'.build-cache'),'--add-data',str(ROOT/'web')+os.pathsep+'web',
        '--collect-submodules','webview','--collect-data','webview',
        *[arg for name in excluded for arg in ('--exclude-module',name)],str(ROOT/'desktop_launcher.py')])
