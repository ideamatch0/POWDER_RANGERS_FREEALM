from dataclasses import asdict
import io
import json
from pathlib import Path
import tempfile
import time
import unittest

import numpy as np
from PIL import Image

from inspector import Config, analyze
from local_app import Application, preview
from imaging import context_box
from review import picture
from libraries import inventory


class LocalAppTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root/'images'
        self.source.mkdir()
        config = Config(tile_px=16)
        (self.root/'config.nist_sample.json').write_text(json.dumps(asdict(config)),encoding='utf-8')
        for layer in range(1,9):
            pixels = np.full((80,80),100,np.uint8)
            if layer==7:
                pixels[16:32,16:32]=220
            Image.fromarray(pixels).save(self.source/f'cam1_layer{layer}_spread.jpg',quality=100)
        analyze(self.source,self.root/'results_nist_16bit',config)
        self.app = Application(self.root,self.source)

    def tearDown(self):
        self.app.stop_event.set()
        for _ in range(500):
            if not self.app.running:
                break
            time.sleep(.01)
        self.temp.cleanup()

    def test_review_save_and_report(self):
        key=self.app.key
        listing=self.app.events({'run':[key]})
        self.assertGreater(listing['total'],0)
        detail=self.app.detail(key,listing['items'][0]['id'])
        frame=detail['frames'][1]
        image=self.app.image(key,frame['id'])
        with Image.open(io.BytesIO(image)) as decoded:
            self.assertEqual(decoded.size,(80,80))
        with self.assertRaisesRegex(ValueError,'Keep between'):
            self.app.report(key)
        self.app.decide({'run':key,'id':detail['event']['id'],'snapshot':detail['event']['snapshot'],
                         'status':'retenue','comment':'Test <image>'})
        report=self.app.report(key).decode()
        self.assertIn('Test &lt;image&gt;',report)
        self.assertNotIn('<script>',report)
        self.assertNotIn('class="decision"',report)
        self.assertIn('Close-ups: matching crop',report)
        self.assertIn('Overview',report)
        self.assertEqual(self.app.state()['summary']['indications']['retenue'],1)

    def test_stale_tab_cannot_change_another_analysis(self):
        with self.assertRaisesRegex(ValueError,'changed'):
            self.app.decide({'run':'old','id':1,'status':'retenue'})
        with self.assertRaisesRegex(ValueError,'limits'):
            self.app.start({'threshold':float('nan')})

    def replace_events(self,lengths):
        db=self.app.database()
        with db:
            db.execute('DELETE FROM decisions');db.execute('DELETE FROM events')
            frame=db.execute('SELECT id FROM frames WHERE layer=7').fetchone()[0]
            for duration in lengths:
                db.execute('INSERT INTO events(camera,phase,kind,start_layer,end_layer,peak_frame,box,score) VALUES(?,?,?,?,?,?,?,?)',
                           ('cam1','etalement','changement_local',8-duration,7,frame,'[16,16,32,32]',2))
        db.close()

    def test_persistence_filters_list_stack_report_without_new_analysis(self):
        self.replace_events([1,2,3]);key=self.app.key;before=self.app.state()
        items=self.app.events({'run':[key]})['items']
        for event in items:
            detail=self.app.detail(key,event['id'])
            self.app.decide({'run':key,'id':event['id'],'snapshot':detail['event']['snapshot'],'status':'retenue','comment':'duration-'+str(event['consecutive_count'])})
        state=self.app.set_review_settings({'run':key,'min_consecutive':3})
        self.assertEqual(state['run'],key);self.assertEqual(before['analysis'],state['analysis']);self.assertEqual(before['calibration'],state['calibration'])
        listing=self.app.events({'run':[key]})
        self.assertEqual(listing['before_persistence'],3);self.assertEqual(listing['total'],1)
        self.assertEqual(listing['items'][0]['consecutive_count'],3)
        self.assertEqual(len(self.app.stack(key,'etalement')['events']),1)
        report=self.app.report(key).decode()
        self.assertIn('Minimum persistence: 3',report);self.assertIn('duration-3',report);self.assertNotIn('duration-1',report)
        self.assertEqual(Application(self.root,self.source).min_consecutive,3)
        self.app.set_review_settings({'run':key,'min_consecutive':1})
        self.assertEqual(self.app.events({'run':[key],'status':['retenue']})['total'],3)

    def test_priority_is_shared_by_list_detail_stack_report_and_navigation(self):
        self.replace_events([1]*30);key=self.app.key;db=self.app.database()
        with db:
            ids=[r[0] for r in db.execute('SELECT id FROM events ORDER BY id')]
            db.execute('UPDATE events SET score=20 WHERE id=?',(ids[-1],))
        db.close()
        q={'run':[key],'sort':['priority'],'status':['a_examiner']}
        first=self.app.events(q);self.assertEqual(first['items'][0]['id'],ids[-1])
        self.assertEqual(self.app.events({'run':[key]})['items'][0]['id'],ids[0])
        event=first['items'][0];detail=self.app.detail(key,event['id'])
        marker=next(e for e in self.app.stack(key,'etalement')['events'] if e['id']==event['id'])
        self.assertEqual(marker['priority_score'],event['priority_score'])
        self.assertEqual(detail['event']['priority_score'],event['priority_score'])
        self.app.decide({'run':key,'id':event['id'],'snapshot':detail['event']['snapshot'],'status':'retenue'})
        self.assertIn(f"Priority {event['priority_score']:.1f} / 100",self.app.report(key).decode())
        after=self.app.events(dict(q,after=[str(event['id'])]))
        self.assertEqual(after['next_id'],ids[0]);self.assertEqual(after['items'][0]['id'],ids[0])
        anchor=after['items'][24];d=self.app.detail(key,anchor['id'])
        self.app.decide({'run':key,'id':anchor['id'],'snapshot':d['event']['snapshot'],'status':'ecartee'})
        next_page=self.app.events(dict(q,after=[str(anchor['id'])]))
        self.assertEqual(next_page['items'][24]['id'],next_page['next_id'])
        self.assertEqual(next_page['next_id'],ids[25])
        with self.assertRaises(ValueError):self.app.events({'run':[key],'sort':['score; DROP TABLE events']})

    def test_shape_requires_measured_fusion_and_preserves_analysis(self):
        stack=self.app.stack(self.app.key,'etalement')
        self.assertFalse(stack['shape_available'])
        with self.assertRaisesRegex(ValueError,'post-melting'):self.app.shape_image(self.app.key,stack['frames'][0]['id'])
        for layer in range(1,9):
            pixels=np.full((80,80),100,np.uint8);pixels[20:40,20:40]=np.indices((20,20)).sum(axis=0)%3*60+100
            Image.fromarray(pixels).save(self.source/f'cam1_layer{layer}_fused.jpg')
        self.app.start({'analysis_phase':'both','tile':16,'threshold':12})
        for _ in range(500):
            if not self.app.running:break
            time.sleep(.01)
        self.assertFalse(self.app.running);self.assertIsNone(self.app.error)
        before=self.app.state();stack=self.app.stack(self.app.key,'fusion')
        self.assertTrue(stack['shape_available'])
        data,stats=self.app.shape_image(self.app.key,stack['frames'][0]['id'])
        with Image.open(io.BytesIO(data)) as mask:self.assertEqual(mask.mode,'RGBA')
        self.assertGreater(stats['coverage_percent'],0)
        after=self.app.state();self.assertEqual(before['run'],after['run']);self.assertEqual(before['analysis'],after['analysis'])
        with self.assertRaisesRegex(ValueError,'changed'):self.app.shape_image('old',stack['frames'][0]['id'])

    def test_next_event_after_save_respects_filter_and_page_boundaries(self):
        self.replace_events([1]*52);key=self.app.key
        before=self.app.events({'run':[key]});current=before['items'][24]
        detail=self.app.detail(key,current['id'])
        self.app.decide({'run':key,'id':current['id'],'snapshot':detail['event']['snapshot'],'status':'ecartee'})
        after=self.app.events({'run':[key],'status':['a_examiner'],'after':[str(current['id'])]})
        self.assertEqual(after['next_id'],current['id']+1)
        self.assertEqual(after['offset'],0)
        self.assertEqual(after['items'][24]['id'],after['next_id'])
        all_statuses=self.app.events({'run':[key],'after':[str(current['id'])]})
        self.assertEqual(all_statuses['offset'],25);self.assertEqual(all_statuses['items'][0]['id'],after['next_id'])
        last=self.app.events({'run':[key],'offset':['50']})['items'][-1]
        self.assertIsNone(self.app.events({'run':[key],'after':[str(last['id'])]})['next_id'])

    def test_start_runs_python_and_reuses_same_settings(self):
        before=self.app.key
        self.app.start({'threshold':12,'tile':16,'region':'full'})
        for _ in range(500):
            if not self.app.running:
                break
            time.sleep(.01)
        self.assertFalse(self.app.running)
        state=self.app.state()
        self.assertIsNone(state['error'])
        self.assertNotEqual(before,state['run'])
        self.assertEqual(state['summary']['images_mesurees'],8)
        self.assertTrue(state['summary']['parcours_termine'])

    def test_dataset_extension_starts_a_separate_project(self):
        before=self.app.project_for(self.app.config)
        self.assertEqual(self.app.state()['dataset']['images'],8)
        Image.new('L',(80,80),100).save(self.source/'cam1_layer9_spread.jpg')
        after=Application(self.root,self.source)
        self.assertEqual(after.dataset['images'],9)
        self.assertNotEqual(after.project_for(after.config),before)
        self.assertTrue((self.root/'results_nist_16bit'/'project.sqlite').exists())

    def test_documented_job_has_separate_gray_calibration_and_common_summary(self):
        settings={'threshold':13,'tile':16,'region':'full'}
        self.app.calibrate_job(settings)
        deadline=time.monotonic()+10
        while self.app.running and time.monotonic()<deadline:time.sleep(.01)
        state=self.app.state()
        self.assertIsNone(state['error']);self.assertFalse(state['running'])
        self.assertEqual(state['calibration']['sample_images'],8)
        self.assertIsNone(state['analysis'])
        self.assertEqual(state['summary']['images_mesurees'],0)
        self.assertEqual(list(state['calibration']['channels']),['cam1/etalement'])
        calibrated=state['calibration']
        self.app.start(settings)
        deadline=time.monotonic()+10
        while self.app.running and time.monotonic()<deadline:time.sleep(.01)
        state=self.app.state()
        self.assertIsNone(state['error']);self.assertFalse(state['running'])
        self.assertEqual(state['calibration'],calibrated)
        self.assertEqual(state['analysis']['measured'],8)
        self.assertEqual(state['analysis']['evaluated'],3)

    def test_analysis_phase_is_applied_and_persisted(self):
        for layer in range(1,9):
            Image.new('L',(80,80),100).save(self.source/f'cam1_layer{layer}_fused.jpg')
        self.app.start({'analysis_phase':'fusion','tile':16,'threshold':12})
        for _ in range(500):
            if not self.app.running: break
            time.sleep(.01)
        state=self.app.state()
        self.assertIsNone(state['error'])
        self.assertEqual(state['dataset']['images'],16)
        self.assertEqual(state['summary']['images_mesurees'],8)
        self.assertEqual([s['phase'] for s in state['summary']['series']],['fusion'])
        restored=Application(self.root,self.source)
        self.assertEqual(restored.config.analysis_phases,['fusion'])
        self.assertEqual(restored.key,self.app.key)
        self.assertTrue(restored.state()['summary']['parcours_termine'])

    def test_comparison_rejects_unrelated_and_mismatched_frames(self):
        key=self.app.key
        event=self.app.events({'run':[key]})['items'][0]
        detail=self.app.detail(key,event['id'],'tight')
        self.assertEqual(detail['crop'],[0,0,80,80])
        for frame in detail['frames']:
            self.assertTrue(frame['comparable'])
            with Image.open(io.BytesIO(self.app.image(key,frame['id'],event['id'],'tight'))) as image:
                self.assertEqual(image.size,(80,80))
        db=self.app.database()
        unrelated=db.execute('SELECT id FROM frames WHERE layer=1').fetchone()[0]
        with self.assertRaisesRegex(ValueError,'compared layers'):
            self.app.image(key,unrelated,event['id'])
        geometry=dict(detail['geometry'],width=81)
        with db:
            db.execute('UPDATE frames SET geometry=? WHERE id=?',(json.dumps(geometry),detail['frames'][0]['id']))
        db.close()
        revised=self.app.detail(key,event['id'])
        self.assertFalse(revised['frames'][0]['comparable'])
        with self.assertRaisesRegex(ValueError,'compared layers'):
            self.app.image(key,detail['frames'][0]['id'],event['id'])

    def test_stack_keeps_phase_order_and_actual_heights(self):
        stack=self.app.stack(self.app.key,'etalement','full')
        self.assertEqual([f['layer'] for f in stack['frames']],list(range(1,9)))
        self.assertAlmostEqual(stack['frames'][6]['z_mm'],.42)
        self.assertEqual(stack['crop'],[0,0,80,80])
        with Image.open(io.BytesIO(self.app.stack_image(self.app.key,stack['frames'][0]['id'],'full'))) as image:
            self.assertEqual(image.size,(80,80))
        with self.assertRaisesRegex(ValueError,'included in the analysis'):
            self.app.stack(self.app.key,'fusion')

    def test_stack_includes_red_markers_at_peak_and_current_decisions(self):
        stack=self.app.stack(self.app.key,'etalement','full')
        self.assertGreater(len(stack['events']),0)
        event=stack['events'][0]
        detail=self.app.detail(self.app.key,event['id'])
        self.assertEqual(event['box'],json.loads(detail['event']['box']))
        self.assertEqual(event['layer'],detail['peak_layer'])
        self.assertAlmostEqual(event['z_mm'],detail['z_mm'])
        before=self.app.state()['revision']
        self.app.decide({'run':self.app.key,'id':event['id'],'snapshot':detail['event']['snapshot'],'status':'retenue'})
        updated=self.app.stack(self.app.key,'etalement','full')
        self.assertEqual(next(e for e in updated['events'] if e['id']==event['id'])['status'],'retenue')
        self.assertGreater(self.app.state()['revision'],before)

    def test_local_import_references_files_and_survives_library_switch(self):
        config=json.loads((self.root/'config.nist_sample.json').read_text())
        originals={p.name:p.stat().st_mtime_ns for p in self.source.iterdir()}
        self.app.import_library({'path':str(self.source),'name':'Mon job','config':config})
        for _ in range(500):
            if not self.app.running:break
            time.sleep(.01)
        self.assertIsNone(self.app.error)
        library=self.app.library['id']
        self.assertTrue(library.startswith('local_'))
        self.assertEqual(self.app.source,self.source)
        self.assertEqual(self.app.dataset['images'],8)
        self.app.start({'threshold':12,'tile':16,'analysis_phase':'etalement'})
        for _ in range(500):
            if not self.app.running:break
            time.sleep(.01)
        run=self.app.key
        event=self.app.events({'run':[run]})['items'][0]
        detail=self.app.detail(run,event['id'])
        self.app.decide({'run':run,'id':event['id'],'snapshot':detail['event']['snapshot'],'status':'retenue','comment':'Conserver'})
        self.app.select_library('custom');self.app.select_library(library)
        self.assertEqual(self.app.key,run)
        self.assertEqual(self.app.state()['summary']['indications']['retenue'],1)
        self.assertEqual(originals,{p.name:p.stat().st_mtime_ns for p in self.source.iterdir()})
        restored=Application(self.root,self.source)
        self.assertEqual(restored.library['id'],library)
        self.assertEqual(restored.key,run)

    def test_inventory_subfolders_and_duplicate_identifiers(self):
        nested=self.root/'nested';(nested/'job').mkdir(parents=True)
        Image.new('L',(80,80),100).save(nested/'job'/'cam1_layer1_spread.jpg')
        config=Config(filename_regex=r'job/(?P<camera>cam[0-9]+)_layer(?P<layer>[0-9]+)_(?P<phase>spread|fused)\.jpg')
        info=inventory(nested,config)
        self.assertEqual(info['images'],1)
        self.assertEqual(info['examples'][0]['file'],'job/cam1_layer1_spread.jpg')
        Image.new('L',(80,80),100).save(nested/'job'/'cam1_layer01_spread.jpg')
        with self.assertRaisesRegex(ValueError,'Duplicate'):inventory(nested,config)

    def test_stack_separates_cameras_including_markers(self):
        for layer in range(1,9):
            Image.new('L',(80,80),100).save(self.source/f'cam2_layer{layer}_spread.jpg')
        self.app.start({'threshold':12,'tile':16})
        for _ in range(500):
            if not self.app.running:break
            time.sleep(.01)
        first=self.app.stack(self.app.key,'etalement','full','cam1')
        second=self.app.stack(self.app.key,'etalement','full','cam2')
        self.assertEqual(first['cameras'],['cam1','cam2'])
        self.assertTrue(first['events']);self.assertEqual(second['events'],[])
        self.assertFalse({f['id'] for f in first['frames']} & {f['id'] for f in second['frames']})


class ImagingTests(unittest.TestCase):
    def test_context_preserves_box_and_clips_to_edges(self):
        for box in ([1,2,17,18],[1980,1980,2000,2000],[500,600,1300,700],[0,0,2000,2000]):
            previous=0
            for mode in ('tight','standard','wide'):
                crop=context_box(box,2000,2000,mode)
                self.assertTrue(0<=crop[0]<=box[0]<box[2]<=crop[2]<=2000)
                self.assertTrue(0<=crop[1]<=box[1]<box[3]<=crop[3]<=2000)
                self.assertGreaterEqual(crop[2]-crop[0],previous)
                previous=crop[2]-crop[0]
        self.assertEqual(context_box([500,600,516,616],2000,2000),[380,480,636,736])
        with self.assertRaises(ValueError): context_box([0,0,20,20],10,10)
        with self.assertRaises(ValueError): context_box([0,0,2,2],10,10,'unknown')

    def test_crops_use_original_pixels_and_fixed_brightness(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'source.png'
            # Des pixels lumineux hors cadrage ne doivent pas modifier le contraste du gros plan.
            pixels=np.zeros((600,600),np.uint16)
            pixels[100:400,200:500]=32768
            pixels[0:50]=65535
            Image.fromarray(pixels).save(path)
            content=preview(str(path),65535,(210,110,466,366))
            with Image.open(io.BytesIO(content)) as image:
                self.assertEqual(image.size,(256,256))
                self.assertTrue(126<=np.asarray(image).mean()<=129)
            html=picture({'path':str(path)},Config(intensity_white_level=65535),
                         box=[230,130,250,150],crop=[210,110,466,366],expected_size=(600,600))
            import base64,re
            encoded=re.search('base64,([^\"]+)',html)[1]
            with Image.open(io.BytesIO(base64.b64decode(encoded))) as image:
                self.assertEqual(image.size,(256,256))
                red=np.asarray(image)[20:23,20:40].mean(axis=(0,1))
                self.assertGreater(red[0],red[1]+50)
            rejected=picture({'path':str(path)},Config(intensity_white_level=65535),
                             crop=[0,0,128,128],expected_size=(500,500))
            self.assertIn('Different image dimensions',rejected)


if __name__=='__main__':
    unittest.main()
