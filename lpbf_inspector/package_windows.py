"""Package a verified build and its third-party notices for distribution."""
from pathlib import Path
import hashlib
import importlib.metadata as metadata
import json
import sys
import zipfile
from desktop_launcher import APP_VERSION

ROOT=Path(__file__).resolve().parent
if __name__=='__main__':
    release=ROOT/'release';exe=release/'Powder Ranger.exe'
    check=json.loads((ROOT/'research/windows-binary-test.json').read_text(encoding='utf-8'))
    assert check['ok'] and check['frozen'] and Path(check['executable'])==exe
    assert check['version']==APP_VERSION,'The tested binary must match the application version'
    assert (ROOT/'research/windows-binary-test.json').stat().st_mtime>=exe.stat().st_mtime,'Test the latest binary before packaging'
    licenses=[]
    for name in ('numpy','Pillow'):
        dist=metadata.distribution(name)
        for file in dist.files:
            if '.dist-info/' in str(file) and 'license' in str(file).lower():
                path=dist.locate_file(file)
                if path.is_file():licenses.append((name+' '+dist.version+' / '+path.name,path.read_text(encoding='utf-8')))
    for label,path in [('Python',Path(sys.base_prefix)/'LICENSE.txt'),
                       ('Tcl 8.6.12 / https://github.com/tcltk/tcl/blob/core-8-6-12/license.terms',ROOT/'research/tcl-8.6.12-license.terms'),
                       ('Tk',Path(sys.base_prefix)/'tcl/tk8.6/license.terms')]:
        licenses.append((label,path.read_text(encoding='utf-8')))
    candidates=list((ROOT/'.build-tools').glob('pyinstaller-*.dist-info/licenses/*'))
    assert candidates,'Include the PyInstaller bootloader license and exception'
    licenses.extend(('PyInstaller / '+p.name,p.read_text(encoding='utf-8')) for p in candidates if p.is_file())
    notice=release/'THIRD_PARTY_NOTICES.txt'
    notice.write_text(f'Powder Ranger {APP_VERSION} includes the following third-party software.\nThe NumPy and Pillow notices also cover libraries in their binary wheels.\n\n'+
                      '\n\n'.join('='.ljust(72,'=')+'\n'+title+'\n'+'='.ljust(72,'=')+'\n'+body for title,body in licenses),encoding='utf-8')
    guide=release/'QUICK_START_EN.md';guide.write_bytes((ROOT/'WINDOWS_QUICK_START.md').read_bytes())
    archive=release/f'Powder_Ranger_{APP_VERSION}_Windows_x64_EN.zip'
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for path in [exe,guide,notice]:z.write(path,'Powder Ranger/'+path.name)
    digests={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [exe,archive]}
    (release/'SHA256SUMS.txt').write_text(''.join(v+'  '+k+'\n' for k,v in digests.items()),encoding='ascii')
    print(json.dumps({'files':[{ 'name':p.name,'bytes':p.stat().st_size,'sha256':digests[p.name]} for p in [exe,archive]],'acceptance':check},indent=2))
