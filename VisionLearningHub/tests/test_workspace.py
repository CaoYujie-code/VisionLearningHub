"""File source-of-truth, ordinary imports, cleanup and restore boundaries."""
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
TEMP = tempfile.TemporaryDirectory(prefix='vlh-workspace-')
ROOT = Path(TEMP.name)
os.environ['VLH_DATA_ROOT'] = str(ROOT / 'data')
os.environ['VLH_WORKSPACE'] = str(ROOT / 'workspace')
from fastapi.testclient import TestClient
from backend import server
from backend.workspace import native_code
from learning.curriculum import LESSONS
from learning.storage import export_project
from learning.engine import execute


class WorkspaceChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(server.app, base_url='http://127.0.0.1')
        cls.client.headers['X-VLH-Token'] = server.TOKEN
        cls.client.get('/api/bootstrap').raise_for_status()

    def file(self, key):
        return ROOT / 'workspace/exercises' / (key + '.py')

    def test_01_all_native_references_and_real_debug_entry(self):
        codes = {x['id']:native_code(x['reference']) for x in LESSONS}
        for key,code in codes.items():
            self.file(key).write_text(code,encoding='utf-8')
            result=execute(dict(lesson=key,codes=codes,verify=True,folder=str(ROOT/'native'/key)))
            self.assertTrue(result['passed'], (key,result))
        result=subprocess.run([sys.executable,'-m','learning.debug_runner','--workspace',str(ROOT/'workspace'),'--lesson','T14','--output',str(ROOT/'debug')],cwd=PROJECT,capture_output=True,text=True,encoding='utf-8')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertTrue((ROOT/'debug/output.png').exists())
        export_project(ROOT/'export',codes)
        image=next((ROOT/'debug').glob('input*.png'))
        result=subprocess.run([sys.executable,'run_detector.py',str(image)],cwd=ROOT/'export',capture_output=True,text=True,encoding='utf-8')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertTrue((ROOT/'export/output/pieces.json').exists())

    def test_02_file_wins_over_stale_web_save_and_job(self):
        key='P01'; code=next(x['reference'] for x in LESSONS if x['id']==key)
        self.file(key).write_text(code,encoding='utf-8')
        self.client.put('/api/lesson/P01',json={'code':'stale','note':'keep note'}).raise_for_status()
        self.assertEqual(self.file(key).read_text(encoding='utf-8'),code)
        job=self.client.post('/api/jobs',json={'lesson':key,'code':'stale','note':'keep note','verify':True}).json()
        for _ in range(100):
            result=self.client.get('/api/jobs/'+job['id']).json()
            if result['status'] not in ('queued','running'):break
            time.sleep(.05)
        self.assertTrue(result['result']['passed'])
        self.file(key).write_text(code+'\n# new revision',encoding='utf-8')
        self.assertFalse(self.client.get('/api/bootstrap').json()['passed'][key])

    def test_03_confirmation_and_busy_guard(self):
        self.assertEqual(self.client.post('/api/clear',json={'scope':'all','confirmation':'no'}).status_code,400)
        server.JOBS['busy-test']={'status':'running'}
        try:self.assertEqual(self.client.post('/api/clear',json={'scope':'all','confirmation':'CLEAR'}).status_code,409)
        finally:server.JOBS.pop('busy-test')

    def test_04_clear_scopes_preserve_files(self):
        before={p.name:p.read_bytes() for p in (ROOT/'workspace/exercises').glob('*.py')}
        self.client.put('/api/settings/bookmarks',json={'value':['R01']}).raise_for_status()
        self.client.post('/api/clear',json={'scope':'cache','confirmation':'CLEAR'}).raise_for_status()
        self.assertGreater(self.client.get('/api/bootstrap').json()['attempts'],0)
        self.client.post('/api/clear',json={'scope':'history','confirmation':'CLEAR'}).raise_for_status()
        self.assertEqual(self.client.get('/api/bootstrap').json()['attempts'],0)
        self.assertEqual(self.client.get('/api/lesson/P01').json()['note'],'keep note')
        self.client.post('/api/clear',json={'scope':'all','confirmation':'CLEAR'}).raise_for_status()
        self.assertEqual(self.client.get('/api/bootstrap').json()['settings'],{})
        self.assertEqual(self.client.get('/api/lesson/P01').json()['note'],'')
        self.assertEqual(before,{p.name:p.read_bytes() for p in (ROOT/'workspace/exercises').glob('*.py')})

    def test_05_reset_backups_and_restore_does_not_overwrite(self):
        previous=self.file('P01').read_text(encoding='utf-8')
        archive=self.client.get('/api/backup').content
        result=self.client.post('/api/workspace/reset/P01',json={'scope':'exercise','confirmation':'CLEAR'}).json()
        self.assertEqual(Path(result['backup']).read_text(encoding='utf-8'),previous)
        self.assertIn('TODO',self.file('P01').read_text(encoding='utf-8'))
        reset=self.file('P01').read_text(encoding='utf-8')
        self.client.post('/api/restore',files={'file':('backup.zip',archive,'application/zip')}).raise_for_status()
        self.assertEqual(self.file('P01').read_text(encoding='utf-8'),reset)
        imported=list((ROOT/'data/restored-code').glob('*/P01.py'))
        self.assertEqual(imported[0].read_text(encoding='utf-8'),previous)


if __name__=='__main__':
    unittest.main(verbosity=2)
