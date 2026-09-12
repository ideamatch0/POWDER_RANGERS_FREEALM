"""One-time extraction of HTTP routing and transactional library selection."""
from pathlib import Path
root=Path(__file__).resolve().parents[1];p=root/'local_app.py';s=p.read_text(encoding='utf-8')
start=s.index('def make_handler(app):');end=s.index('\ndef main():',start)
http='''"""Loopback HTTP adapter; application logic lives in local_app.Application."""
from http.server import BaseHTTPRequestHandler
import json
from pathlib import Path
import socket
import sqlite3
from urllib.parse import parse_qs,urlparse

ROOT=Path(__file__).resolve().parent


'''+s[start:end]
http=http.replace("data = json.loads(self.rfile.read(length))", """if self.headers.get('Transfer-Encoding'):
                    raise ValueError('Chunked requests are not supported.')
                def reject_constant(value):raise ValueError('JSON numbers must be finite.')
                data = json.loads(self.rfile.read(length),parse_constant=reject_constant)
                if not isinstance(data,dict):raise ValueError('A JSON object is required.')""")
http=http.replace("'Adresse inconnue.'","'Unknown address.'").replace("'JSON requis.'","'JSON content type required.'")
http=http.replace("except (ValueError,KeyError,OSError,sqlite3.Error) as error:","except (ValueError,KeyError,OSError,sqlite3.Error,TypeError) as error:")
(root/'http_api.py').write_text(http,encoding='utf-8')
s=s[:start]+s[end:]
start=s.index('@lru_cache(maxsize=220)');end=s.index('\ndef main():',start)
s=s[:start]+s[end:]
s=s.replace('from functools import lru_cache\n','').replace('from urllib.parse import parse_qs, urlparse\n','')
s=s.replace('from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer','from http.server import ThreadingHTTPServer')
s=s.replace('import html\n','').replace('import io\n','').replace('import socket\n','')
s=s.replace('from review import create_review\n','')
s=s.replace('from reporting import ReportTasks, collect_report, create_report','from reporting import ReportTasks, collect_report, create_report\nfrom http_api import make_handler\nfrom previews import preview\nfrom storage import atomic_json\nfrom copy import deepcopy')
s=s.replace("        temporary=self.root/'web_settings.tmp'\n        temporary.write_text(json.dumps({'library':self.library['id'],'by_library':self.preferences}),encoding='utf-8')\n        temporary.replace(self.root/'web_settings.json')","        atomic_json(self.root/'web_settings.json',{'library':self.library['id'],'by_library':self.preferences})")
start=s.index('            self.save_preferences()\n',s.index('    def select_library('))
end=s.index('\n    def import_library(',start)
block=s[start:end]
capture="""            attributes=('library','source','config','acquisition_step','min_consecutive','gallery','dataset','gray_calibration','aalto_result','project','error','progress','revision','preferences')
            previous={name:getattr(self,name) for name in attributes}
            previous['preferences']=deepcopy(self.preferences)
            try:
"""
s=s[:start]+capture+'\n'.join('    '+line if line else line for line in block.splitlines())+"""
            except Exception:
                for name,value in previous.items():setattr(self,name,value)
                self._acquisition_events_cache=None;self._persistence_cache=None
                raise
"""+s[end:]
# Cancellation is an expected outcome, not a processing error.
needle="            except Exception as error:\n                with self.lock:\n                    self.error=str(error);self.progress['stage']='erreur';self.running=False"
s=s.replace(needle,"            except InterruptedError:\n                with self.lock:self.error=None;self.progress['stage']='interrompu';self.running=False\n"+needle)
needle="        except Exception as error:\n            with self.lock:\n                self.error=str(error);self.progress['stage']='erreur';self.running=False"
s=s.replace(needle,"        except InterruptedError:\n            with self.lock:self.error=None;self.progress['stage']='interrompu';self.running=False\n"+needle)
p.write_text(s,encoding='utf-8')
