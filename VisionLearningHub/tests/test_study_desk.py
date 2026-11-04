"""Study summaries must remain read-only and separate self checks from grades."""
import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import test_platform as baseline
from learning.storage import Store
from learning import walkthrough as w
from learning.study_desk import snapshot,notebook

class StudyDeskChecks(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.store=Store(self.root)
    def tearDown(self):
        self.store.connection.close();self.temp.cleanup()
    def row(self,key='A06',passed=None):
        return next(r for r in snapshot(self.root,self.store,passed or {})['rows'] if r['id']==key)
    def save(self,key='A06',**changes):
        state=w.state(self.store,key);state.update(changes);w.save_state(self.store,key,state);return state
    def own(self,**changes):
        data=dict(revision=w.revision('A06'),parameter=0,results={s['id']:{'difference':{'available':True,'different':0}} for s in w.definition('A06')['steps']});data.update(changes)
        p=self.root/'runs/walkthrough/A06/latest.json';p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(data),encoding='utf-8');return p
    def test_empty_snapshot_is_read_only_and_does_not_execute_course(self):
        before=list(self.store.connection.execute('SELECT * FROM settings'))
        with patch.object(w,'demonstration',side_effect=AssertionError('must not execute')):data=snapshot(self.root,self.store,{})
        self.assertEqual(data['counts'],dict(total=44,started=0,verified=0,notes=0,attention=0));self.assertEqual(len(data['rows']),44)
        self.assertEqual(list(self.store.connection.execute('SELECT * FROM settings')),before);self.assertFalse((self.root/'previews').exists())
    def test_notes_position_and_self_checks_never_award_grades(self):
        state=self.save(step=3,done=[0,1,2,3,4,5],notes={'step4':'撤销恢复状态','step2':'  '},parameter=1)
        row=self.row();self.assertTrue(row['started']);self.assertEqual(row['done'],6);self.assertFalse(row['verified']);self.assertEqual(row['step'],3);self.assertEqual(row['parameter'],1)
        self.assertEqual(len(row['notes']),1);self.assertEqual(row['notes'][0]['step'],3);self.assertEqual(w.state(self.store,'A06'),state)
    def test_import_summary_classifies_missing_different_and_unknown(self):
        self.own();self.assertEqual(self.row()['result']['status'],'same');self.assertFalse(self.row()['verified'])
        self.own(results={'step1':{'difference':{'available':True,'different':1}},'step2':{'difference':{'available':False}},'step3':{}})
        self.assertEqual(self.row()['result'],dict(status='check',saved=3,missing=3,different=1,unknown=2));self.assertTrue(self.row()['attention'])
        self.own(results={});self.assertEqual(self.row()['result']['missing'],6)
    def test_old_versions_parameter_mismatch_and_corrupt_file_are_explicit(self):
        state=self.save(step=4,done=[1],notes={'step1':'旧笔记'});state['revision']='0'*16;self.store.set_setting(w.SETTING,json.dumps({'A06':state}))
        self.assertTrue(self.row()['changed']);self.assertEqual(self.row()['step'],0);self.assertEqual(self.row()['notes'],[])
        self.own(revision='0'*16);self.assertEqual(self.row()['result']['status'],'stale')
        self.own(parameter=1);self.assertEqual(self.row()['result']['status'],'parameter')
        p=self.own();p.write_text('{bad',encoding='utf-8');self.assertEqual(self.row()['result']['status'],'unreadable')
    def test_formal_status_follows_current_grade_map_only(self):
        self.assertTrue(self.row(passed={'A06':True})['verified']);self.assertFalse(self.row(passed={'A06':False})['verified'])
        self.save(done=list(range(6)));self.own();self.assertFalse(self.row()['verified'])
    def test_export_preserves_notes_and_fences_without_mutating_records(self):
        text='第一行\n```python\n<script>alert(1)</script>\n````\n原样保留'
        self.save(notes={'step4':text});data=snapshot(self.root,self.store,{})
        export=notebook(data);self.assertIn(text,export);self.assertIn('`````text',export);self.assertIn('当前代码：待验收',export);self.assertIn('第 4 步',export)
        self.assertEqual(self.row()['notes'][0]['text'],text)
    def test_authenticated_api_and_markdown_download_do_not_generate_assets(self):
        client=baseline.TestClient(baseline.server.app,base_url='http://127.0.0.1')
        self.assertEqual(client.get('/api/study-desk').status_code,403);self.assertEqual(client.get('/api/study-desk/export').status_code,403)
        client.headers['X-VLH-Token']=baseline.server.TOKEN
        before=client.get('/api/bootstrap').json()
        with patch.object(w,'demonstration',side_effect=AssertionError('must not execute')):
            data=client.get('/api/study-desk');data.raise_for_status();export=client.get('/api/study-desk/export');export.raise_for_status()
        self.assertEqual(data.json()['counts']['total'],44);self.assertIn('text/markdown',export.headers['content-type']);self.assertIn('vision-study-notes.md',export.headers['content-disposition'])
        after=client.get('/api/bootstrap').json();self.assertEqual(after['settings'],before['settings']);self.assertEqual(after['passed'],before['passed']);self.assertEqual(after['attempts'],before['attempts'])
    def test_backup_clear_restore_reconstructs_summary_from_existing_storage(self):
        client=baseline.TestClient(baseline.server.app,base_url='http://127.0.0.1');client.headers['X-VLH-Token']=baseline.server.TOKEN
        state=client.get('/api/lesson/A06/walkthrough').json()['progress'];state.update(step=3,notes={'step4':'复习撤销'},done=[0])
        client.post('/api/lesson/A06/walkthrough/progress',json=state).raise_for_status()
        before=client.get('/api/study-desk').json();backup=client.get('/api/backup').content
        client.post('/api/clear',json=dict(scope='all',confirmation='CLEAR')).raise_for_status();self.assertEqual(client.get('/api/study-desk').json()['counts']['started'],0)
        client.post('/api/restore',files={'file':('backup.zip',backup,'application/zip')}).raise_for_status();self.assertEqual(client.get('/api/study-desk').json(),before)

if __name__=='__main__':unittest.main(verbosity=2)
