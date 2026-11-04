"""Personal plans persist independently, survive backup and reject invalid writes."""
import io,json,sqlite3,tempfile,unittest,zipfile
from pathlib import Path
import test_platform as baseline
from learning.study_plan import SETTING,read_plan,save_plan,validate_plan
from learning.study_desk import snapshot,notebook
from learning.storage import Store

class StudyPlanChecks(unittest.TestCase):
    def setUp(self):
        self.client=baseline.TestClient(baseline.server.app,base_url='http://127.0.0.1');self.client.headers['X-VLH-Token']=baseline.server.TOKEN
        with baseline.server.LOCK,baseline.server.database() as store:
            store.connection.execute('DELETE FROM settings WHERE key=?',(SETTING,));store.connection.commit()
    def save(self,key='A06',status='next',note='先复习撤销状态'):
        return self.client.post('/api/study-plan/'+key,json=dict(status=status,note=note))
    def row(self,key='A06'):
        return next(r for r in self.client.get('/api/study-desk').json()['rows'] if r['id']==key)
    def test_planned_unstarted_exercise_has_independent_state(self):
        before=self.client.get('/api/bootstrap').json();draft=self.client.get('/api/lesson/A06').json()
        self.save().raise_for_status();self.assertEqual(self.row()['plan'],dict(status='next',note='先复习撤销状态'))
        after=self.client.get('/api/bootstrap').json();self.assertEqual(before['passed'],after['passed']);self.assertEqual(before['attempts'],after['attempts'])
        current=self.client.get('/api/lesson/A06').json();self.assertEqual(draft['code'],current['code']);self.assertEqual(draft['note'],current['note'])
    def test_all_statuses_update_only_selected_lesson_and_clear_is_idempotent(self):
        self.save('T03','stuck','光照不均').raise_for_status()
        for status in ('next','stuck','review'):
            self.save(status=status).raise_for_status();self.assertEqual(self.row()['plan']['status'],status)
            self.assertEqual(self.row('T03')['plan'],dict(status='stuck',note='光照不均'))
        for _ in range(2):self.save(status='none',note='').raise_for_status()
        self.assertEqual(self.row()['plan'],dict(status='none',note=''));self.assertEqual(self.row('T03')['plan']['status'],'stuck')
    def test_invalid_payloads_are_rejected_without_overwriting_record(self):
        self.save().raise_for_status();before=self.row()['plan']
        for value in [{},{'status':'done','note':''},{'status':True,'note':''},{'status':[],'note':''},{'status':'next','note':None},{'status':'next','note':'x'*1001},{'status':'next','note':'','passed':True},{'status':'none','note':'不能隐式丢掉'}]:
            response=self.client.post('/api/study-plan/A06',json=value);self.assertEqual(response.status_code,400,value)
        for key in ('E01','Z99'):self.assertEqual(self.save(key).status_code,400)
        self.assertEqual(self.row()['plan'],before)
        self.save(note='字'*1000).raise_for_status();self.assertEqual(len(self.row()['plan']['note']),1000)
    def test_authenticated_route_and_new_client_read_persistent_state(self):
        fresh=baseline.TestClient(baseline.server.app,base_url='http://127.0.0.1')
        self.assertEqual(fresh.post('/api/study-plan/A06',json=dict(status='next',note='')).status_code,403)
        self.save(status='review').raise_for_status();fresh.headers['X-VLH-Token']=baseline.server.TOKEN
        self.assertEqual(next(r for r in fresh.get('/api/study-desk').json()['rows'] if r['id']=='A06')['plan']['status'],'review')
    def test_verified_exercise_retains_manual_review_and_exports_unstarted_plan(self):
        with tempfile.TemporaryDirectory() as directory:
            store=Store(directory)
            try:
                save_plan(store,'A06',dict(status='review',note='```\n复习再独立实现\n````'))
                data=snapshot(Path(directory),store,{'A06':True});row=next(r for r in data['rows'] if r['id']=='A06')
                self.assertTrue(row['verified']);self.assertFalse(row['started']);self.assertEqual(row['plan']['status'],'review')
                text=notebook(data);self.assertIn('个人安排：待复习',text);self.assertIn('`````text',text);self.assertIn('当前代码：已验收',text)
                unverified=notebook(snapshot(Path(directory),store,{}));self.assertIn('复习再独立实现',unverified)
                self.assertEqual(read_plan(store)['A06']['status'],'review')
            finally:store.connection.close()
    def test_backup_restore_and_clear_scopes(self):
        self.save(status='stuck',note='看不懂递归返回').raise_for_status();before=self.row()['plan'];raw=self.client.get('/api/backup').content
        for scope in ('cache','history'):
            self.client.post('/api/clear',json=dict(scope=scope,confirmation='CLEAR')).raise_for_status();self.assertEqual(self.row()['plan'],before)
        self.client.post('/api/clear',json=dict(scope='all',confirmation='CLEAR')).raise_for_status();self.assertEqual(self.row()['plan']['status'],'none')
        self.client.post('/api/restore',files={'file':('backup.zip',raw,'application/zip')}).raise_for_status();self.assertEqual(self.row()['plan'],before)
    def test_invalid_plan_backup_rejected_atomically(self):
        self.save().raise_for_status();before=self.row()['plan'];raw=self.client.get('/api/backup').content
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'learning.sqlite3'
            with zipfile.ZipFile(io.BytesIO(raw)) as pack:p.write_bytes(pack.read('learning.sqlite3'))
            db=sqlite3.connect(p);db.execute('UPDATE settings SET value=? WHERE key=?',(json.dumps({'E01':{'status':'next','note':''}}),SETTING));db.commit();db.close()
            bad=io.BytesIO()
            with zipfile.ZipFile(bad,'w') as pack:pack.write(p,'learning.sqlite3')
            response=self.client.post('/api/restore',files={'file':('bad.zip',bad.getvalue(),'application/zip')});self.assertEqual(response.status_code,400)
        self.assertEqual(self.row()['plan'],before)
    def test_older_backup_without_plans_is_accepted(self):
        backup=self.client.get('/api/backup').content;self.save().raise_for_status()
        self.client.post('/api/restore',files={'file':('old.zip',backup,'application/zip')}).raise_for_status();self.assertEqual(self.row()['plan']['status'],'none')
        for data in ([],{'A06':{'status':'none','note':''}},{'A06':{'status':'next','note':1}}):
            with self.assertRaises(ValueError):validate_plan(data)

if __name__=='__main__':unittest.main(verbosity=2)
