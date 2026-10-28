"""Calibration has independent truth, error recomputation and ordinary CLI deliverables."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
import test_platform as baseline
from learning.project_catalog import source_bundle
from learning.project_runner import write_sources,run_main,assess
from learning.project_data import prepare
from learning.project_studies import study
from learning.project_guides import guide_readme
from learning.storage import Store

class CalibrationChecks(unittest.TestCase):
    def test_truth_and_reprojection_reject_fabricated_models(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);source=root/'source';inputs=root/'input';output=root/'output'
            write_sources(source,source_bundle('E09',True));truth,manifest=prepare('E09',207,inputs)
            run_main(source,inputs,output);good=json.loads((output/'results.json').read_text(encoding='utf-8'))
            self.assertTrue(all(c['ok'] for c in assess('E09',inputs,output,truth,manifest)[0]))
            self.assertFalse((inputs/'calibration.json').exists())
            self.assertNotIn('distortion',(inputs/'_manifest.json').read_text(encoding='utf-8'))
            variants=[]
            wrong=copy.deepcopy(good);wrong['calibration']['matrix'][0][0]*=1.2;variants.append(wrong)
            wrong=copy.deepcopy(good);wrong['calibration']['distortion']=[0]*5;variants.append(wrong)
            wrong=copy.deepcopy(good);wrong['calibration']['rms']=0;wrong['calibration']['view_errors']={k:0 for k in wrong['calibration']['view_errors']};variants.append(wrong)
            wrong=copy.deepcopy(good);wrong['calibration']['distortion'][0]=float('nan');variants.append(wrong)
            wrong=copy.deepcopy(good);wrong['calibration']['view_errors']={};variants.append(wrong)
            for value in variants:
                (output/'results.json').write_text(json.dumps(value),encoding='utf-8')
                self.assertFalse(all(c['ok'] for c in assess('E09',inputs,output,truth,manifest)[0]))
            (output/'results.json').write_text(json.dumps(good),encoding='utf-8')
            # A saved original is not a calibrated image.
            import shutil
            name=next(v['file'] for v in good['records'] if v.get('status')=='ok');shutil.copyfile(inputs/name,output/'undistorted'/name)
            self.assertFalse(all(c['ok'] for c in assess('E09',inputs,output,truth,manifest)[0]))

    def test_api_keeps_descriptive_input_output(self):
        from fastapi.testclient import TestClient
        client=TestClient(baseline.server.app,base_url='http://127.0.0.1')
        client.headers['X-VLH-Token']=baseline.server.TOKEN
        for i in range(1,10):
            data=client.get(f'/api/projects/E{i:02}').json()
            self.assertIsInstance(data['project']['output'],str)
            self.assertGreater(len(data['project']['output']),40)
            self.assertTrue(all(isinstance(step['input'],str) and step['input'] for step in data['guide']['study']['steps']))
            self.assertTrue(data['images'][0]['input'].startswith('/api/assets/'))

    def test_studies_export_and_selfcheck_do_not_grant_acceptance(self):
        self.assertEqual(sum(len(study(f'E{i:02}')['steps']) for i in range(1,10)),37)
        for i in range(1,10):
            key=f'E{i:02}';value=study(key);text=guide_readme(key)
            self.assertIn(value['comparison']['title'],text);self.assertIn(value['repair']['task'],text)
            self.assertTrue(all(s['input'] and s['implementation'] and s['evidence'] for s in value['steps']))
        self.assertEqual(len(baseline.server.COURSES),33)
        self.assertEqual(len({c['id'] for c in baseline.server.COURSES}),33)

if __name__=='__main__':unittest.main(verbosity=2)
