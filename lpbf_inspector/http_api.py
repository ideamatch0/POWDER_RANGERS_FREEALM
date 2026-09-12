"""Loopback HTTP adapter; application logic lives in local_app.Application."""
from http.server import BaseHTTPRequestHandler
import json
from pathlib import Path
import socket
import sqlite3
from urllib.parse import parse_qs,urlparse

ROOT=Path(__file__).resolve().parent


def make_handler(app):
    class Handler(BaseHTTPRequestHandler):
        protocol_version='HTTP/1.1'

        def setup(self):
            super().setup()
            self.connection.settimeout(30)
            self.connection.setsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY,1)

        def log_message(self, *args):
            pass

        def send(self, data, mime='application/json; charset=utf-8', status=200, filename=None, headers=None):
            if not isinstance(data,bytes):
                data = json.dumps(data,ensure_ascii=False).encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type',mime)
            self.send_header('Content-Length',str(len(data)))
            self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            for name,value in (headers or {}).items():self.send_header(name,str(value))
            if status>=400:
                self.send_header('Connection','close')
                self.close_connection=True
            if filename:
                self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
            self.end_headers()
            try:
                self.wfile.write(data)
                self.wfile.flush()
            except (BrokenPipeError,ConnectionResetError,ConnectionAbortedError):
                self.close_connection=True

        def valid_host(self):
            expected = {f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}'}
            return self.headers.get('Host') in expected

        def do_GET(self):
            if not self.valid_host():
                return self.send({'error':'Host not allowed.'}, status=403)
            route = urlparse(self.path)
            q = parse_qs(route.query)
            try:
                if route.path=='/':
                    self.send((ROOT/'web'/'home.html').read_bytes(),'text/html; charset=utf-8')
                elif route.path in {'/workspace','/workspace/'}:
                    self.send((ROOT/'web'/'index.html').read_bytes(),'text/html; charset=utf-8')
                elif route.path=='/stack.js':
                    self.send((ROOT/'web'/'stack.js').read_bytes(),'text/javascript; charset=utf-8')
                elif route.path in {'/gallery.js','/libraries.js','/dark.css','/home.css','/home.js','/reports.js','/reports.css'}:
                    self.send((ROOT/'web'/route.path[1:]).read_bytes(),'text/css; charset=utf-8' if route.path.endswith('.css') else 'text/javascript; charset=utf-8')
                elif route.path=='/api/state':
                    self.send(app.state())
                elif route.path=='/api/events':
                    self.send(app.events(q))
                elif route.path=='/api/event':
                    self.send(app.detail(q.get('run',[''])[0],q['id'][0],q.get('context',['standard'])[0]))
                elif route.path=='/api/image':
                    event=q['event'][0] if 'event' in q else None
                    self.send(app.image(q.get('run',[''])[0],int(q['id'][0]),event,q.get('context',['standard'])[0]),'image/jpeg')
                elif route.path=='/api/reports/context':
                    self.send(app.report_context(q.get('run',[''])[0]))
                elif route.path=='/api/reports/status':
                    self.send(app.report_status(q.get('id',[''])[0]))
                elif route.path=='/api/reports/file':
                    content,filename=app.report_file(q.get('id',[''])[0])
                    self.send(content,'text/html; charset=utf-8',filename=filename if q.get('download',[''])[0]=='1' else None,
                              headers={'Content-Security-Policy':"default-src 'none'; img-src data:; style-src 'unsafe-inline'; base-uri 'none'; frame-ancestors 'self'"})
                elif route.path=='/api/report':
                    self.send(app.report(q.get('run',[''])[0]),'text/html; charset=utf-8',filename='rapport_lpbf.html')
                elif route.path=='/api/stack':
                    self.send(app.stack(q.get('run',[''])[0],q.get('phase',['fusion'])[0],q.get('region',['full'])[0],q.get('camera',[None])[0]))
                elif route.path=='/api/stack-image':
                    self.send(app.stack_image(q.get('run',[''])[0],int(q['id'][0]),q.get('region',['full'])[0]),'image/jpeg')
                elif route.path=='/api/shape-image':
                    data,stats=app.shape_image(q.get('run',[''])[0],int(q['id'][0]),q.get('region',['full'])[0],q.get('contrast',['3'])[0])
                    self.send(data,'image/png',headers={'X-Shape-Coverage':stats['coverage_percent'],'X-Shape-Threshold':stats['threshold']})
                elif route.path=='/api/gallery':
                    self.send(app.gallery_items(q.get('run',[''])[0],int(q.get('offset',['0'])[0]),q.get('job',[''])[0],q.get('detected',[''])[0]=='1'))
                elif route.path=='/api/gallery/detail':
                    self.send(app.gallery_detail(q.get('run',[''])[0],int(q['id'][0])))
                elif route.path=='/api/gallery/image':
                    if 'annotation' in q:raise ValueError('Researcher annotations are hidden. Use an automatically detected indication.')
                    self.send(app.gallery_image(q.get('run',[''])[0],int(q['id'][0]),int(q['prediction'][0]) if 'prediction' in q else None,int(q['anchor'][0]) if 'anchor' in q else None),'image/jpeg')
                elif route.path=='/api/gallery/report':
                    self.send(app.gallery_report(q.get('run',[''])[0]),'text/html; charset=utf-8',filename='rapport_aalto.html')
                elif route.path in {'/api/gallery/evaluation','/api/analysis-summary'}:
                    with app.lock:
                        app.require_run(q.get('run',[''])[0])
                        state=app.state()
                        if not state['analysis']:raise ValueError('Analysis unavailable.')
                        self.send({'analysis':state['analysis'],'calibration':state['calibration'],'review_settings':state['review_settings']},filename='analyse_job.json')
                elif route.path=='/favicon.ico':
                    self.send(b'', 'image/x-icon', status=204)
                elif route.path in {'/powder-ranger-icon.svg','/powder-ranger-logo.svg'}:
                    self.send((ROOT/'web'/route.path[1:]).read_bytes(),'image/svg+xml')
                else:
                    self.send({'error':'Unknown address.'},status=404)
            except (ValueError,KeyError,OSError,sqlite3.Error,TypeError) as error:
                self.send({'error':str(error)},status=400)

        def do_POST(self):
            origin = self.headers.get('Origin')
            allowed = {f'http://127.0.0.1:{self.server.server_port}',f'http://localhost:{self.server.server_port}'}
            if not self.valid_host() or (origin is not None and origin not in allowed):
                return self.send({'error':'Origin not allowed.'},status=403)
            if self.headers.get_content_type()!='application/json':
                return self.send({'error':'JSON content type required.'},status=415)
            try:
                length = int(self.headers.get('Content-Length','0'))
                if not 0 < length <= 40000:
                    raise ValueError('Request too large or empty.')
                if self.headers.get('Transfer-Encoding'):
                    raise ValueError('Chunked requests are not supported.')
                def reject_constant(value):raise ValueError('JSON numbers must be finite.')
                data = json.loads(self.rfile.read(length),parse_constant=reject_constant)
                if not isinstance(data,dict):raise ValueError('A JSON object is required.')
                if self.path=='/api/analyze':
                    self.send(app.start(data))
                elif self.path=='/api/calibrate':
                    self.send(app.calibrate_job(data))
                elif self.path=='/api/libraries/select':
                    self.send(app.select_library(data['id']))
                elif self.path=='/api/libraries/import':
                    self.send(app.import_library(data))
                elif self.path=='/api/libraries/browse':
                    import tkinter as tk
                    from tkinter import filedialog
                    root=tk.Tk();root.withdraw();root.attributes('-topmost',True)
                    try:
                        selected=filedialog.askdirectory(title='Choose the LPBF image folder',parent=root,mustexist=True)
                        self.send({'path':selected})
                    finally:root.destroy()
                elif self.path=='/api/stop':
                    app.stop_event.set()
                    self.send({'stopping':True})
                elif self.path=='/api/reports/start':
                    self.send(app.start_report(data))
                elif self.path=='/api/reports/cancel':
                    self.send(app.cancel_report(data.get('id')))
                elif self.path=='/api/decision':
                    self.send(app.decide(data))
                elif self.path=='/api/review-settings':
                    self.send(app.set_review_settings(data))
                elif self.path=='/api/gallery/decision':
                    self.send(app.gallery_decide(data))
                else:
                    self.send({'error':'Unknown address.'},status=404)
            except (ValueError,KeyError,OSError,sqlite3.Error,TypeError) as error:
                self.send({'error':str(error)},status=400)
    return Handler

