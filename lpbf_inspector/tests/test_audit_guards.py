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
