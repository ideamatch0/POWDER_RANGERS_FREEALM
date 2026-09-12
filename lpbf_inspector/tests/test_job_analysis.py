import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
from PIL import Image

from inspector import Config
from job_analysis import analyze_job, calibrate, check_records


class SingleJobTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.config=Config(tile_px=8,history=5,warmup=3)
        self.records=[]

    def tearDown(self):self.temp.cleanup()

    def frame(self,counter,level=100,patch=False):
        pixels=np.full((64,80),level,np.uint8)
        if patch:pixels[24:40,32:48]=220
        path=self.root/f'{counter}.png';Image.fromarray(pixels).save(path)
        self.records.append({'id':counter,'name':path.name,'job':'one','counter':counter})

    def analyze(self,step=1,folder='result'):
        cal=calibrate(self.root,self.records,self.config,step,'fingerprint')
        result=analyze_job(self.root,self.records,self.config,step,'fingerprint',cal,self.root/folder)
        return cal,result

    def test_separate_alternating_sequences_have_own_gray_and_no_spurious_jumps(self):
        for counter in range(1,41):self.frame(counter,60 if counter%2 else 160)
        cal,result=self.analyze(step=2)
        self.assertEqual(cal['channels']['0']['mean_gray'],160)
        self.assertEqual(cal['channels']['1']['mean_gray'],60)
        self.assertEqual(result['report']['jobs']['one']['detections'],0)
        self.assertEqual(result['report']['jobs']['one']['warmup_images'],6)

    def test_local_change_and_global_jump_are_detected_and_cache_is_identical(self):
        for counter in range(1,30):self.frame(counter,170 if counter==29 else 100,patch=counter==26)
        cal,result=self.analyze()
        self.assertEqual(cal['mean_gray'],100)
        local=result['images']['26']['predictions']
        self.assertTrue(any(p['kind']=='changement_local' and p['box'][0]<=32 and p['box'][2]>=48 for p in local))
        self.assertTrue(any(p['kind']=='luminosite_globale' for p in result['images']['29']['predictions']))
        _,again=self.analyze()
        self.assertEqual(result['images'],again['images'])
        self.assertEqual(again['report']['jobs']['one']['cached'],29)

    def test_corrupt_photo_and_counter_gap_restart_only_that_history(self):
        for counter in range(1,37):
            if counter!=25:self.frame(counter)
        (self.root/'30.png').write_bytes(b'broken image')
        _,result=self.analyze()
        m=result['report']['jobs']['one']
        self.assertEqual(len(m['errors']),1)
        self.assertEqual(m['errors'][0]['id'],30)
        self.assertEqual(m['gaps'],1)
        self.assertFalse(result['images']['26']['analyzed'])
        self.assertFalse(result['images']['31']['analyzed'])
        self.assertTrue(result['images']['34']['analyzed'])
        self.assertIsNotNone(result['images']['30']['error'])

    def test_another_job_calibration_or_mixed_jobs_are_rejected(self):
        for counter in range(1,24):self.frame(counter)
        cal,_=self.analyze()
        cal['job']='another'
        with self.assertRaisesRegex(ValueError,'does not match'):
            analyze_job(self.root,self.records,self.config,1,'fingerprint',cal,self.root/'other')
        with self.assertRaisesRegex(ValueError,'exactly one job'):
            check_records(self.records+[{'job':'another','counter':50}])


if __name__=='__main__':unittest.main()
