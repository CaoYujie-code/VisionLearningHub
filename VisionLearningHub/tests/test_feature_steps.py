"""E07 isolated steps, failure rejection, and complete-project distinction."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import test_platform as baseline
from learning.project_catalog import source_bundle
from learning.project_runner import serialize, materialize
from learning.project_checkpoints import execute
from learning.feature_steps import IDS, STANDARD, assess_step

class FeatureStepChecks(unittest.TestCase):
    def run_step(self, files, block, source='own'):
        folder=tempfile.TemporaryDirectory();self.addCleanup(folder.cleanup)
        return execute(dict(lesson='E07',codes={'E07':serialize(files)},folder=folder.name,verify=False,project_block=block,block_source=source))

    def test_all_new_reference_steps_and_sources(self):
        files=source_bundle('E07',True)
        for block in IDS:
            for source in (('own','standard') if block in STANDARD else ('own',)):
                with self.subTest(block=block,source=source):
                    r=self.run_step(files,block,source)
                    self.assertTrue(r['passed'],r)
                    self.assertFalse(r['verify'])
                    self.assertEqual(len(r['reports']),2)
                    self.assertTrue(all(s['facts'] for s in r['reports']))

    def test_standard_upstream_does_not_require_student_features(self):
        files=source_bundle('E07',True)
        files['feature_steps.py']=files['feature_steps.py'].replace("def run_step(block,input_dir,output_dir,config):", "def run_step(block,input_dir,output_dir,config):\n    if block=='features':raise RuntimeError('student features unfinished')")
        # Use source inspection to keep this deliberate branch corruption meaningful.
        self.assertIn("raise RuntimeError('student features unfinished')",files['feature_steps.py'])
        self.assertTrue(self.run_step(files,'matches','standard')['passed'])
        self.assertFalse(self.run_step(files,'matches','own')['passed'])

    def test_fake_descriptors_and_wrong_distance_are_rejected(self):
        files=source_bundle('E07',True)
        bad=source_bundle('E07',False)
        r=self.run_step(bad,'repair')
        self.assertFalse(r['passed'])
        self.assertTrue(any(not c['ok'] for s in r['reports'] for c in s['checks']))
        from learning.feature_steps import validate_features
        import numpy as np
        import cv2
        rng=np.random.default_rng(99);image=rng.integers(0,256,(160,200,3),dtype=np.uint8)
        keys,desc=cv2.ORB_create(nfeatures=100,edgeThreshold=8).detectAndCompute(cv2.cvtColor(image,cv2.COLOR_BGR2GRAY),None)
        value=dict(keypoints=[[p.pt[0],p.pt[1],p.size,p.angle,p.response,p.octave] for p in keys],descriptors=np.zeros_like(desc).tolist())
        self.assertFalse(validate_features(value,image,40)[0])

    def test_standard_export_has_inputs_but_no_reference_source(self):
        with tempfile.TemporaryDirectory() as folder:
            materialize('E07',Path(folder),source_bundle('E07'))
            self.assertTrue((Path(folder)/'FEATURE_STEPS.md').is_file())
            standard=Path(folder)/'data/feature_standard'
            for name in ('_features.json','_matches.json','_comparison.json','_repair.json'):
                self.assertTrue((standard/name).is_file(),name)
            self.assertFalse(list(standard.rglob('*.py')))

if __name__=='__main__':unittest.main(verbosity=2)
