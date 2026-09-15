import io
from pathlib import Path
import tempfile
import unittest
import numpy as np
from PIL import Image
from shape_reconstruction import part_overlap, section_mask, shape_preview


class ShapeTests(unittest.TestCase):
    @staticmethod
    def specimen():
        a=np.full((160,200),80,dtype=np.uint8)
        y,x=np.indices(a.shape)
        a[25:65,35:75]=(100+((x[25:65,35:75]+y[25:65,35:75])%4)*40).astype(np.uint8)
        a[90:135,120:165]=(100+((x[90:135,120:165]+y[90:135,120:165])%4)*40).astype(np.uint8)
        return a

    def test_textured_sections_and_uniform_powder(self):
        im=Image.fromarray(self.specimen());mask,stats=section_mask(im)
        a=np.asarray(mask)>0
        self.assertGreater(a[28:62,38:72].mean(),.95)
        self.assertGreater(a[93:132,123:162].mean(),.95)
        self.assertEqual(a[:15].sum(),0);self.assertEqual(a[70:80].sum(),0)
        self.assertGreater(stats['coverage_percent'],8);self.assertLess(stats['coverage_percent'],20)
        for powder in [np.full((160,200),90,np.uint8),np.tile(np.linspace(70,150,200,dtype=np.uint8),(160,1))]:
            self.assertEqual(np.asarray(section_mask(Image.fromarray(powder))[0]).sum(),0)

    def test_png_alpha_16bit_and_crop_without_changing_source(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'raw.png';eight=Path(folder)/'8bit.png'
            Image.fromarray(self.specimen().astype(np.uint16)*257).save(path)
            Image.fromarray(self.specimen()).save(eight)
            original=path.read_bytes()
            data,stats=shape_preview(path,65535,(0,0,200,160))
            other,_=shape_preview(eight,255,(0,0,200,160))
            with Image.open(io.BytesIO(data)) as mask,Image.open(io.BytesIO(other)) as mask8:
                self.assertEqual(mask.mode,'RGBA');np.testing.assert_array_equal(mask,mask8)
                cropped,_=shape_preview(path,65535,(30,20,80,70))
                with Image.open(io.BytesIO(cropped)) as crop:np.testing.assert_array_equal(crop,mask.crop((30,20,80,70)))
            self.assertEqual(path.read_bytes(),original)
            self.assertLessEqual(max(stats['width'],stats['height']),512)
            for contrast in [0,9,'nan']:
                with self.assertRaises(ValueError):shape_preview(path,65535,(0,0,200,160),contrast)
            with self.assertRaises(ValueError):shape_preview(path,65535,(-1,0,200,160))

    def test_cache_invalidated_when_source_changes(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'image.png';Image.fromarray(self.specimen()).save(path)
            data,stats=shape_preview(path,255,(0,0,200,160));self.assertGreater(stats['coverage_percent'],0)
            Image.new('L',(200,160),80).save(path)
            data2,stats2=shape_preview(path,255,(0,0,200,160));self.assertEqual(stats2['coverage_percent'],0)
            self.assertNotEqual(data,data2)

    def test_part_overlap_marks_boxes_on_extracted_shape(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'image.png';Image.fromarray(self.specimen()).save(path)
            self.assertGreater(part_overlap(path,255,(40,30,70,60)),.9)
            self.assertEqual(part_overlap(path,255,(80,70,110,88)),0)


if __name__=='__main__':unittest.main()
