from dataclasses import asdict
import hashlib
import http.client
import io
import json
from pathlib import Path
import re
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image
from inspector import Config, analyze
from local_app import Application, ThreadingHTTPServer, make_handler
from reporting import collect_report, create_report, options_for, TEMPLATES
from report_volume import Projection, render_volume, score_color


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.source=self.root/'images';self.source.mkdir()
        config=Config(tile_px=16)
        (self.root/'config.nist_sample.json').write_text(json.dumps(asdict(config)))
        for layer in range(1,9):
            for phase in ('spread','fused'):
                a=np.full((100,100),90,np.uint8)
                if phase=='fused':a[30:60,30:60]=100+np.indices((30,30)).sum(axis=0)%3*60
                if layer==7:a[64:80,64:80]=240
                Image.fromarray(a).save(self.source/f'cam1_layer{layer}_{phase}.jpg',quality=100)
        analyze(self.source,self.root/'results_nist_16bit',config)
        self.app=Application(self.root,self.source)
        events=self.app.events({'run':[self.app.key]})['items']
        self.kept=next(e for e in events if e['phase']=='etalement')
        self.other=next(e for e in events if e['phase']=='fusion')
        self.decide(self.kept,'retenue','Retained observation <script>unsafe()</script>')
        self.decide(self.other,'ecartee','DISMISSED_SECRET')

    def decide(self,event,status,comment=''):
        d=self.app.detail(self.app.key,event['id'])
        self.app.decide({'run':self.app.key,'id':event['id'],'snapshot':d['event']['snapshot'],'status':status,'comment':comment})

    def wait(self,identifier):
        deadline=time.monotonic()+10
        while time.monotonic()<deadline:
            status=self.app.report_status(identifier)
            if status['status']!='running':return status
            time.sleep(.01)
        self.fail('Report worker did not finish')

    def test_snapshot_keeps_only_retained_and_uses_fusion_shape_at_spreading_height(self):
        ctx=self.app.report_context(self.app.key)
        snap=collect_report(self.app,self.app.key,expected_revision=ctx['revision'])
        self.assertEqual(len(snap['details']),1)
        scene=snap['scenes'][0]
        self.assertTrue(scene['cyan']);self.assertEqual(scene['phase'],'etalement')
        self.assertTrue(all(f['path'].endswith('_fused.jpg') for f in scene['frames']))
        self.assertEqual([e['id'] for e in scene['events']],[self.kept['id']])
        self.assertAlmostEqual(scene['events'][0]['position'],.42)
        self.decide(self.kept,'ecartee','Changed after snapshot')
        self.assertEqual(snap['details'][0]['event']['status'],'retenue')
        with self.assertRaisesRegex(ValueError,'review has changed'):
            collect_report(self.app,self.app.key,expected_revision=ctx['revision'])

    def test_templates_escape_content_embed_assets_and_leave_sources_unchanged(self):
        before={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in self.source.iterdir()}
        snap=collect_report(self.app,self.app.key,{'job_name':'Build <A>','planes':32})
        volume=render_volume(snap['scenes'][0],255,planes=32)
        for template in TEMPLATES:
            snap['options']['template']=template
            with patch('reporting.render_volume',return_value=volume):html=create_report(snap).decode()
            self.assertTrue('lang="en"' in html)
            self.assertTrue('Build &lt;A&gt;' in html and '&lt;script&gt;' in html)
            self.assertFalse('<script>' in html or 'DISMISSED_SECRET' in html)
            self.assertEqual('class="indication"' in html,template!='summary')
            self.assertTrue(all(url.startswith('data:') for url in re.findall(r'<img[^>]+src="([^"]+)"',html)))
            self.assertTrue('data:image/png;base64,' in html and 'Cyan shape' in html)
        self.assertEqual(before,{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in self.source.iterdir()})

    def test_rendered_markers_are_visible_over_the_cyan_volume(self):
        scene=collect_report(self.app,self.app.key)['scenes'][0]
        result=render_volume(scene,255,planes=32)
        self.assertEqual(result['markers'],1);self.assertEqual(result['loaded'],8)
        color=np.array(score_color(scene['events'][0]['priority_score']))
        with Image.open(io.BytesIO(result['oblique'])) as img:a=np.array(img)
        self.assertGreater(np.all(a==color,axis=2).sum(),10)
        self.assertGreater(((a[:,:,1]>a[:,:,0]*1.5)&(a[:,:,2]>a[:,:,0]*1.5)&(a[:,:,1]>50)).sum(),100)
        p=Projection(scene,top=True)
        self.assertLess(p.point(.1,.1,.1)[0],p.point(.9,.1,.1)[0])
        self.assertLess(p.point(.1,.1,.1)[1],p.point(.1,.9,.1)[1])

    def test_report_options_are_bounded_and_3d_is_optional(self):
        for data in ({'planes':10000},{'template':'<script>'},{'job_name':''},{'date':'tomorrow'},{'contrast':99},{'include_3d':'yes'}):
            with self.assertRaises(ValueError):options_for(data,'Build')
        snap=collect_report(self.app,self.app.key,{'include_3d':False})
        self.assertEqual(snap['scenes'],[])
        self.assertFalse('data:image/png;base64,' in create_report(snap).decode())

    def test_report_rejects_sources_changed_after_snapshot(self):
        snap=collect_report(self.app,self.app.key)
        source=Path(snap['details'][0]['frames'][1]['path'])
        Image.new('L',(100,100),210).save(source)
        with self.assertRaisesRegex(ValueError,'Source image changed'):create_report(snap)

    def test_review_and_stack_reject_named_sources_changed_since_analysis(self):
        frames=self.app.stack(self.app.key,'fusion')['frames']
        frame=frames[0]['id'];db=self.app.database()
        source=Path(db.execute('SELECT path FROM frames WHERE id=?',(frame,)).fetchone()[0]);db.close()
        Image.new('L',(100,100),210).save(source)
        for method in (self.app.image,self.app.stack_image,self.app.shape_image):
            with self.subTest(method=method.__name__),self.assertRaisesRegex(ValueError,'Source image changed'):
                method(self.app.key,frame)

    def test_report_rejects_sources_changed_since_temporal_analysis(self):
        detail=self.app.detail(self.app.key,self.kept['id'])
        source=self.source/detail['frames'][1]['name']
        Image.new('L',(100,100),210).save(source)
        with self.assertRaisesRegex(ValueError,'Source image changed'):collect_report(self.app,self.app.key)

    def test_async_export_and_http_download_are_self_contained(self):
        task=self.app.start_report({'run':self.app.key,'options':{'job_name':'Build / A','template':'summary','planes':32}})
        status=self.wait(task['id']);self.assertEqual(status['status'],'ready',status)
        self.assertEqual(status['progress'],100)
        data,name=self.app.report_file(task['id']);self.assertTrue(name.startswith('Powder_Ranger_Build_A_'))
        server=ThreadingHTTPServer(('127.0.0.1',0),make_handler(self.app))
        threading.Thread(target=server.serve_forever,daemon=True).start()
        try:
            conn=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=5)
            try:
                conn.request('GET','/api/reports/file?id='+task['id']+'&download=1')
                response=conn.getresponse();self.assertEqual(response.status,200)
                self.assertIn(name,response.getheader('Content-Disposition'))
                self.assertIn("default-src 'none'",response.getheader('Content-Security-Policy'))
                self.assertEqual(response.read(),data)
            finally:conn.close()
        finally:server.shutdown();server.server_close()

    def test_cancel_does_not_publish_a_partial_report(self):
        started=threading.Event();release=threading.Event()
        def blocked(snapshot,progress):
            started.set();release.wait(5);progress('Test checkpoint');return b'partial'
        with patch('reporting.create_report',side_effect=blocked):
            task=self.app.start_report({'run':self.app.key})
            try:
                self.assertTrue(started.wait(3))
                with self.assertRaisesRegex(ValueError,'already being generated'):self.app.start_report({'run':self.app.key})
                self.app.cancel_report(task['id'])
            finally:release.set()
            self.assertEqual(self.wait(task['id'])['status'],'cancelled')
        with self.assertRaisesRegex(ValueError,'not ready'):self.app.report_file(task['id'])
        self.assertFalse((self.root/'report_exports').exists())


if __name__=='__main__':unittest.main()
