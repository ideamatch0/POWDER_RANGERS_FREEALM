import json
import unittest
from persistence import consecutive_runs, minimum_count


def occurrence(identifier, layer, box=(0,0,10,10), phase='fusion', camera='cam1', kind='changement_local', geometry='g'):
    return {'id':identifier,'start_layer':layer,'box':json.dumps(box),'phase':phase,'camera':camera,'kind':kind,'geometry_key':geometry}


class PersistenceTests(unittest.TestCase):
    def test_counts_whole_run_including_its_first_occurrence(self):
        rows=[occurrence(str(i),i) for i in [2,3,4,6]]
        result=consecutive_runs(rows)
        for i in [2,3,4]:
            self.assertEqual(result[str(i)],{'consecutive_count':3,'persistence_start':2,'persistence_end':4})
        self.assertEqual(result['6']['consecutive_count'],1)

    def test_different_location_or_stream_never_extends_run(self):
        for field,value in [('box',json.dumps([10,0,20,10])),('phase','etalement'),('camera','cam2'),('kind','derive_locale'),('geometry_key','different')]:
            with self.subTest(field=field):
                a=occurrence('a',1);b=occurrence('b',2);b[field]=value
                self.assertTrue(all(r['consecutive_count']==1 for r in consecutive_runs([a,b]).values()))

    def test_multiple_boxes_on_one_image_are_not_multiple_layers(self):
        rows=[occurrence(str(i),1) for i in range(10)]+[occurrence('next',2)]
        self.assertTrue(all(r['consecutive_count']==2 for r in consecutive_runs(rows).values()))

    def test_alternation_and_missing_acquisition(self):
        rows=[occurrence(str(i),i,phase='sequence'+str(i%2)) for i in [2,3,4,5,6,9]]
        result=consecutive_runs(rows,step=2)
        self.assertEqual(result['2']['consecutive_count'],3)
        self.assertEqual(result['3']['consecutive_count'],2)
        self.assertEqual(result['9']['consecutive_count'],1)

    def test_branch_does_not_inherit_unrelated_end_of_run(self):
        rows=[occurrence('a',1),occurrence('b',2),occurrence('c',3,box=(0,0,30,10)),
              occurrence('d',4,box=(0,0,10,10)),occurrence('e',4,box=(20,0,30,10)),
              occurrence('f',5,box=(20,0,30,10)),occurrence('g',6,box=(20,0,30,10))]
        result=consecutive_runs(rows)
        self.assertEqual(result['d']['consecutive_count'],4)
        self.assertEqual(result['e']['consecutive_count'],6)

    def test_invalid_minimum_rejected(self):
        for value in [0,-1,1.5,True,'3',10001,None]:
            with self.assertRaises(ValueError):minimum_count(value)
        self.assertEqual(minimum_count(3),3)
