import unittest
from priority import legacy_priority_value, priority_value, with_priority, priority_text
from persistence import page_after


class PriorityTests(unittest.TestCase):
    def test_readable_landmarks_and_monotonic_components(self):
        self.assertEqual(legacy_priority_value(2,3),50)
        self.assertEqual(legacy_priority_value(6,6),70.7)
        self.assertEqual(priority_value(2,3),42.5)
        self.assertEqual(priority_value(6,6),55.4)
        for n in (1,2,3,10,100):
            scores=[priority_value(r,n) for r in (1,2,3,6,20,100)]
            self.assertEqual(scores,sorted(scores))
            self.assertTrue(all(0<=s<=100 for s in scores))
        self.assertLess(priority_value(2,1),priority_value(2,3))
        self.assertLess(priority_value(2,3),priority_value(2,10))
        raw={'score':2,'start_layer':10,'end_layer':12,'snapshot':'unchanged'}
        scored=with_priority(raw)
        self.assertNotIn('priority_score',raw)
        self.assertEqual(scored['score'],2);self.assertEqual(scored['snapshot'],'unchanged')
        self.assertEqual(scored['variation_component'],50);self.assertEqual(scored['persistence_component'],50)
        self.assertIn('42.5 / 100',priority_text(scored))

    def test_composite_score_uses_area_part_and_stage(self):
        low=with_priority({'score':2,'start_layer':10,'end_layer':12,'box':'[0,0,16,16]','phase':'etalement','kind':'changement_local','part_overlap':0})
        high=with_priority({'score':2,'start_layer':10,'end_layer':12,'box':'[0,0,128,128]','phase':'fusion','kind':'changement_local','part_overlap':1})
        self.assertGreater(high['priority_score'],low['priority_score'])
        self.assertEqual(high['part_component'],100)
        self.assertEqual(high['stage_component'],100)
        self.assertGreater(high['area_component'],low['area_component'])
        self.assertEqual(high['legacy_priority_score'],low['legacy_priority_score'])

    def test_priority_pagination_after_removed_anchor_and_ties(self):
        rows=[with_priority({'id':f'{i}:0','peak_frame':i,'prediction':0,'start_layer':i,'end_layer':i,
                             'score':10 if i<28 else 2,'consecutive_count':3}) for i in range(60)]
        first=page_after(list(reversed(rows)),sort='priority')
        self.assertEqual(first['items'],rows[:25])
        anchor=rows[24];remaining=[r for r in rows if r is not anchor]
        after=page_after(remaining,anchor=anchor,sort='priority')
        self.assertEqual(after['next_id'],rows[25]['id']);self.assertEqual(after['items'][24]['id'],rows[25]['id'])
        last=page_after(rows,anchor=rows[-1],sort='priority');self.assertIsNone(last['next_id'])
        with self.assertRaises(ValueError):page_after(rows,sort='unknown')

    def test_invalid_values_rejected(self):
        for r,n in [(float('nan'),1),(float('inf'),1),(-1,2),(1,0)]:
            with self.assertRaises(ValueError):priority_value(r,n)


if __name__=='__main__':unittest.main()
