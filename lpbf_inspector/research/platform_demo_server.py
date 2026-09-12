"""Isolated filming profile. Never opens or edits the installed user profile."""
from pathlib import Path
import json, shutil, sys
from http.server import ThreadingHTTPServer
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from local_app import Application
from http_api import make_handler
OUT = ROOT/'output/platform_video'
PROFILE = OUT/'demo_profile'
OUT.mkdir(parents=True, exist_ok=True)
if not PROFILE.exists():
    shutil.copytree(ROOT/'research/desktop_library_restore_2026-09-10/staging', PROFILE)
    libraries = json.loads((PROFILE/'libraries.json').read_text())
    (PROFILE/'libraries.json').write_text(json.dumps([x for x in libraries if x['id']=='local_nist_scan']), encoding='utf-8')
app = Application(PROFILE)
Base = make_handler(app)
class Handler(Base):
    def do_GET(self):
        if self.path.split('?')[0] == '/platform':
            if not self.valid_host(): return self.send({'error':'Host not allowed'},status=403)
            return self.send((OUT/'platform.html').read_bytes(), 'text/html; charset=utf-8')
        return super().do_GET()
server = ThreadingHTTPServer(('127.0.0.1',0),Handler)
(OUT/'server.json').write_text(json.dumps({'port':server.server_port,'profile':str(PROFILE)}))
print(f'http://127.0.0.1:{server.server_port}/platform',flush=True)
server.serve_forever()
