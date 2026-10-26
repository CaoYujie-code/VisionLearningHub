"""Independent checkpoints, honest progress, migration, and reference-free learner projects."""
import json
import tempfile
import unittest
import zipfile
import io
import subprocess
import sys
from pathlib import Path
import test_platform as baseline
from learning.project_catalog import PROJECT_IDS,source_bundle
from learning.project_runner import execute,serialize,materialize
from learning.project_guides import guide,checkpoint_source
from learning.storage import Store
from backend.workspace import Workspace

class GuideChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        baseline.PlatformChecks.setUpClass.__func__(cls)
        baseline.server.TIMEOUT=12
    wait_job=baseline.PlatformChecks.wait_job

    def run_block(self,key,files,block,source='own'):
        response=self.client.post('/api/jobs',json=dict(lesson=key,code=serialize(files),note='guide-test',verify=block=='accept',project_block=block,block_source=source))
        self.assertEqual(response.status_code,200,response.text)
        job=self.wait_job(response.json()['id']);self.assertEqual(job['status'],'done',job)
        return job['result']

    def test_01_all_checkpoint_references(self):
        for key in sorted(PROJECT_IDS):
            self.assertEqual(len(guide(key)['blocks']),5)
            for block,source in [('io','own'),('detect','own'),('render','standard'),('render','own'),('batch','own'),('accept','own')]:
                with tempfile.TemporaryDirectory() as folder:
                    result=execute(dict(lesson=key,codes={key:serialize(source_bundle(key,True))},verify=block=='accept',project_block=block,block_source=source,folder=folder))
                    self.assertTrue(result['passed'],(key,block,source,result))
                    self.assertEqual(result['verify'],block=='accept')

    def test_02_partial_code_and_standard_input_do_not_claim_completion(self):
        files=source_bundle('E05')
        reference=source_bundle('E05',True)
        files.update({'imaging.py':reference['imaging.py'],'checkpoint.py':reference['checkpoint.py']})
        # The unimplemented pipeline must not prevent independent input or rendering work.
        for block,source in [('io','own'),('render','standard')]:
            result=self.run_block('E05',files,block,source);self.assertTrue(result['passed'],result)
        result=self.run_block('E05',files,'render','own');self.assertFalse(result['passed'])
        self.assertFalse(self.client.get('/api/bootstrap').json()['passed']['E05'])
        state=self.client.get('/api/projects/E05').json()['block_progress']
        self.assertEqual(state['render:standard']['state'],'passed')
        self.assertEqual(state['render:own']['state'],'failed')
        files['imaging.py']+='\n# changed\n'
        self.client.put('/api/lesson/E05',json=dict(code=serialize(files),note='')).raise_for_status()
        self.assertEqual(self.client.get('/api/projects/E05').json()['block_progress']['io:own']['state'],'stale')

    def test_03_bad_checkpoint_deliverables_rejected(self):
        files=source_bundle('E01',True)
        for body in ["(output_dir/'results.json').write_text('{\"records\": []}')",'return']:
            files['checkpoint.py']='def run_checkpoint(block,input_dir,output_dir,config):\n    '+body+'\n'+__import__('learning.project_guides',fromlist=['CLI']).CLI
            for block in ('io','detect','render'):
                result=self.run_block('E01',files,block,'standard' if block=='render' else 'own')
                self.assertFalse(result['passed'],block)

    def test_04_upgrade_is_opt_in_and_native_sources_are_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            store=Store(Path(folder)/'data');workspace=Workspace(Path(folder)/'workspace')
            files=source_bundle('E01',True);files.pop('checkpoint.py');files['pipeline.py']+='\n# learner-owned\n'
            code=serialize(files);note=json.dumps(dict(projectNote=1,text='旧笔记',completed=[0,2]))
            store.save('E01',code,note);workspace.initialize(store)
            self.assertEqual(serialize(files),store.draft('E01')[0]);self.assertFalse((workspace.file('E01').parent/'checkpoint.py').exists())
            store.close()
        self.client.put('/api/lesson/E01',json=dict(code=code,note=note)).raise_for_status()
        result=self.client.post('/api/projects/E01/guide').json()
        self.assertEqual(result['note'],note)
        self.assertEqual(result['files']['pipeline.py'],files['pipeline.py'])
        self.assertIn('checkpoint.py',result['files'])
        again=self.client.post('/api/projects/E01/guide').json();self.assertEqual(again['files'],result['files'])

    def test_05_request_boundaries(self):
        body=dict(lesson='E01',code=serialize(source_bundle('E01')),verify=False,project_block='io')
        for patch in [dict(project_block='../escape'),dict(project_block='accept'),dict(verify=True),dict(block_source='standard'),dict(lesson='P01'),dict(upload_id='0'*32),dict(block_source='anything')]:
            response=self.client.post('/api/jobs',json={**body,**patch});self.assertEqual(response.status_code,400,response.text)
        self.assertEqual(self.client.post('/api/projects/E99/guide').status_code,404)
        self.assertEqual(self.client.post('/api/projects/E01/guide',headers={'X-VLH-Token':''}).status_code,403)

    def test_06_exported_checkpoint_cli_with_standard_data(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);materialize('E08',root,source_bundle('E08',True),include_holdout=True)
            self.assertTrue((root/'GUIDED_LEARNING.md').is_file())
            for block,input_dir in [('io','data/sample'),('detect','data/sample'),('render','data/standard')]:
                run=subprocess.run([sys.executable,'checkpoint.py','--block',block,'--input',input_dir,'--output','output-'+block],cwd=root,capture_output=True,text=True,encoding='utf-8',timeout=15)
                self.assertEqual(run.returncode,0,run.stderr)
                self.assertTrue((root/('output-'+block)/'results.json').is_file())

    def test_07_progress_and_notes_backup_restore(self):
        files=source_bundle('E06',True);result=self.run_block('E06',files,'detect');self.assertTrue(result['passed'])
        note=json.dumps(dict(projectNote=2,text='测量误差',completed=[0],mode='guided',block='detect',source='own',hints={'detect':1}))
        self.client.put('/api/lesson/E06',json=dict(code=serialize(files),note=note)).raise_for_status()
        backup=self.client.get('/api/backup');backup.raise_for_status()
        self.client.put('/api/lesson/E06',json=dict(code=serialize(source_bundle('E06')),note='')).raise_for_status()
        response=self.client.post('/api/restore',files={'file':('backup.zip',backup.content,'application/zip')});response.raise_for_status()
        project=self.client.get('/api/projects/E06').json();self.assertEqual(project['note'],note)
        self.assertEqual(project['block_progress']['detect:own']['state'],'passed')
        self.assertFalse(self.client.get('/api/bootstrap').json()['passed']['E06'])

if __name__=='__main__':unittest.main(verbosity=2)
