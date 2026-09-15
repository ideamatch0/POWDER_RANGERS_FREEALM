"""Windows launcher. Frozen builds include Python, NumPy, Pillow and the web UI."""
from __future__ import annotations
import argparse
from dataclasses import asdict
import http.client
import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import traceback
import webbrowser

APP_VERSION='0.3.7'


def data_folder(override=None):
    if override:return Path(override).expanduser().resolve()
    return Path(os.environ.get('LOCALAPPDATA',str(Path.home()/'AppData/Local')))/'PowderRanger'


def install_current_executable():
    """Install for the current Windows user, without requiring elevation."""
    if not getattr(sys,'frozen',False):raise ValueError('Installation is available from the packaged Windows executable.')
    source=Path(sys.executable).resolve()
    primary=Path(os.environ['LOCALAPPDATA'])/'Programs'/'Powder Ranger'
    fallback=data_folder()/'App'
    fallback_notice=None
    def copy_to(folder):
        folder.mkdir(parents=True,exist_ok=True)
        target=folder/'Powder Ranger.exe'
        if source!=target.resolve():
            # Folder builds require the runtime beside the executable. Copy it
            # before publishing the executable or creating any shortcuts.
            runtime=source.parent/'_internal'
            if runtime.is_dir():
                shutil.copytree(runtime,folder/'_internal',dirs_exist_ok=True)
            temporary=folder/'Powder Ranger.installing.exe'
            try:
                shutil.copy2(source,temporary)
                os.replace(temporary,target)
            finally:
                if temporary.exists():temporary.unlink(missing_ok=True)
        return target
    try:
        programs=primary;target=copy_to(primary)
    except PermissionError:
        programs=fallback;target=copy_to(fallback)
        fallback_notice='Windows refused the standard Programs folder, so Powder Ranger was installed in its local application folder. It will work normally.'
    # Literal PowerShell strings escape single quotes. No values are interpolated as code.
    def literal(value):return "'"+str(value).replace("'","''")+"'"
    script=("$shell = New-Object -ComObject WScript.Shell\n"
            "$desktop = [Environment]::GetFolderPath('Desktop')\n"
            "$menu = [Environment]::GetFolderPath('Programs')\n"
            "foreach ($folder in @($desktop, $menu)) {\n"
            "  $shortcut = $shell.CreateShortcut((Join-Path $folder 'Powder Ranger.lnk'))\n"
            "  $shortcut.TargetPath = "+literal(target)+"\n"
            "  $shortcut.WorkingDirectory = "+literal(programs)+"\n"
            "  $shortcut.Description = 'Powder Ranger - Every layer under watch.'\n"
            "  $shortcut.Save()\n}\n")
    import base64
    encoded=base64.b64encode(script.encode('utf-16-le')).decode('ascii')
    result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-EncodedCommand',encoded],
                          creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0),capture_output=True,text=True,timeout=25)
    if result.returncode:
        shortcut_notice='The application was installed, but Windows could not create its shortcuts. You can run it from:\n'+str(target)
        return target,(fallback_notice+'\n\n' if fallback_notice else '')+shortcut_notice
    return target,fallback_notice


def self_test(output,profile):
    """Headless acceptance check executed by the actual packaged binary."""
    from PIL import Image
    import numpy as np
    from inspector import Config
    from local_app import Application,ThreadingHTTPServer,make_handler
    started=time.monotonic();server=None;record={'version':APP_VERSION,'frozen':bool(getattr(sys,'frozen',False)),'executable':sys.executable}
    try:
        import tkinter
        tcl=tkinter.Tcl()
        record['tcl_version']=str(tcl.eval('info patchlevel'))
        if getattr(sys,'frozen',False):
            assert (Path(os.environ['TK_LIBRARY'])/'tk.tcl').is_file(),'Bundled Tk scripts are missing'
        del tcl
        profile.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='acceptance-',dir=profile) as directory:
            root=Path(directory);app=Application(root)
            assert app.dataset.get('empty') and app.dataset['images']==0
            source=root/'test-images';source.mkdir()
            for layer in range(1,9):
                for phase in ('spread','fused'):
                    a=np.full((100,100),90,np.uint8)
                    if phase=='fused':a[30:60,30:60]=100+np.indices((30,30)).sum(axis=0)%3*60
                    if layer==7:a[64:80,64:80]=240
                    Image.fromarray(a).save(source/f'cam1_layer{layer}_{phase}.jpg',quality=100)
            entry=app.catalog.add({'path':str(source),'name':'Executable acceptance test','config':asdict(Config())},lambda **kw:None,lambda:False)
            app.select_library(entry['id']);app.start({'threshold':12,'tile':16,'analysis_phase':'both'})
            deadline=time.monotonic()+60
            while app.running and time.monotonic()<deadline:time.sleep(.05)
            assert not app.running and not app.error,app.error
            event=app.events({'run':[app.key]})['items'][0];detail=app.detail(app.key,event['id'])
            app.decide({'run':app.key,'id':event['id'],'snapshot':detail['event']['snapshot'],'status':'retenue','comment':'Standalone binary check'})
            report=app.report(app.key,{'job_name':'Standalone acceptance report','template':'summary','planes':32})
            assert b'data:image/png;base64,' in report and b'Standalone acceptance report' in report
            server=ThreadingHTTPServer(('127.0.0.1',0),make_handler(app));threading.Thread(target=server.serve_forever,daemon=True).start()
            assets={}
            for route in ('/','/workspace','/reports.js','/reports.css','/powder-ranger-icon.svg','/api/state'):
                c=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=20)
                try:
                    c.request('GET',route);response=c.getresponse();data=response.read();assert response.status==200,(route,response.status);assets[route]=len(data)
                finally:c.close()
            server.shutdown();server.server_close();server=None
            record.update(ok=True,measured=app.state()['analysis']['measured'],report_bytes=len(report),assets=assets)
    except Exception:
        record.update(ok=False,error=traceback.format_exc())
    finally:
        if server:server.shutdown();server.server_close()
        record['seconds']=round(time.monotonic()-started,2)
        Path(output).write_text(json.dumps(record,indent=2),encoding='utf-8')
    return 0 if record['ok'] else 1


def open_desktop_window(url):
    import webview
    webview.create_window('Powder Ranger', url, width=1440, height=920, min_size=(1100,720))
    webview.start()


def run_browser_launcher(url,app,server,profile,args):
    import tkinter as tk
    from tkinter import messagebox
    window=tk.Tk();window.title('Powder Ranger');window.geometry('475x325');window.resizable(False,False);window.configure(bg='#0e1720')
    if args.install:
        target,notice=install_current_executable();messagebox.showinfo('Powder Ranger installed','Installed to:\n'+str(target)+('\n\n'+notice if notice else '\n\nDesktop and Start menu shortcuts are ready.'),parent=window)
    def label(text,size,color='#e4edf3'):
        tk.Label(window,text=text,font=('Segoe UI',size),fg=color,bg='#0e1720').pack(pady=(10,0))
    label('POWDER RANGER',22);label('Every layer under watch.',10,'#61d8cf');label('Local server is running',11)
    label('Keep this window open while using the application.',9,'#9eb2c3')
    def button(text,command):tk.Button(window,text=text,command=command,font=('Segoe UI',10),bg='#1d3e4c',fg='white',activebackground='#2f6171',relief='flat',padx=14,pady=6).pack(pady=(10,0))
    button('Open Powder Ranger',lambda:webbrowser.open(url))
    def install():
        try:
            target,notice=install_current_executable()
            message='Installed to:\n'+str(target)+('\n\n'+notice if notice else '\n\nShortcuts are available on your Desktop and Start menu.')
            messagebox.showinfo('Installation complete',message,parent=window)
        except Exception as error:logging.exception('Install failed');messagebox.showerror('Installation failed',str(error),parent=window)
    if getattr(sys,'frozen',False):button('Install on this computer',install)
    def close():
        if app.running:
            if not messagebox.askyesno('Stop analysis?','An analysis is running. Stop it and close Powder Ranger?',parent=window):return
            app.stop_event.set()
        for task in getattr(app,'_report_tasks',{}).values():task['cancel'].set()
        if app.running:window.after(150,finish_close)
        else:window.destroy()
    def finish_close():
        if app.running:window.after(150,finish_close)
        else:window.destroy()
    window.protocol('WM_DELETE_WINDOW',close)
    window.after(350,lambda:webbrowser.open(url));window.mainloop()


def main():
    parser=argparse.ArgumentParser(description='Powder Ranger desktop launcher')
    parser.add_argument('--data-dir');parser.add_argument('--self-test',metavar='RESULT_JSON');parser.add_argument('--install',action='store_true');parser.add_argument('--browser',action='store_true')
    args=parser.parse_args();profile=data_folder(args.data_dir);profile.mkdir(parents=True,exist_ok=True)
    if args.self_test:return self_test(args.self_test,profile)
    from local_app import Application,ThreadingHTTPServer,make_handler
    log=RotatingFileHandler(profile/'launcher.log',maxBytes=500000,backupCount=2,encoding='utf-8');logging.basicConfig(level=logging.INFO,handlers=[log],force=True)
    lock=None;server=None
    try:
        if os.name=='nt':
            import msvcrt
            lock=(profile/'instance.lock').open('a+b');lock.seek(0)
            if lock.read(1)==b'':lock.write(b'0');lock.flush()
            lock.seek(0)
            try:msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
            except OSError:
                for _ in range(20):
                    try:
                        port=int(json.loads((profile/'instance.json').read_text())['port'])
                        if not 1<=port<=65535:raise ValueError('Invalid port')
                        connection=http.client.HTTPConnection('127.0.0.1',port,timeout=1)
                        try:connection.request('GET','/api/state');response=connection.getresponse();response.read();assert response.status==200
                        finally:connection.close()
                        if args.browser:webbrowser.open(f'http://127.0.0.1:{port}/')
                        else:open_desktop_window(f'http://127.0.0.1:{port}/')
                        return 0
                    except (OSError,ValueError,AssertionError):time.sleep(.2)
                raise OSError('Powder Ranger is already starting. Try opening it again in a few seconds.')
        app=Application(profile);server=ThreadingHTTPServer(('127.0.0.1',0),make_handler(app))
        url=f'http://127.0.0.1:{server.server_port}/'
        (profile/'instance.json').write_text(json.dumps({'pid':os.getpid(),'port':server.server_port}),encoding='utf-8')
        threading.Thread(target=server.serve_forever,daemon=True).start()
        if args.browser or args.install:run_browser_launcher(url,app,server,profile,args)
        else:
            try:open_desktop_window(url)
            except Exception:
                logging.exception('Desktop window failed; falling back to browser launcher')
                run_browser_launcher(url,app,server,profile,args)
    except Exception as error:
        logging.exception('Launcher failed')
        try:
            import tkinter as tk
            from tkinter import messagebox
            window=tk.Tk();window.withdraw();messagebox.showerror('Powder Ranger',str(error)+'\n\nLog: '+str(profile/'launcher.log'),parent=window);window.destroy()
        except Exception:pass
        return 1
    finally:
        if server:server.shutdown();server.server_close()
        if lock:lock.close()
        logging.getLogger().removeHandler(log);log.close()
    return 0


if __name__=='__main__':
    import multiprocessing
    multiprocessing.freeze_support()
    raise SystemExit(main())
