from dataclasses import asdict
import json
from pathlib import Path
import tempfile
import time
import unittest
import numpy as np
from PIL import Image
from buildplate import validate_outlines,plate_mask
from inspector import Config,extract,analyze,connect,metadata
from local_app import Application

class BuildPlateTests(unittest.TestCase):
    def test_rejects_crossed_degenerate_and_nonfinite_contours(self):
        for points in ([[0,0],[1,1],[1,0],[0,1]],[[0,0],[.5,.5],[1,1]],[[0,0],[1,0],[1,float('nan')]],[[0,0],[1,0],[2,1]]):
            with self.assertRaises(ValueError):validate_outlines({'cam1':points})
        self.assertIn('cam1',validate_outlines({'CAM1':[[0,0],[1,0],[1,1],[0,1]]}))

    def test_mask_excludes_pixels_within_bounding_box_but_outside_polygon(self):
        points=[[.1,.1],[.9,.1],[.1,.9]]
        mask=plate_mask(64,64,tuple(map(tuple,points)))
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'test.png'
            first=np.where(mask,100,20).astype(np.uint8)
            second=np.where(mask,100,250).astype(np.uint8)
            config=Config(tile_px=8,plate_by_camera={'cam1':points}).validate()
            Image.fromarray(first).save(path);features,light,geometry=extract(path,config,'cam1')
            Image.fromarray(second).save(path);changed,changed_light,_=extract(path,config,'cam1')
            np.testing.assert_array_equal(features,changed)
            self.assertEqual(light,100);self.assertEqual(changed_light,100)
            self.assertTrue(np.isfinite(features).all());self.assertIn('plate_polygon',geometry)
            with self.assertRaisesRegex(ValueError,'camera cam2'):extract(path,config,'cam2')

    def test_calibration_and_detection_ignore_side_changes_and_keep_plate_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'images';source.mkdir()
            points=[[.1,.1],[.9,.1],[.1,.9]]
            mask=plate_mask(64,64,tuple(map(tuple,points)))
            for layer in range(1,11):
                pixels=np.where(mask,100,40 if layer<7 else 250).astype(np.uint8)
                if layer==9:pixels[16:24,16:24]=200
                Image.fromarray(pixels).save(source/f'cam1_layer{layer}_spread.png')
            config=Config(filename_regex=r'(?P<camera>cam\d+)_layer(?P<layer>\d+)_(?P<phase>spread|fused)\.png',
                          tile_px=8,history=5,warmup=3,plate_by_camera={'cam1':points})
            result=analyze(source,root/'results',config)
            self.assertEqual(result['images_mesurees'],10);self.assertEqual(result['images_en_erreur'],0)
            db=connect(root/'results')
            try:
                calibration=metadata(db,'gray_calibration')
                # Includes the real inside change, but none of the outside brightness jump.
                self.assertLess(calibration['mean_gray'],102)
                rows=list(db.execute('SELECT * FROM events'))
                self.assertTrue(rows);self.assertTrue(all(row['start_layer']>=9 for row in rows))
            finally:db.close()

    def test_editor_saves_per_camera_and_retains_old_analysis(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'images';source.mkdir()
            for layer in range(1,8):Image.new('L',(64,64),100).save(source/f'cam1_layer{layer}_spread.jpg')
            app=Application(root,source);app.start({'tile':16,'threshold':12})
            while app.running:time.sleep(.01)
            old_run=app.key;old_project=app.project
            reference=app.plate_reference()
            self.assertEqual(reference['camera'],'cam1');self.assertEqual(reference['width'],64)
            self.assertEqual(reference['run'],old_run)
            self.assertEqual(len(reference['profile']),16)
            points=[[.2,.2],[.8,.2],[.8,.8],[.2,.8]]
            saved=app.set_buildplate({'run':old_run,'outlines':{'cam1':points}})
            self.assertNotEqual(saved['run'],old_run);self.assertIsNone(saved['analysis'])
            self.assertTrue((old_project/'project.sqlite').is_file())
            self.assertEqual(app.config.plate_by_camera,{'cam1':points})
            restored=Application(root,source)
            self.assertEqual(restored.config.plate_by_camera,{'cam1':points})
            with self.assertRaisesRegex(ValueError,'changed'):app.set_buildplate({'run':old_run,'outlines':{}})
            cleared=app.set_buildplate({'run':app.key,'outlines':{}})
            self.assertEqual(cleared['run'],old_run);self.assertEqual(cleared['summary']['images_mesurees'],7)

    def test_contours_survive_library_switch_with_different_cameras_and_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);entries=[]
            app=Application(root)
            for camera in ('cam1','cam2'):
                source=root/camera;source.mkdir()
                Image.new('L',(64,64),100).save(source/f'{camera}_layer1_spread.jpg')
                entry=app.catalog.add({'path':str(source),'config':asdict(Config()),'name':camera},lambda **kw:None,lambda:False)
                entries.append(entry['id'])
                app.select_library(entry['id'])
                app.set_buildplate({'run':app.key,'outlines':{camera:[[.1,.1],[.9,.1],[.9,.9],[.1,.9]]}})
            for key,camera in zip(entries,('cam1','cam2')):
                state=app.select_library(key)
                self.assertEqual(list(state['config']['plate_by_camera']),[camera])
                app.config=app.make_config({'region':'full'})
                app.save_preferences()
                self.assertIn(camera,app.plate_outlines())
                app.config=app.make_config({'region':'plate'})
                app.save_preferences()
            restored=Application(root)
            self.assertEqual(restored.plate_outlines(),app.plate_outlines())
            self.assertEqual(restored.plate_reference()['profile'],app.plate_reference()['profile'])

    def test_partial_camera_contours_stay_saved_without_enabling_incomplete_mask(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'images';source.mkdir()
            for camera in ('cam1','cam2'):Image.new('L',(64,64),100).save(source/f'{camera}_layer1_spread.jpg')
            app=Application(root,source)
            outlines={'cam1':[[.1,.1],[.9,.1],[.9,.9],[.1,.9]]}
            saved=app.set_buildplate({'run':app.key,'outlines':outlines})
            self.assertEqual(saved['buildplate']['outlines'],outlines)
            self.assertEqual(saved['config']['plate_by_camera'],{})
            restored=Application(root,source)
            self.assertEqual(restored.plate_outlines(),outlines)
            self.assertEqual(restored.config.plate_by_camera,{})

    def test_unmasked_project_signature_stays_compatible(self):
        import hashlib
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'images';source.mkdir()
            Image.new('L',(64,64),100).save(source/'cam1_layer1_spread.jpg')
            app=Application(root,source);values=asdict(app.config);values.pop('plate_by_camera')
            expected=hashlib.sha256(json.dumps({'dataset':app.dataset['fingerprint'],'config':values,'engine':'0.2.1'},sort_keys=True).encode()).hexdigest()[:16]
            self.assertEqual(app.key,'essai_'+expected)

if __name__=='__main__':unittest.main()
