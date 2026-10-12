from dataclasses import asdict
import http.client
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from PIL import Image
from inspector import Config
from local_app import Application, make_handler, ThreadingHTTPServer, preview


class AuditGuards(unittest.TestCase):
    def test_acquisition_calibration_skips_unreadable_images(self):
        from job_analysis import calibrate
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder);records=[]
            for i in range(22):
                path=source/f'{i}.png';Image.new('L',(32,32),100).save(path)
                records.append({'id':i,'job':'build','name':path.name,'counter':i})
            (source/'0.png').write_bytes(b'not an image')
            result=calibrate(source,records,Config(),1,'test')
            self.assertEqual(result['sample_images'],19);self.assertEqual(result['mean_gray'],100)
            self.assertEqual(result['errors'][0]['id'],0);self.assertNotIn(0,result['channels']['0']['sample_ids'])

    def test_atomic_storage_does_not_replace_valid_file_on_serialization_error(self):
        from storage import atomic_json
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'settings.json';atomic_json(p,{'value':1})
            with self.assertRaises(ValueError):atomic_json(p,{'value':float('nan')})
            self.assertEqual(json.loads(p.read_text()),{'value':1})
            self.assertEqual(list(Path(folder).glob('*.tmp')),[])

    def test_preview_refreshes_when_same_path_changes(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'frame.png';Image.new('L',(80,80),20).save(p)
            first=preview(str(p),255);stamp=p.stat().st_mtime_ns
            Image.new('L',(80,80),220).save(p);os.utime(p,ns=(stamp+10000000,stamp+10000000))
            self.assertNotEqual(first,preview(str(p),255))

    def test_failed_selection_preserves_active_job(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);a=Application(root);before=a.state()
            a.catalog.entries['bad']={'id':'bad','name':'Missing folder','source':str(root/'missing'),'mode':'temporal','config':asdict(Config()),'default_roi':{}}
            with self.assertRaises(ValueError):a.select_library('bad')
            after=a.state()
            self.assertEqual(before['dataset'],after['dataset']);self.assertEqual(a.library['id'],'empty')
            self.assertEqual(before['run'],after['run'])

    def test_startup_with_all_saved_sources_missing_opens_import_screen(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            entry={'id':'local_missing','name':'Offline job','source':str(root/'offline'),
                   'mode':'temporal','config':asdict(Config()),'default_roi':{}}
            catalog=json.dumps([entry])
            settings=json.dumps({'library':entry['id'],'by_library':{entry['id']:{'threshold':24}}})
            (root/'libraries.json').write_text(catalog,encoding='utf-8')
            (root/'web_settings.json').write_text(settings,encoding='utf-8')
            app=Application(root)
            state=app.state()
            self.assertTrue(state['dataset']['empty'])
            self.assertEqual(state['dataset']['images'],0)
            self.assertIn(entry['source'],state['error'])
            self.assertIn(entry['id'],app.catalog.entries)
            self.assertEqual((root/'libraries.json').read_text(encoding='utf-8'),catalog)
            self.assertEqual((root/'web_settings.json').read_text(encoding='utf-8'),settings)
            # Reconnecting the drive restores the requested job on the next start.
            (root/'offline').mkdir()
            Image.new('L',(32,32),100).save(root/'offline/cam1_layer1_spread.jpg')
            restored=Application(root)
            self.assertEqual(restored.library['id'],entry['id'])
            self.assertEqual(restored.dataset['images'],1)
            self.assertIsNone(restored.error)

    def test_startup_with_missing_source_preserves_other_jobs_without_selecting_them(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);source=root/'available';source.mkdir()
            Image.new('L',(32,32),100).save(source/'cam1_layer1_spread.jpg')
            missing={'id':'local_missing','name':'Offline job','source':str(root/'offline'),
                     'mode':'temporal','config':asdict(Config()),'default_roi':{}}
            valid={**missing,'id':'local_valid','name':'Available job','source':str(source)}
            (root/'libraries.json').write_text(json.dumps([missing,valid]),encoding='utf-8')
            (root/'web_settings.json').write_text(json.dumps({'library':missing['id'],
                'by_library':{missing['id']:{'threshold':24},valid['id']:{'threshold':18}}}),encoding='utf-8')
            app=Application(root)
            self.assertTrue(app.dataset['empty'])
            self.assertIn(valid['id'],app.catalog.entries)
            self.assertIn(missing['source'],app.error)
            app.select_library(valid['id'])
            self.assertEqual(app.library['id'],valid['id'])
            self.assertEqual(app.dataset['images'],1)
            self.assertEqual(app.config.min_change_gray,18)
            self.assertIsNone(app.error)
            self.assertEqual(app.preferences[missing['id']]['threshold'],24)

    def test_saved_import_screen_can_open_with_offline_catalog_entries(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);source=root/'exists';source.mkdir()
            entry={'id':'local_job','name':'Job','source':str(source),'mode':'temporal',
                   'config':asdict(Config()),'default_roi':{}}
            (root/'libraries.json').write_text(json.dumps([entry]),encoding='utf-8')
            (root/'web_settings.json').write_text(json.dumps({'library':'empty'}),encoding='utf-8')
            app=Application(root)
            self.assertTrue(app.dataset['empty'])
            self.assertIn(entry['id'],app.catalog.entries)

    def test_saved_gallery_without_provenance_opens_import_screen(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);source=root/'gallery';source.mkdir()
            entry={'id':'local_gallery','name':'Missing gallery metadata','source':str(source),
                   'mode':'gallery','job':'job','config':asdict(Config()),'default_roi':{}}
            (root/'libraries.json').write_text(json.dumps([entry]),encoding='utf-8')
            app=Application(root)
            self.assertTrue(app.dataset['empty'])
            self.assertIn(str(source),app.error)

    def test_malformed_configuration_reports_validation_errors(self):
        for kwargs in [{'phase_aliases':[]},{'roi_by_camera':[]},{'roi_by_camera':{'cam1':None}},{'filename_regex':42},{'filename_regex':'['},{'first_layer_z_mm':'bad'}]:
            with self.subTest(kwargs=kwargs),self.assertRaises(ValueError):Config(**kwargs).validate()

    def test_non_object_json_is_rejected_without_a_connection_crash(self):
        with tempfile.TemporaryDirectory() as folder:
            app=Application(Path(folder));server=ThreadingHTTPServer(('127.0.0.1',0),make_handler(app))
            threading.Thread(target=server.serve_forever,daemon=True).start()
            try:
                for body in ('[]','null','true','"abc"','{"threshold":NaN}'):
                    c=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=3)
                    try:
                        c.request('POST','/api/analyze',body,{'Content-Type':'application/json'})
                        response=c.getresponse();self.assertEqual(response.status,400);self.assertIn('error',json.loads(response.read()))
                    finally:c.close()
            finally:server.shutdown();server.server_close()


if __name__=='__main__':unittest.main()
