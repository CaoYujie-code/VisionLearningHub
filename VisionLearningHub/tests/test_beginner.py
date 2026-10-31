"""The beginner read-image reference must run with native libraries alone."""
import tempfile,unittest
from pathlib import Path
import test_platform as baseline
import cv2
import numpy as np
from learning.curriculum import BY_ID

class BeginnerReferenceChecks(unittest.TestCase):
    def test_native_reference_reads_real_unicode_path_without_injected_helpers(self):
        scope={};exec(BY_ID['T01']['reference'],scope)
        with tempfile.TemporaryDirectory() as folder:
            image=np.zeros((13,21,3),np.uint8);image[0,0]=[5,40,210]
            path=Path(folder)/'中文图像 空格.png';cv2.imencode('.png',image)[1].tofile(path)
            actual=scope['solve'](np.zeros((2,2,3),np.uint8),{'image_path':str(path)})
            self.assertEqual(actual,dict(width=21,height=13,channels=3,pixel=[5,40,210]))
            self.assertNotIn('read_image',scope)

    def test_native_reference_rejects_missing_and_undecodable_files(self):
        scope={};exec(BY_ID['T01']['reference'],scope)
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'not-an-image.png';path.write_bytes(b'not a png')
            with self.assertRaisesRegex(ValueError,'解码失败'):scope['solve'](None,{'image_path':str(path)})
            with self.assertRaises(FileNotFoundError):scope['solve'](None,{'image_path':str(Path(folder)/'missing.png')})

if __name__=='__main__':unittest.main(verbosity=2)
