"""Understanding checks persist separately and never grant code completion."""
import copy
import hashlib
import io
import sqlite3
import tempfile
import zipfile
from pathlib import Path
import json
import unittest
from unittest.mock import patch
import test_platform as baseline
from learning.function_handbook import CARDS
from learning.function_review import SETTING

class FunctionReviewChecks(unittest.TestCase):
    def setUp(self):
        self.client=baseline.TestClient(baseline.server.app,base_url='http://127.0.0.1')
        self.client.headers['X-VLH-Token']=baseline.server.TOKEN
        with baseline.server.LOCK,baseline.server.database() as store:
            store.connection.execute('DELETE FROM settings WHERE key=?',(SETTING,));store.connection.commit()

    def submit(self,key='threshold',choice=None,revision=None):
        quiz=CARDS[key]['quiz']
        return self.client.post('/api/function-review',json=dict(card=key,choice=quiz['answer'] if choice is None else choice,revision=revision or quiz['revision']))

    def test_content_and_revision_identity(self):
        positions=set()
        for card in CARDS.values():
            q=card['quiz'];positions.add(q['answer'])
            self.assertEqual(len(q['options']),3)
            self.assertEqual(len({v['text'] for v in q['options']}),3)
            self.assertTrue(all(v['explanation'] for v in q['options']))
            self.assertIn(q['answer'],range(3))
            data={k:v for k,v in q.items() if k!='revision'}
            self.assertEqual(q['revision'],hashlib.sha256(json.dumps(data,ensure_ascii=False,sort_keys=True).encode()).hexdigest()[:16])
        self.assertEqual(positions,{0,1,2})
        self.assertEqual(CARDS['threshold']['quiz']['options'][CARDS['threshold']['quiz']['answer']]['text'],'0')
        self.assertEqual(CARDS['iou']['quiz']['options'][CARDS['iou']['quiz']['answer']]['text'],'0')

    def test_answer_feedback_is_separate_from_grades_and_validated(self):
        before=self.client.get('/api/bootstrap').json()['passed']
        draft=self.client.get('/api/lesson/T03').json()
        wrong=(CARDS['threshold']['quiz']['answer']+1)%3
        first=self.submit(choice=wrong);self.assertEqual(first.status_code,200)
        self.assertEqual(first.json()['review'],1)
        self.assertFalse(first.json()['records']['threshold']['correct'])
        second=self.submit().json();record=second['records']['threshold']
        self.assertEqual((record['attempts'],record['wrong_attempts']),(2,1))
        self.assertEqual((second['review'],second['correct']),(0,1))
        self.assertEqual(self.client.get('/api/bootstrap').json()['passed'],before)
        after=self.client.get('/api/lesson/T03').json()
        self.assertEqual((after['code'],after['note'],after['history']),(draft['code'],draft['note'],draft['history']))
        for value in (True,-1,3,1.5,'1',None):
            response=self.client.post('/api/function-review',json=dict(card='threshold',choice=value,revision=CARDS['threshold']['quiz']['revision']))
            self.assertEqual(response.status_code,422,(value,response.text))
        self.assertEqual(self.client.post('/api/function-review',json=dict(card='../bad',choice=0,revision='a'*16)).status_code,400)
        self.assertEqual(self.client.get('/api/function-review').json()['records']['threshold']['attempts'],2)

    def test_backup_restore_and_clear_scopes(self):
        self.submit().raise_for_status()
        backup=self.client.get('/api/backup');backup.raise_for_status()
        for scope in ('cache','history'):
            self.client.post('/api/clear',json=dict(scope=scope,confirmation='CLEAR')).raise_for_status()
            self.assertEqual(self.client.get('/api/function-review').json()['correct'],1)
        self.client.post('/api/clear',json=dict(scope='all',confirmation='CLEAR')).raise_for_status()
        self.assertEqual(self.client.get('/api/function-review').json()['records'],{})
        self.client.post('/api/restore',files={'file':('learning.zip',backup.content,'application/zip')}).raise_for_status()
        self.assertEqual(self.client.get('/api/function-review').json()['correct'],1)
        fresh=baseline.TestClient(baseline.server.app,base_url='http://127.0.0.1');fresh.headers['X-VLH-Token']=baseline.server.TOKEN
        self.assertEqual(fresh.get('/api/function-review').json()['records']['threshold']['attempts'],1)

    def test_invalid_backup_is_rejected_without_losing_current_record(self):
        self.submit().raise_for_status()
        saved=self.client.get('/api/function-review').json()
        backup=self.client.get('/api/backup').content
        with tempfile.TemporaryDirectory() as folder:
            db=Path(folder)/'learning.sqlite3'
            with zipfile.ZipFile(io.BytesIO(backup)) as archive:db.write_bytes(archive.read('learning.sqlite3'))
            connection=sqlite3.connect(db)
            raw=json.loads(connection.execute('SELECT value FROM settings WHERE key=?',(SETTING,)).fetchone()[0])
            raw['threshold']['choice']=True
            connection.execute('UPDATE settings SET value=? WHERE key=?',(json.dumps(raw),SETTING));connection.commit();connection.close()
            altered=io.BytesIO()
            with zipfile.ZipFile(altered,'w') as archive:archive.write(db,'learning.sqlite3')
            response=self.client.post('/api/restore',files={'file':('invalid.zip',altered.getvalue(),'application/zip')})
            self.assertEqual(response.status_code,400)
        self.assertEqual(self.client.get('/api/function-review').json(),saved)

    def test_changed_question_requires_fresh_answer_and_bad_records_are_ignored(self):
        self.submit().raise_for_status()
        old=CARDS['threshold'];changed=copy.deepcopy(old);changed['quiz']['revision']='b'*16
        with patch.dict(CARDS,{'threshold':changed}):
            state=self.client.get('/api/function-review').json()
            self.assertEqual((state['answered'],state['correct'],state['review']),(0,0,1))
            self.assertTrue(state['records']['threshold']['stale'])
            self.assertEqual(self.submit(revision=old['quiz']['revision']).status_code,409)
            self.assertEqual(self.submit().json()['records']['threshold']['attempts'],1)
        with baseline.server.LOCK,baseline.server.database() as store:
            store.set_setting(SETTING,json.dumps({'unknown':{},'threshold':{'choice':True},'color':{'choice':0,'attempts':-1,'wrong_attempts':0}}))
        self.assertEqual(self.client.get('/api/function-review').json()['records'],{})

if __name__=='__main__':unittest.main(verbosity=2)
