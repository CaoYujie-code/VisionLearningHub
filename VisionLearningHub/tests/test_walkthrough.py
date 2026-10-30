"""Visual course contract, real native examples, persistence and untrusted imports."""
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

import test_platform as baseline
import cv2
import numpy as np
from learning import walkthrough as w


class WalkthroughChecks(unittest.TestCase):
    def setUp(self):
        self.client=baseline.TestClient(baseline.server.app,base_url='http://127.0.0.1')
        self.client.headers['X-VLH-Token']=baseline.server.TOKEN

    def get(self,key='T03'):
        response=self.client.get('/api/lesson/'+key+'/walkthrough');response.raise_for_status();return response.json()

    def pack(self,key='T03',value=130,extra=None,partial=False):
        with tempfile.TemporaryDirectory() as folder:
            folder=Path(folder)
            files=w.bundle(baseline.server.ROOT,key,value)
            for name,raw in files.items():(folder/name).write_bytes(raw)
            process=subprocess.run([sys.executable,str(folder/'reference.py')],capture_output=True,env={**os.environ,'PYTHONUTF8':'1'},timeout=20)
            self.assertEqual(process.returncode,0,process.stderr.decode('utf-8'))
            raw=(folder/'results.zip').read_bytes()
        if extra or partial:
            modified=io.BytesIO()
            with zipfile.ZipFile(io.BytesIO(raw)) as original,zipfile.ZipFile(modified,'w') as target:
                for name in original.namelist():
                    if partial and name not in ('context.json','step1.npy'):continue
                    target.writestr(name,original.read(name))
                for name,value in (extra or {}).items():target.writestr(name,value)
            raw=modified.getvalue()
        return raw

    def upload(self,key,raw):
        return self.client.post('/api/lesson/'+key+'/walkthrough/import',files={'file':('results.zip',raw,'application/zip')})

    def test_all_courses_and_parameter_variants_are_real(self):
        self.assertEqual(set(w.CATALOG),{'T01','T02','T03','T04','T05','T06','A01','A02','A03',*[f'V{i:02d}' for i in range(1,15)]})
        for key,item in w.CATALOG.items():
            for value in item['control']['values']:
                response=self.client.post('/api/lesson/'+key+'/walkthrough/demo',json={'parameter':value});response.raise_for_status();demo=response.json()
                self.assertEqual(len(demo['results']),len(item['steps']))
                for s in item['steps']:
                    self.assertTrue(all(s[f] for f in ('why','watch','failure','question','answer','lines')))
                    self.assertTrue(self.client.get(demo['results'][s['id']]['output']).content.startswith(b'\x89PNG'))
                if key=='V04':
                    self.assertLess(demo['results']['step1']['minimum'],0)
                    self.assertGreater(demo['results']['step1']['maximum'],255)
                    self.assertEqual(demo['results']['step1']['dtype'],'float32')
        self.assertEqual(self.client.get('/api/lesson/T14/walkthrough').status_code,400)
        self.assertEqual(self.client.post('/api/lesson/T03/walkthrough/demo',json={'parameter':101}).status_code,400)
        for value in (True,'100',100.5):self.assertEqual(self.client.post('/api/lesson/T03/walkthrough/demo',json={'parameter':value}).status_code,422)

    def test_portable_scripts_execute_for_all_courses_without_platform_imports(self):
        before=self.client.get('/api/bootstrap').json()['passed']
        for key,item in w.CATALOG.items():
            value=item['control']['default'];raw=self.pack(key,value)
            response=self.upload(key,raw);response.raise_for_status();own=response.json()
            self.assertEqual(len(own['results']),len(item['steps']))
            demo=w.demonstration(baseline.server.ROOT,key,value)
            for s in item['steps']:
                actual=own['results'][s['id']]
                for name in ('shape','dtype'):self.assertEqual(actual[name],demo['results'][s['id']][name])
                for name in ('minimum','maximum'):self.assertAlmostEqual(actual[name],demo['results'][s['id']][name],delta=max(1e-4,abs(actual[name])*1e-6))
                expected=cv2.imdecode(np.frombuffer(Path(demo['results'][s['id']]['output']).read_bytes(),np.uint8),cv2.IMREAD_UNCHANGED)
                got=cv2.imdecode(np.frombuffer(self.client.get(actual['output']).content,np.uint8),cv2.IMREAD_UNCHANGED)
                np.testing.assert_allclose(got.astype(float),expected.astype(float),atol=1,rtol=0)
        self.assertEqual(self.client.get('/api/bootstrap').json()['passed'],before)

    def test_threshold_is_strict_and_parameter_changes_real_pixels(self):
        low=w.demonstration(baseline.server.ROOT,'T03',60);high=w.demonstration(baseline.server.ROOT,'T03',210)
        self.assertGreater(low['results']['step2']['nonzero'],high['results']['step2']['nonzero'])
        code=w.CATALOG['T03']['steps'][1]['code']
        scope=dict(cv2=cv2,np=np,gray=np.array([[99,100,101]],np.uint8),params={'threshold':100})
        exec(code,scope);np.testing.assert_array_equal(scope['mask'],[[0,0,255]])

    def test_partial_results_do_not_fabricate_missing_steps(self):
        response=self.upload('T03',self.pack(partial=True));response.raise_for_status()
        self.assertEqual(set(response.json()['results']),{'step1'})
        with tempfile.TemporaryDirectory() as folder:
            folder=Path(folder)
            for name,raw in w.bundle(baseline.server.ROOT,'T03',130).items():(folder/name).write_bytes(raw)
            subprocess.run([sys.executable,str(folder/'practice.py')],check=True,capture_output=True,env={**os.environ,'PYTHONUTF8':'1'},timeout=20)
            empty=self.upload('T03',(folder/'results.zip').read_bytes());empty.raise_for_status();self.assertEqual(empty.json()['results'],{})

    def test_bad_imports_are_rejected_and_previous_snapshot_survives(self):
        self.upload('T03',self.pack()).raise_for_status();old=self.get()['own']
        self.assertEqual(self.upload('T03',b'not a zip').status_code,400)
        self.assertEqual(self.upload('T03',self.pack(extra={'../escape.py':b'bad'})).status_code,400)
        self.assertEqual(self.upload('T04',self.pack()).status_code,400)
        good=self.pack();buf=io.BytesIO()
        np.save(buf,np.array([[float('nan')]],np.float32),allow_pickle=False)
        for data in (buf.getvalue(),b'invalid npy'):
            changed=io.BytesIO()
            with zipfile.ZipFile(io.BytesIO(good)) as source,zipfile.ZipFile(changed,'w') as target:
                for name in source.namelist():target.writestr(name,data if name=='step1.npy' else source.read(name))
            self.assertEqual(self.upload('T03',changed.getvalue()).status_code,400)
        self.assertEqual(self.get()['own'],old)

    def test_progress_and_imported_images_restore_separately_from_grades(self):
        row=self.get()['progress'];row.update(step=1,mode='write',notes={'step2':'预测白色区域缩小；实测吻合'},done=[0],parameter=210)
        self.client.post('/api/lesson/T03/walkthrough/progress',json=row).raise_for_status()
        self.upload('T03',self.pack(value=210)).raise_for_status()
        before=self.get();self.assertEqual(before['progress'],row);self.assertEqual(before['demo']['parameter'],210)
        raw=self.client.get('/api/backup').content
        self.client.post('/api/clear',json=dict(scope='all',confirmation='CLEAR')).raise_for_status()
        cleared=self.get();self.assertEqual(cleared['progress']['done'],[]);self.assertIsNone(cleared['own'])
        self.client.post('/api/restore',files={'file':('backup.zip',raw,'application/zip')}).raise_for_status()
        restored=self.get();self.assertEqual(restored['progress'],row)
        self.assertEqual(self.client.get(restored['own']['results']['step2']['output']).status_code,200)
        for field,value in [('step',True),('done',[99]),('mode','unknown'),('notes',{'bad':'text'}),('parameter',999)]:
            self.assertEqual(self.client.post('/api/lesson/T03/walkthrough/progress',json={**row,field:value}).status_code,400)
        self.assertEqual(self.get()['progress'],row)

    def test_authenticated_routes_and_exports(self):
        fresh=baseline.TestClient(baseline.server.app,base_url='http://127.0.0.1')
        self.assertEqual(fresh.get('/api/lesson/T03/walkthrough').status_code,403)
        archive=self.client.get('/api/lesson/T03/walkthrough/export/130');archive.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(archive.content)) as pack:
            self.assertEqual(set(pack.namelist()),{'input.npy','input.png','context.json','params.json','README.md','practice.py','reference.py'})
            self.assertNotIn('learning.',pack.read('practice.py').decode())
            self.assertNotIn('cv2.threshold(',pack.read('practice.py').decode())

if __name__=='__main__':unittest.main(verbosity=2)
