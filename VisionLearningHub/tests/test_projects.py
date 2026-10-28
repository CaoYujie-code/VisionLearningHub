"""Engineering deliverables, negative cases, independent CLI export and learner data boundaries."""
import copy
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile
import numpy as np
import cv2
import test_platform as baseline
from learning.project_catalog import PROJECTS, PROJECT_LESSONS, source_bundle
from learning.project_data import prepare, verify_assets
from learning.project_runner import execute, parse_files, serialize, materialize, run_main, assess
from learning.storage import fingerprint

class EngineeringChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        baseline.PlatformChecks.setUpClass.__func__(cls)
        cls.project_codes={p['id']:p['reference'] for p in PROJECT_LESSONS}

    wait_job=baseline.PlatformChecks.wait_job
    run_code=baseline.PlatformChecks.run_code

    def test_01_all_project_references_and_hashes(self):
        verify_assets()
        for key in self.project_codes:
            response=execute(dict(lesson=key,codes=self.project_codes,verify=True,folder=str(Path(baseline.TEMP.name)/'projects-reference'/key)))
            self.assertTrue(response['passed'],(key,response))
            self.assertEqual(len(response['reports']),5)
            self.assertTrue(all(Path(r['input']).is_file() and Path(r['output']).is_file() for r in response['reports']))

    def test_02_graders_reject_incomplete_or_fabricated_deliverables(self):
        with tempfile.TemporaryDirectory() as folder:
            for key in self.project_codes:
                root=Path(folder)/key;source=root/'source';inputs=root/'input';output=root/'output'
                materialize(key,source,source_bundle(key,True))
                truth,manifest=prepare(key,101,inputs)
                run_main(source,inputs,output)
                self.assertTrue(all(c['ok'] for c in assess(key,inputs,output,truth,manifest)[0]))
                good=json.loads((output/'results.json').read_text(encoding='utf-8'))
                mutants=[]
                duplicate=copy.deepcopy(good);duplicate['records'].append(duplicate['records'][0]);mutants.append(duplicate)
                missing=copy.deepcopy(good);missing['records']=missing['records'][1:];mutants.append(missing)
                wrong=copy.deepcopy(good)
                for record in wrong['records']:
                    if 'error' in record:continue
                    if key=='E01':record.update(count=0,centers=[])
                    if key=='E02':record.update(boxes=[],decision='accept')
                    if key=='E03':record.update(corners=[])
                    if key=='E05':record.update(objects=[])
                    if key=='E06':record.update(status='ok',sizes_mm=[])
                    if key=='E07':record.update(corners=[],decision='missing')
                    if key=='E08':record.update(assignments=[],valid=True)
                    if key=='E09':record.update(status='not_found',corners=[])
                    if key=='E04':
                        for obj in record['objects']:obj['id']=record['file']+str(obj['id'])
                mutants.append(wrong)
                if key=='E04':
                    wrong_event=copy.deepcopy(good);wrong_event['events']=[];mutants.append(wrong_event)
                else:
                    wrong_error=copy.deepcopy(good)
                    for record in wrong_error['records']:
                        if 'error' in record:record['error']='ignored'
                    mutants.append(wrong_error)
                for mutant in mutants:
                    (output/'results.json').write_text(json.dumps(mutant),encoding='utf-8')
                    self.assertFalse(all(c['ok'] for c in assess(key,inputs,output,truth,manifest)[0]),key)
                (output/'results.json').write_text(json.dumps(good),encoding='utf-8')
                next((output/'overlays').glob('*.png')).unlink()
                self.assertFalse(all(c['ok'] for c in assess(key,inputs,output,truth,manifest)[0]),key)

    def test_03_exported_project_runs_without_platform_imports(self):
        for key in self.project_codes:
            self.client.put('/api/lesson/'+key,json={'code':self.project_codes[key],'note':'engineering note'}).raise_for_status()
            archive=self.client.get('/api/projects/'+key+'/export');archive.raise_for_status()
            with tempfile.TemporaryDirectory(prefix='工程CLI-') as folder:
                with zipfile.ZipFile(io.BytesIO(archive.content)) as zipped:
                    self.assertIn(key+'/data/sample/_manifest.json',zipped.namelist())
                    self.assertIn(key+'/data/holdout/995/_manifest.json',zipped.namelist())
                    self.assertIn(key+'/SOURCES.json',zipped.namelist())
                    zipped.extractall(folder)
                root=Path(folder)/key
                env=os.environ.copy();env['PYTHONUTF8']='1';env.pop('PYTHONPATH',None)
                process=subprocess.run([sys.executable,'main.py','--input','data/sample','--output','output'],cwd=root,env=env,capture_output=True,text=True,encoding='utf-8',timeout=20)
                self.assertEqual(process.returncode,0,process.stderr)
                self.assertTrue((root/'output/results.json').is_file())

    def test_04_module_and_config_are_part_of_snapshot(self):
        files=source_bundle('E01',True);files['detector.py']='def learning_marker():\n    return 1\n'
        files['pipeline.py']='from detector import learning_marker\n'+files['pipeline.py']
        codes={**self.project_codes,'E01':serialize(files)}
        response=execute(dict(lesson='E01',codes=codes,verify=False,folder=str(Path(baseline.TEMP.name)/'modules')))
        self.assertTrue(response['passed'],response)
        before=fingerprint('E01',{**self.references,**codes})
        changed_prerequisite={**self.references,**codes,'T06':'changed unrelated prior exercise'}
        self.assertEqual(before,fingerprint('E01',changed_prerequisite))
        files['detector.py']+='\n# changed helper\n';codes['E01']=serialize(files)
        self.assertNotEqual(before,fingerprint('E01',{**self.references,**codes}))
        files['config.json']='{ invalid while typing'
        response=self.client.put('/api/lesson/E01',json={'code':serialize(files),'note':'draft config'})
        self.assertEqual(response.status_code,200,response.text)
        response=execute(dict(lesson='E01',codes={'E01':serialize(files)},verify=False,folder=str(Path(baseline.TEMP.name)/'invalid-config')))
        self.assertFalse(response['passed'])
        self.assertIn('JSONDecodeError',response['reports'][0]['summary'])

    def test_05_custom_image_is_exploration_only(self):
        self.client.put('/api/lesson/E01',json={'code':self.project_codes['E01'],'note':''}).raise_for_status()
        raw=cv2.imencode('.png',np.zeros((120,180,3),np.uint8))[1].tobytes()
        upload=self.client.post('/api/upload',files={'file':('自己的图片.png',raw,'image/png')}).json()
        body=dict(lesson='E01',code=self.project_codes['E01'],verify=False,upload_id=upload['id'])
        response=self.client.post('/api/jobs',json=body);response.raise_for_status();job=self.wait_job(response.json()['id'])
        self.assertTrue(job['result']['passed'],job)
        self.assertFalse(job['result']['verify'])
        self.assertFalse(self.client.get('/api/bootstrap').json()['passed']['E01'])
        self.assertIn('没有人工真值',job['result']['reports'][0]['checks'][0]['detail'])
        self.assertEqual(self.client.post('/api/jobs',json={**body,'verify':True}).status_code,400)
        self.assertEqual(self.client.post('/api/jobs',json={**body,'lesson':'E02'}).status_code,400)
        self.assertEqual(self.client.post('/api/jobs',json={**body,'upload_id':'../anything'}).status_code,400)

    def test_06_project_notes_and_code_survive_backup(self):
        note=json.dumps({'projectNote':1,'text':'自定义函数分工','completed':[0,2,4]},ensure_ascii=False)
        code=self.project_codes['E02']
        self.client.put('/api/lesson/E02',json={'code':code,'note':note}).raise_for_status()
        backup=self.client.get('/api/backup');backup.raise_for_status()
        self.client.put('/api/lesson/E02',json={'code':serialize(source_bundle('E02')),'note':''}).raise_for_status()
        self.client.post('/api/restore',files={'file':('backup.zip',backup.content,'application/zip')}).raise_for_status()
        result=self.client.get('/api/projects/E02').json()
        self.assertEqual(result['note'],note)
        self.assertEqual(result['files'],parse_files(code))

    def test_07_source_and_route_boundaries(self):
        for name in ['../escape.py','sub/f.py','C:/evil.py','_secret.py','config.JSON']:
            with self.subTest(name=name),self.assertRaises(ValueError):parse_files({**source_bundle('E01'),name:'pass'})
        self.assertEqual(self.client.get('/api/projects/E99').status_code,404)
        self.assertEqual(self.client.get('/api/projects/E01',headers={'X-VLH-Token':''}).status_code,403)

    def test_08_todo_and_malformed_delivery_do_not_pass(self):
        for source in [source_bundle('E01'),{**source_bundle('E01',True),'pipeline.py':'def run_batch(*args):\n    return 24\n'}]:
            with tempfile.TemporaryDirectory() as folder:
                response=execute(dict(lesson='E01',codes={'E01':serialize(source)},verify=False,folder=folder))
                self.assertFalse(response['passed'])

if __name__=='__main__':unittest.main(verbosity=2)
