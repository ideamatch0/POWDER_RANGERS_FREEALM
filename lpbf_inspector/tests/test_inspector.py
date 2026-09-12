import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image

from inspector import Config, Detector, analyze, connect, event_fingerprint, extract, metadata, save_decisions
from review import create_review


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.source = self.root/'images'
        self.source.mkdir()
        self.project = self.root/'result'
        self.config = Config(tile_px=8, history=5, warmup=3)

    def tearDown(self):
        self.tmp.cleanup()

    def make(self, layer, camera='cam1', phase='spread', brightness=100, defect=False):
        pixels = np.full((64, 80), brightness, np.uint8)
        if defect:
            pixels[16:32, 24:40] = 200
        file = self.source/f'{camera}_layer{layer:04d}_{phase}.jpg'
        Image.fromarray(pixels).save(file, quality=100, subsampling=0)
        return file

    def rows(self, project=None):
        db = connect(project or self.project)
        try:
            return [dict(r) for r in db.execute('SELECT * FROM events ORDER BY id')]
        finally:
            db.close()

    def test_steps_cameras_and_numeric_layers_are_independent(self):
        for layer in [10, 1, 4, 5, 3, 2, 6, 7, 8, 9]:
            for camera in ['cam1', 'cam2']:
                for phase, light in [('spread', 80), ('fused', 170)]:
                    self.make(layer, camera, phase, light, camera=='cam1' and phase=='spread' and layer==7)
        result = analyze(self.source, self.project, self.config)
        rows = self.rows()
        self.assertTrue(result['parcours_termine'])
        self.assertEqual(result['images_mesurees'], 40)
        self.assertTrue(rows)
        self.assertTrue(all(r['camera']=='cam1' and r['phase']=='etalement' for r in rows))
        self.assertEqual(rows[0]['start_layer'], 7)

    def test_global_change_stays_visible_without_local_flood(self):
        for layer in range(1, 8):
            self.make(layer, brightness=140 if layer==5 else 100)
        analyze(self.source, self.project, self.config)
        kinds = [r['kind'] for r in self.rows()]
        self.assertIn('luminosite_globale', kinds)
        self.assertNotIn('changement_local', kinds)

    def test_pause_resume_reuses_cache_and_matches_uninterrupted_run(self):
        for layer in range(1, 11):
            self.make(layer, defect=layer in [5,6])
        processed = [0]
        def progress(**p):
            if p['stage']=='analyse':processed[0]=p['done']
        result = analyze(self.source, self.project, self.config, progress=progress, stop=lambda:processed[0]>=5)
        self.assertFalse(result['parcours_termine'])
        with patch('inspector.extract', wraps=extract) as extractor:
            analyze(self.source, self.project, self.config)
            self.assertEqual(extractor.call_count, 5)
        other = self.root/'continuous'
        analyze(self.source, other, self.config)
        self.assertEqual(self.rows(), self.rows(other))
        with patch('inspector.extract', side_effect=AssertionError('Cache non utilisé')):
            analyze(self.source, self.project, self.config)

    def test_duplicate_camera_phase_layer_blocks_ambiguous_import(self):
        first = self.make(1)
        (self.source/'cam1_layer1_spread.jpg').write_bytes(first.read_bytes())
        with self.assertRaisesRegex(ValueError, '[Aa]mbiguous'):
            analyze(self.source, self.project, self.config)

    def test_gap_and_corrupt_image_reset_history(self):
        for layer in [1,2,3,4,6,7,8,9,10]:
            self.make(layer, brightness=140 if layer>=6 else 100)
        (self.source/'cam1_layer0009_spread.jpg').write_bytes(b'not a JPEG')
        result = analyze(self.source, self.project, self.config)
        self.assertEqual(result['images_en_erreur'], 1)
        self.assertFalse(self.rows())
        self.assertEqual(result['observations_import_couverture']['discontinuite'], 1)

    def test_config_and_changed_sources_cannot_silently_reuse_cache(self):
        self.make(1)
        analyze(self.source, self.project, self.config)
        with self.assertRaisesRegex(ValueError, 'fixed'):
            analyze(self.source, self.project, Config(tile_px=16))
        self.make(1, brightness=180)
        with self.assertRaisesRegex(ValueError, 'changed'):
            analyze(self.source, self.project, self.config)

    def test_height_is_based_on_actual_layer_number(self):
        self.assertAlmostEqual(self.config.z(100), 6.0)
        self.assertAlmostEqual(Config(first_layer=100, first_layer_z_mm=5.7).z(103), 5.88)

    def test_local_slow_drift_uses_fixed_initial_baseline(self):
        d = Detector(self.config)
        geometry = {'width':64, 'height':64, 'roi':[0,0,64,64], 'tile':8}
        found = []
        for layer in range(1,35):
            values = np.zeros((4,8,8), np.float32)
            values[0,2:4,2:4] = max(0,layer-5)*1.5
            events, _, _ = d.process(layer, values, 100., geometry)
            found += [e[0] for e in events]
        self.assertIn('derive_locale', found)

    def test_crop_coordinates_and_partial_edge_tiles(self):
        path = self.make(1, defect=True)
        config = Config(tile_px=8, roi_by_camera={'cam1':[7,9,75,60]})
        features, light, geometry = extract(path, config, 'cam1')
        self.assertEqual(features.shape, (4,7,9))
        self.assertEqual(geometry['roi'], [7,9,75,60])

    def test_16_bit_scale_is_fixed_and_preserves_brightness(self):
        raw = np.full((32,32),25700,np.uint16)
        raw[8:16,8:16] = 51400
        file = self.source/'test.png'
        Image.fromarray(raw).save(file)
        with self.assertRaisesRegex(ValueError,'16-bit'):
            extract(file,self.config,'cam1')
        features, light, _ = extract(file,Config(tile_px=8,intensity_white_level=65535),'cam1')
        # Moyenne de tous les pixels : 1/16 de la photo est à 200, le reste à 100.
        self.assertAlmostEqual(light,106.25,places=4)
        self.assertAlmostEqual(float(features[0,1,1])+light,200.,places=4)

    def test_review_persists_decisions_and_escapes_comments(self):
        for layer in range(1,8):
            self.make(layer, defect=layer==5)
        analyze(self.source, self.project, self.config)
        db = connect(self.project)
        try:
            definition = metadata(db,'definition')
            event = db.execute('SELECT * FROM events LIMIT 1').fetchone()
            payload = {'project_key':hashlib.sha256(json.dumps(definition,sort_keys=True).encode()).hexdigest(),
                       'decisions':[{'id':event['id'],'snapshot':event_fingerprint(event),
                                     'status':'retenue','comment':'<script>alert(1)</script>'}]}
        finally:
            db.close()
        decision_file = self.root/'decisions.json'
        decision_file.write_text(json.dumps(payload), encoding='utf-8')
        save_decisions(self.project, decision_file)
        result = create_review(self.project, retained_only=True)
        page = result.read_text(encoding='utf-8')
        self.assertIn('&lt;script&gt;alert(1)&lt;/script&gt;', page)
        self.assertIn('data:image/jpeg;base64,', page)
        self.assertIn('couches 5', page)
        payload['decisions'][0]['snapshot'] = 'obsolete'
        decision_file.write_text(json.dumps(payload),encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'changed'):
            save_decisions(self.project, decision_file)


if __name__ == '__main__':
    unittest.main()
