from dataclasses import asdict
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import time
import unittest

import numpy as np
from PIL import Image

from inspector import Config
from aalto_detector import VERSION, candidate_regions, select_regions, detect_image, percentile90
from aalto_calibration import CONFIGS, choose_config, match_boxes, run_calibration
from local_app import Application
import job_analysis


class CalibrationTests(unittest.TestCase):
    def test_optimized_quantile_preserves_numeric_scores(self):
        generator=np.random.default_rng(5)
        for count in (1,2,6,17,244,1000):
            values=generator.normal(5,3,count).astype(np.float32)
            self.assertAlmostEqual(percentile90(values),float(np.percentile(values,90)),places=4)

    def test_one_prediction_cannot_claim_several_annotations(self):
        predictions=[{'box':[0,0,20,20],'score':10}]
        labels=[{'box':[0,0,20,20]},{'box':[0,0,20,20]}]
        self.assertEqual(match_boxes(predictions,labels), (1,0,1))
        self.assertEqual(match_boxes(predictions*2,labels[:1]), (1,1,0))
        self.assertEqual(match_boxes([],labels), (0,0,2))

    def test_excluded_job_cannot_influence_threshold_selection(self):
        counts=np.ones((3,len(CONFIGS),3),dtype=np.int64)
        counts[:2,4]=[100,0,0]
        before=choose_config(counts,[0,1])
        counts[2]=[100000,0,0]
        counts[2,4]=[0,100000,100000]
        self.assertEqual(choose_config(counts,[0,1]),before)
        self.assertEqual(before[0],4)

    def test_inference_needs_only_pixels_and_thresholds(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'unknown.jpg'
            pixels=np.full((1024,1280),140,np.uint8)
            pixels[500:510,350:850]=60
            Image.fromarray(pixels).save(path,quality=100)
            profile={'version':VERSION,'config':{'threshold':7,'min_area':6,'mode':'dark_lines'}}
            first=detect_image(path,profile)
            self.assertTrue(first)
            # Des labels contradictoires placés à côté ne sont jamais lus.
            path.with_suffix('.xml').write_text('<annotation><object>FAUX CADRE</object></annotation>')
            self.assertEqual(first,detect_image(path,profile))
            self.assertTrue(any(p['box'][0]<400 and p['box'][2]>800 for p in first))


class AaltoLibrariesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        cls.root=Path(cls.temp.name)
        cls.source=cls.root/'datasets'/'aalto_pb';cls.source.mkdir(parents=True)
        (cls.root/'config.nist_sample.json').write_text(json.dumps(asdict(Config())))
        rows=[];cls.keys=[]
        for index,job in enumerate(['SI383820211201123521','SI383820240226095904','SI383820240318120348'],1):
            cls.keys.append('aalto_'+job)
            for offset in range(27):
                path=cls.source/f'{job}_{offset+9:05d}.jpg'
                pixels=np.full((128,128),80+index*20,np.uint8)
                if offset==25:pixels[32:64,32:64]=30
                Image.fromarray(pixels).save(path,quality=100)
                rows.append({'id':index*100+offset,'name':path.name,'job':job,'counter':offset+9,'timestamp':job[6:14]+'T120000',
                             'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'width':128,'height':128,
                             'annotations':[{'box':[100,100,110,110],'label':'secret-label'}]})
        provenance={'complete':True,'records':rows,'source_url':'https://zenodo.org/records/14996806',
                    'license':'CC BY 4.0','archive_md5':'test'}
        (cls.source/'provenance.json').write_text(json.dumps(provenance),encoding='utf-8')
        app=Application(cls.root)
        for key in cls.keys:
            app.select_library(key)
            cal=job_analysis.calibrate(app.source,app.gallery,app.config,1,app.dataset['fingerprint'])
            job_analysis.write_json(app.job_folder()/('gray_'+cal['signature']+'.json'),cal)
            job_analysis.analyze_job(app.source,app.gallery,app.config,1,app.dataset['fingerprint'],cal,app.job_folder())

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def setUp(self):self.app=Application(self.root)

    def test_three_libraries_have_disjoint_images_and_runs(self):
        self.assertEqual(len(self.app.catalog.list()),3)
        runs=set()
        for index,key in enumerate(self.keys,1):
            state=self.app.select_library(key);runs.add(state['run'])
            self.assertEqual(state['dataset']['images'],27)
            listing=self.app.gallery_items(state['run'])
            self.assertEqual([r['id'] for r in listing['items']],list(range(index*100,index*100+25)))
            self.assertEqual(state['calibration']['job'],self.app.library['job'])
            self.assertEqual(state['calibration']['mean_gray'],80+index*20)
            self.assertNotIn('calibration_jobs',state['analysis'])
            with self.assertRaisesRegex(ValueError,'this job'):
                self.app.gallery_detail(state['run'],(index%3+1)*100)
            with self.assertRaisesRegex(ValueError,'another library'):
                self.app.gallery_items(state['run'],job='autre')
        self.assertEqual(len(runs),3)

    def test_browser_receives_predictions_never_researcher_boxes(self):
        self.app.select_library(self.keys[0])
        detail=self.app.gallery_detail(self.app.key,125)
        serialized=json.dumps(detail)
        self.assertNotIn('annotations',serialized)
        self.assertNotIn('secret-label',serialized)
        self.assertTrue(detail['predictions'])
        self.assertNotIn('annotations',json.dumps(self.app.gallery_items(self.app.key)))
        with Image.open(io.BytesIO(self.app.gallery_image(self.app.key,125,0))) as image:
            crop=detail['contexts'][0]
            self.assertEqual(image.size,(crop[2]-crop[0],crop[3]-crop[1]))

    def test_decisions_reports_and_stale_library_are_isolated(self):
        self.app.select_library(self.keys[0]);run=self.app.key
        detail=self.app.gallery_detail(run,125);p=detail['predictions'][0]
        data={'run':run,'id':125,'prediction':p['key'],'status':'retenue','comment':'Mon <avis>'}
        self.app.gallery_decide(data)
        report=self.app.gallery_report(run).decode()
        self.assertIn('Mon &lt;avis&gt;',report)
        self.assertNotIn('secret-label',report)
        self.app.select_library(self.keys[1])
        with self.assertRaisesRegex(ValueError,'changed'):self.app.gallery_decide(data)
        with self.assertRaisesRegex(ValueError,'Keep between'):self.app.gallery_report(self.app.key)
        self.app.select_library(self.keys[0])
        self.assertEqual(self.app.gallery_detail(self.app.key,125)['predictions'][0]['status'],'retenue')

    def test_interrupted_run_keeps_previous_results(self):
        self.app.select_library(self.keys[0])
        path=self.app.job_folder()/('analysis_'+self.app.state()['analysis']['signature']+'.json')
        before=path.read_bytes()
        with self.assertRaises(InterruptedError):
            job_analysis.analyze_job(self.source,self.app.gallery,self.app.config,1,self.app.dataset['fingerprint'],self.app.gray_calibration,self.app.job_folder(),stop=lambda:True)
        self.assertEqual(before,path.read_bytes())

    def test_calibration_and_analysis_are_distinct_and_job_local(self):
        self.app.select_library(self.keys[0])
        other=self.app.root/'job_runs'/self.keys[1]
        untouched={p.name:p.read_bytes() for p in other.glob('*.json')}
        settings={'threshold':13,'tile':16,'acquisition_step':1,'region':'full'}
        def wait():
            deadline=time.monotonic()+10
            while self.app.running and time.monotonic()<deadline:time.sleep(.02)
            self.assertFalse(self.app.running);self.assertIsNone(self.app.error)
            return self.app.state()
        self.app.calibrate_job(settings);state=wait()
        self.assertEqual(state['calibration']['sample_images'],20)
        self.assertIsNone(state['analysis'])
        self.app.start(settings);state=wait()
        self.assertEqual(state['analysis']['images'],27)
        self.assertEqual(state['analysis']['evaluated'],22)
        self.assertGreater(state['analysis']['detections'],0)
        self.assertEqual(untouched,{p.name:p.read_bytes() for p in other.glob('*.json')})
        # Revenir aux réglages du jeu d’essai partagé.
        self.app.config=self.app.make_config({});self.app.save_preferences()

    def test_labels_and_other_job_pixels_do_not_affect_results_or_cache(self):
        self.app.select_library(self.keys[0]);before=self.app.state()
        provenance_path=self.source/'provenance.json';original=provenance_path.read_bytes()
        other=self.source/(self.keys[1][6:]+'_00009.jpg');other_original=other.read_bytes();other_stat=other.stat()
        try:
            data=json.loads(original)
            for r in data['records']:r['annotations']=[{'label':'contradiction','box':[0,0,128,128]}]
            provenance_path.write_text(json.dumps(data),encoding='utf-8')
            Image.fromarray(np.zeros((128,128),np.uint8)).save(other)
            self.app.select_library(self.keys[0]);after=self.app.state()
            self.assertEqual(before['run'],after['run'])
            self.assertEqual(before['calibration'],after['calibration'])
            self.assertEqual(before['analysis'],after['analysis'])
            self.assertTrue(all('annotations' not in r for r in self.app.gallery))
        finally:
            provenance_path.write_bytes(original);other.write_bytes(other_original)
            os.utime(other,ns=(other_stat.st_atime_ns,other_stat.st_mtime_ns))

    def test_neighbor_crops_use_same_location_and_reject_other_job(self):
        self.app.select_library(self.keys[0]);run=self.app.key
        detail=self.app.gallery_detail(run,125)
        self.assertEqual([n['id'] for n in detail['neighbors']],[124,126])
        with Image.open(io.BytesIO(self.app.gallery_image(run,124,0,125))) as image:
            crop=detail['contexts'][0];self.assertEqual(image.size,(crop[2]-crop[0],crop[3]-crop[1]))
        with self.assertRaisesRegex(ValueError,'adjacent'):self.app.gallery_image(run,100,0,125)
        with self.assertRaisesRegex(ValueError,'this job'):self.app.gallery_image(run,200,0,125)

    def test_common_review_stack_and_decisions_use_detected_boxes(self):
        self.app.select_library(self.keys[0]);run=self.app.key
        listing=self.app.events({'run':[run]})
        event=next(e for e in listing['items'] if e['peak_frame']==125)
        detail=self.app.detail(run,event['id'])
        self.assertEqual(detail['axis'],'acquisition');self.assertIsNone(detail['z_mm'])
        self.assertEqual([f['id'] for f in detail['frames']],[124,125,126])
        for frame in detail['frames']:
            with Image.open(io.BytesIO(self.app.image(run,frame['id'],event['id']))) as photo:
                crop=detail['crop'];self.assertEqual(photo.size,(crop[2]-crop[0],crop[3]-crop[1]))
        stack=self.app.stack(run,'acquisition')
        self.assertEqual(len(stack['frames']),27)
        mark=next(e for e in stack['events'] if e['id']==event['id'])
        self.assertEqual(mark['box'],json.loads(event['box']))
        self.assertEqual(mark['priority_score'],event['priority_score'])
        self.assertEqual(detail['event']['priority_score'],event['priority_score'])
        with self.assertRaisesRegex(ValueError,'post-melting'):self.app.shape_image(run,125)
        self.assertEqual(mark['position'],34);self.assertIsNone(mark['z_mm'])
        with Image.open(io.BytesIO(self.app.stack_image(run,125))) as photo:self.assertLessEqual(max(photo.size),384)
        self.app.decide({'run':run,'id':event['id'],'snapshot':detail['event']['snapshot'],'status':'retenue','comment':'Build image review report'})
        self.assertEqual(next(e for e in self.app.stack(run,'acquisition')['events'] if e['id']==event['id'])['status'],'retenue')
        self.assertIn('Build image review report',self.app.report(run).decode())
        self.assertIn(f"Priority {event['priority_score']:.1f} / 100",self.app.report(run).decode())
        from reporting import collect_report
        scene=collect_report(self.app,run)['scenes'][0]
        self.assertFalse(scene['cyan']);self.assertEqual(scene['axis'],'acquisition')
        self.assertTrue(all(f['z_mm'] is None for f in scene['frames']))
        self.assertEqual([m['id'] for m in scene['events']],[event['id']])
        self.assertNotIn('secret-label',json.dumps([listing,detail,stack]))
        self.app.select_library(self.keys[1])
        with self.assertRaisesRegex(ValueError,'changed'):self.app.detail(run,event['id'])

    def test_acquisition_persistence_uses_raw_predictions_and_preserves_decisions(self):
        self.app.select_library(self.keys[0]);self.app.save_preferences=lambda:None
        self.app.aalto_result['report']['signature']+='-persistence-test'
        for row in self.app.aalto_result['images'].values():row['predictions']=[]
        for image in [123,124,125]:self.app.aalto_result['images'][str(image)]['predictions']=[{'kind':'changement_local','box':[32,32,64,64],'score':2}]
        self.app.aalto_result['images']['126']['predictions']=[{'kind':'changement_local','box':[80,80,96,96],'score':2}]
        run=self.app.key;self.app.set_review_settings({'run':run,'min_consecutive':3})
        listing=self.app.events({'run':[run]})
        self.assertEqual(listing['total'],3);self.assertEqual(listing['before_persistence'],4)
        self.assertTrue(all(e['consecutive_count']==3 for e in listing['items']))
        self.assertEqual(len(self.app.stack(run,'acquisition')['events']),3)
        current=listing['items'][0];detail=self.app.detail(run,current['id'])
        self.app.decide({'run':run,'id':current['id'],'snapshot':detail['event']['snapshot'],'status':'retenue','comment':'persistance confirmée'})
        successor=self.app.events({'run':[run],'status':['a_examiner'],'after':[current['id']]})
        self.assertEqual(successor['next_id'],listing['items'][1]['id'])
        self.assertIn('Minimum persistence: 3',self.app.report(run).decode())
        self.app.set_review_settings({'run':run,'min_consecutive':4})
        self.assertEqual(self.app.events({'run':[run]})['total'],0)
        self.assertFalse(self.app.stack(run,'acquisition')['events'])
        with self.assertRaisesRegex(ValueError,'persistence'):self.app.report(run)
        self.app.set_review_settings({'run':run,'min_consecutive':1})
        self.assertEqual(self.app.detail(run,current['id'])['event']['status'],'retenue')

    def test_priority_order_uses_own_variation_and_consecutive_acquisitions(self):
        self.app.select_library(self.keys[0]);self.app.save_preferences=lambda:None
        self.app.aalto_result['report']['signature']+='-priority-test'
        for row in self.app.aalto_result['images'].values():row['predictions']=[]
        for image in [123,124,125]:self.app.aalto_result['images'][str(image)]['predictions']=[{'kind':'changement_local','box':[32,32,64,64],'score':2}]
        self.app.aalto_result['images']['126']['predictions']=[{'kind':'changement_local','box':[80,80,96,96],'score':2}]
        q={'run':[self.app.key],'sort':['priority'],'status':['a_examiner']}
        listing=self.app.events(q);self.assertEqual(listing['items'][0]['legacy_priority_score'],50)
        self.assertGreater(listing['items'][0]['priority_score'],40)
        self.assertGreater(listing['items'][0]['priority_score'],listing['items'][-1]['priority_score'])
        event=listing['items'][0]
        self.app.decide({'run':self.app.key,'id':event['id'],'snapshot':event['snapshot'],'status':'ecartee'})
        after=self.app.events(dict(q,after=[event['id']]))
        self.assertEqual(after['next_id'],listing['items'][1]['id'])
        self.assertEqual(after['items'][0]['id'],after['next_id'])


if __name__=='__main__':unittest.main()
