"""Behavioral regression tests; all data is temporary and independent of the learner's database."""
import io
import json
import os
import sqlite3
from pathlib import Path
import sys
import tempfile
import time
import unittest
import zipfile

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
TEMP = tempfile.TemporaryDirectory(prefix='vision-hub-check-')
os.environ['VLH_DATA_ROOT'] = TEMP.name
os.environ['VLH_JOB_TIMEOUT'] = '2'
from fastapi.testclient import TestClient
from backend import server
from learning.curriculum import LESSONS, BY_ID
from learning.engine import execute, fixture, check_result


class PlatformChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(server.app, base_url='http://127.0.0.1')
        cls.client.headers['X-VLH-Token'] = server.TOKEN
        cls.references = {l['id']:l['reference'] for l in LESSONS}

    def wait_job(self, key):
        for _ in range(160):
            response = self.client.get('/api/jobs/' + key)
            self.assertEqual(response.status_code, 200)
            job = response.json()
            if job['status'] not in ('queued', 'running', 'stopping'):
                return job
            time.sleep(.05)
        self.fail('Worker did not finish')

    def run_code(self, key, code, verify=True):
        response = self.client.post('/api/jobs', json=dict(lesson=key, code=code, note='test note', verify=verify))
        self.assertEqual(response.status_code, 200, response.text)
        return self.wait_job(response.json()['id'])

    def test_01_all_reference_contracts(self):
        self.assertEqual(len(LESSONS), 53)
        for lesson in LESSONS:
            with self.subTest(lesson=lesson['id']):
                response = execute(dict(lesson=lesson['id'], codes=self.references, verify=True,
                                        folder=str(Path(TEMP.name)/'reference'/lesson['id'])))
                self.assertTrue(response['passed'], json.dumps(response,ensure_ascii=False))
                self.assertEqual(len(response['reports']),5)
        print('53 reference solutions / 265 fixtures (44 exercises + 9 multi-file projects) passed')

    def test_02_local_access_and_assets(self):
        self.assertEqual(self.client.get('/api/bootstrap',headers={'X-VLH-Token':''}).status_code,403)
        self.assertEqual(self.client.get('/api/bootstrap',headers={'Origin':'https://elsewhere.example'}).status_code,403)
        self.assertEqual(self.client.get('/api/health',headers={'Host':'evil.example'}).status_code,400)
        self.assertEqual(self.client.get('/api/assets/learning.sqlite3').status_code,404)
        self.assertEqual(self.client.post('/api/shutdown').status_code,403)
        boot=self.client.get('/api/bootstrap').json()
        self.assertEqual(len(boot['courses']),33)
        self.assertEqual(len(boot['resources']),35)
        assigned=[key for c in boot['courses'] for key in c['lessons']]
        self.assertEqual(sorted(assigned),sorted(self.references))
        self.assertNotIn('reference',boot['lessons'][0])
        for lesson in LESSONS:
            detail=self.client.get('/api/lesson/'+lesson['id'])
            self.assertEqual(detail.status_code,200,detail.text)
            image=self.client.get(detail.json()['input'])
            self.assertEqual(image.status_code,200)
            self.assertTrue(image.content.startswith(b'\x89PNG'))

    def test_03_worker_progress_and_staleness(self):
        failed=self.run_code('P01',BY_ID['P01']['starter'])
        self.assertEqual(failed['status'],'done')
        self.assertFalse(failed['result']['passed'])
        single=self.run_code('P01',self.references['P01'],False)
        self.assertTrue(single['result']['passed'])
        self.assertFalse(single['passed']['P01'])
        passed=self.run_code('P01',self.references['P01'])
        self.assertTrue(passed['passed']['P01'])
        self.client.put('/api/lesson/P01',json={'code':self.references['P01']+'\n# changed','note':'saved'})
        changed=self.client.get('/api/jobs/'+passed['id']).json()
        self.assertTrue(changed['stale'])
        self.assertFalse(changed['passed']['P01'])
        stored=self.client.get('/api/lesson/P01').json()
        self.assertEqual(stored['note'],'saved')
        self.assertEqual(len(stored['history']),3)

    def test_04_stop_and_timeout(self):
        code='def solve(image, params):\n    while True: pass\n'
        start=self.client.post('/api/jobs',json=dict(lesson='P02',code=code,note='',verify=False)).json()
        self.assertEqual(self.client.post('/api/jobs',json=dict(lesson='P02',code=code,note='',verify=False)).status_code,409)
        self.assertEqual(self.client.get('/api/bootstrap').json()['active_job']['id'],start['id'])
        self.client.post('/api/jobs/'+start['id']+'/stop')
        self.assertEqual(self.wait_job(start['id'])['status'],'cancelled')
        timed=self.run_code('P02',code,False)
        self.assertEqual(timed['status'],'timeout')

    def test_05_laboratory(self):
        import cv2
        import numpy as np
        for source in ['standard','dim','noise','same_color']:
            for method in ['gray','threshold','blur','hsv','canny']:
                response=self.client.post('/api/lab',json={'source':source,'method':method})
                self.assertEqual(response.status_code,200,response.text)
                result=response.json()
                self.assertIn('cv2.',result['code'])
                self.assertEqual(self.client.get(result['output']).status_code,200)
        raw=cv2.imencode('.png',np.full((40,60,3),100,np.uint8))[1].tobytes()
        uploaded=self.client.post('/api/upload',files={'file':('中文图像.png',raw,'image/png')}).json()
        result=self.client.post('/api/lab',json={'source':'upload:'+uploaded['id'],'method':'threshold','threshold':110}).json()
        self.assertEqual(result['nonzero'],0)
        self.assertEqual(result['width'],60)
        self.assertEqual(self.client.post('/api/lab',json={'low':200,'high':10}).status_code,400)
        self.assertEqual(self.client.post('/api/lab',json={'source':'upload:../../x'}).status_code,400)
        self.assertEqual(self.client.post('/api/upload',files={'file':('bad.png',b'not an image','image/png')}).status_code,400)

    def test_06_backup_roundtrip_and_rollback(self):
        self.client.put('/api/settings/bookmarks',json={'value':['R03','R08']})
        self.client.put('/api/settings/course.S00',json={'value':{'checks':[0,2],'note':'数组与坐标'}})
        backup=self.client.get('/api/backup')
        self.assertEqual(backup.status_code,200)
        self.client.put('/api/lesson/P01',json={'code':'changed','note':'changed'})
        self.client.put('/api/settings/bookmarks',json={'value':[]})
        restored=self.client.post('/api/restore',files={'file':('backup.zip',backup.content,'application/zip')})
        self.assertEqual(restored.status_code,200,restored.text)
        boot=self.client.get('/api/bootstrap').json()
        self.assertEqual(boot['settings']['hub.bookmarks'],['R03','R08'])
        self.assertEqual(boot['settings']['hub.course.S00']['note'],'数组与坐标')
        self.assertNotEqual(self.client.get('/api/lesson/P01').json()['code'],'changed')
        history=self.client.get('/api/lesson/P01').json()['history']
        self.assertEqual(self.client.get(history[0]['report']['reports'][0]['input']).status_code,200)
        bad=io.BytesIO()
        with zipfile.ZipFile(bad,'w') as archive:
            archive.writestr('../escape.txt','bad')
        response=self.client.post('/api/restore',files={'file':('bad.zip',bad.getvalue(),'application/zip')})
        self.assertEqual(response.status_code,400)
        self.assertEqual(self.client.get('/api/bootstrap').json()['settings']['hub.bookmarks'],['R03','R08'])
        # A structurally valid SQLite backup must not permit arbitrary filenames
        # via draft identifiers, nor invalid JSON settings that break startup.
        for mutation in ['UPDATE drafts SET id="../../escape" WHERE id="P01"',
                         "UPDATE settings SET value='not-json' WHERE key='hub.bookmarks'"]:
            with tempfile.TemporaryDirectory(dir=TEMP.name) as directory:
                db=Path(directory)/'learning.sqlite3'
                with zipfile.ZipFile(io.BytesIO(backup.content)) as archive:
                    db.write_bytes(archive.read('learning.sqlite3'))
                connection=sqlite3.connect(db);connection.execute(mutation);connection.commit();connection.close()
                altered=io.BytesIO()
                with zipfile.ZipFile(altered,'w') as archive:
                    archive.write(db,'learning.sqlite3')
                failed=self.client.post('/api/restore',files={'file':('altered.zip',altered.getvalue(),'application/zip')})
                self.assertEqual(failed.status_code,400,failed.text)
                self.assertEqual(self.client.get('/api/bootstrap').json()['settings']['hub.bookmarks'],['R03','R08'])
        export=self.client.get('/api/export-code')
        self.assertEqual(export.status_code,200)
        with zipfile.ZipFile(io.BytesIO(export.content)) as archive:
            self.assertIn('student/Y01.py',archive.namelist())
            self.assertIn('run_detector.py',archive.namelist())

    def test_07_domain_negative_answers(self):
        import numpy as np
        invalid={'Y01':lambda p,t:[True], 'Y02':lambda p,t:np.asarray(p['boxes']),
                 'Y03':lambda p,t:{'tp':0,'fp':0,'fn':0,'precision':1.,'recall':1.},
                 'L01':lambda p,t:{'error_count':7,'warning_count':0,'last_error':'unknown'}}
        for key, wrong in invalid.items():
            image,params,truth=fixture(key,101,Path(TEMP.name)/'negative'/key)
            self.assertFalse(all(c['ok'] for c in check_result(key,image,params,truth,wrong(params,truth))),key)


if __name__ == '__main__':
    try:
        unittest.main(verbosity=2)
    finally:
        TEMP.cleanup()
