import json
import unittest
import numpy as np
from inspector import Config,Detector
from detection_evidence import explain_trace
from priority import with_priority


class DetectionEvidenceTests(unittest.TestCase):
    def test_texture_trigger_can_differ_while_mean_is_unchanged(self):
        config=Config(tile_px=16,min_change_gray=12,min_texture_change=8)
        detector=Detector(config)
        geometry={'roi':[0,0,32,32],'tile':16}
        for layer in range(1,6):detector.process(layer,np.zeros((4,2,2),np.float32),100,geometry)
        current=np.zeros((4,2,2),np.float32);current[1,0,1]=24
        events,ready,_=detector.process(6,current,100,geometry)
        self.assertTrue(ready);self.assertEqual(events,[('changement_local',[16,0,32,16],3.)])
        evidence=explain_trace(detector,{'kind':events[0][0],'box':events[0][1],'score':3},geometry)
        self.assertEqual(evidence['delta'],24);self.assertEqual(evidence['threshold'],8)
        self.assertTrue(evidence['ratio_verified']);self.assertEqual(evidence['peak_tile'],[16,0,32,16])
        self.assertIn('texture',evidence['channel'])
        event=with_priority({'score':3,'start_layer':1,'end_layer':30,'box':json.dumps([0,0,128,128]),'phase':'fusion','part_overlap':1})
        self.assertAlmostEqual(sum(v['points'] for v in event['score_breakdown'].values()),event['priority_score'],delta=.05)

    def test_robust_noise_threshold_not_only_slider_floor(self):
        detector=Detector(Config(tile_px=16,sigma=6,min_change_gray=12))
        geometry={'roi':[0,0,16,16],'tile':16}
        for i,value in enumerate((0,5,10,15,20),1):
            values=np.zeros((4,1,1),np.float32);values[0]=value
            detector.process(i,values,100,geometry)
        values=np.zeros((4,1,1),np.float32);values[0]=100
        events,_,_=detector.process(6,values,100,geometry)
        local=next(e for e in events if e[0]=='changement_local')
        evidence=explain_trace(detector,{'kind':local[0],'box':local[1],'score':local[2]},geometry)
        self.assertAlmostEqual(evidence['reference'],10)
        self.assertAlmostEqual(evidence['threshold'],6*1.4826*5,places=4)
        self.assertTrue(evidence['ratio_verified'])

    def test_replay_does_not_change_detection_outputs_and_global_drift(self):
        config=Config();normal=Detector(config);replay=Detector(config)
        geometry={'roi':[0,0,32,32],'tile':16}
        for layer in range(1,26):
            values=np.zeros((4,2,2),np.float32);values[0,0,0]=max(0,layer-5)*2
            light=100+max(0,layer-5)*3
            normal.process(layer,values,light,geometry)
            replay.process(layer,values,light,geometry,collect_events=False)
            if normal.trace:
                np.testing.assert_array_equal(normal.trace['local'][1],replay.trace['local'][1])
                np.testing.assert_array_equal(normal.ewma,replay.ewma)
        delta=abs(replay.ewma_light-replay.base_light)
        evidence=explain_trace(replay,{'kind':'derive_globale','box':geometry['roi'],'score':delta/config.drift_gray},geometry)
        self.assertTrue(evidence['ratio_verified']);self.assertAlmostEqual(evidence['delta'],delta)


if __name__=='__main__':unittest.main()
