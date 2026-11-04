"""Exercise real search branches, undo invariants and native portable results."""
import copy,json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
import test_platform as baseline
import cv2
import numpy as np
from learning import walkthrough as w
from learning.curriculum import BY_ID
from learning.extra_engine import check_result, _normalize
from test_visual_expansion import execute

def search_input(board,pieces):
    params=dict(board=board,pieces=pieces)
    scope=dict(cv2=cv2,np=np,params=params,image=np.zeros((2,2,3),np.uint8))
    for step in w.definition('A06')['steps'][:4]:exec(step['code'],scope)
    return scope

class BacktrackingChecks(unittest.TestCase):
    def test_previous_43_revisions_and_complete_basic_coverage(self):
        old=json.loads((Path(__file__).parent/'data/visual-v0190-revisions.json').read_text())
        self.assertEqual(len(old),43)
        for key,value in old.items():self.assertEqual(w.revision(key),value)
        self.assertEqual(len(w.CATALOG),44)
        self.assertEqual(sum(len(v['steps']) for v in w.CATALOG.values()),137)
        self.assertEqual(sum(len(v['control']['values']) for v in w.CATALOG.values()),137)

    def test_four_scenes_match_formal_contract_without_changing_input(self):
        ref={};exec(BY_ID['A06']['reference'],ref)
        for case in range(4):
            image,params,s=execute('A06',case);before=copy.deepcopy(params)
            self.assertEqual(s['result'],ref['solve'](image,params));self.assertEqual(params,before)
            checks=check_result('A06',image,params,{'solvable':case in (0,3)},s['result'])
            self.assertTrue(checks);self.assertTrue(all(c['ok'] for c in checks),checks)
            self.assertEqual(s['remaining'],{(r,c) for r,row in enumerate(params['board']) for c,v in enumerate(row) if v==1})

    def test_actual_undo_restores_board_path_and_used_piece(self):
        _,_,s=execute('A06',0)
        self.assertEqual(s['trace'][:,0].tolist(),[1,2,3,1,1,4])
        self.assertEqual(s['events'][2],[3,0,0,6,0]);np.testing.assert_array_equal(s['frames'][2],np.zeros((2,3)))
        np.testing.assert_array_equal(s['frames'][0],[[1,1,0],[0,0,0]])
        np.testing.assert_array_equal(s['frames'][3],[[1,0,0],[1,0,0]])
        self.assertEqual(s['path'],s['result']);self.assertEqual(s['used'],{0,1})
        for event,frame in zip(s['events'],s['frames']):
            self.assertEqual(event[3],np.count_nonzero(frame==0))
            self.assertEqual(event[4],len(set(frame[frame>0].tolist())))
        self.assertFalse(np.shares_memory(s['frames'][0],s['frames'][-1]))

    def test_equal_area_failure_exhausts_branches_and_restores_everything(self):
        _,_,s=execute('A06',1)
        self.assertTrue(s['area_ok']);self.assertIsNone(s['result']);self.assertEqual(s['used'],set());self.assertEqual(s['path'],[])
        self.assertEqual(s['trace'][:,0].tolist(),[1,2,3,1,2,3,2])
        initial=np.where(s['board']==1,0,-1)
        for i in [2,5,6]:np.testing.assert_array_equal(s['frames'][i],initial)
        self.assertEqual([e[2] for e in s['events'] if e[0]==1],[0,1])

    def test_area_rejection_and_empty_success_are_distinct(self):
        _,_,bad=execute('A06',2);_,_,empty=execute('A06',3)
        self.assertFalse(bad['area_ok']);self.assertEqual(bad['events'],[[5,0,-1,6,0]]);self.assertIsNone(bad['result'])
        self.assertTrue(empty['area_ok']);self.assertEqual(empty['events'],[[4,0,-1,0,0]]);self.assertEqual(empty['result'],[])
        self.assertIsNotNone(empty['result']);self.assertEqual(empty['rotation_table'].shape,(0,3));self.assertEqual(empty['candidates'].shape,(0,5))
        self.assertTrue(np.all(empty['final_board']==-1));self.assertIn('合法空解 []',empty['detail'])

    def test_rotations_do_not_allow_mirrors_and_anchor_alignment_is_complete(self):
        _,_,s=execute('A06',0);self.assertEqual([len(v) for v in s['variants']],[2,1])
        piece=[[0,0],[1,0],[2,0],[2,1]]
        custom=search_input([[1,0],[1,0],[1,1]],[piece]);self.assertIsNotNone(custom['result'])
        self.assertNotIn(_normalize([(r,-c) for r,c in piece]),custom['variants'][0])
        l_shape=search_input([[0,1],[1,1]],[[[0,0],[1,0],[1,1]]])
        self.assertIsNotNone(l_shape['result'])
        self.assertTrue(any(row[4] and (row[2] or row[3]) for row in l_shape['candidates']))

    def test_alternative_valid_layout_is_accepted_by_formal_checker(self):
        image,params,s=execute('A06',0)
        alternative=[{'piece':0,'cells':[[0,2],[1,2]]},{'piece':1,'cells':[[0,0],[0,1],[1,0],[1,1]]}]
        self.assertNotEqual(alternative,s['result'])
        self.assertTrue(all(c['ok'] for c in check_result('A06',image,params,{'solvable':True},alternative)))
        broken=copy.deepcopy(alternative);broken[1]['cells'][0]=[0,2]
        self.assertFalse(all(c['ok'] for c in check_result('A06',image,params,{'solvable':True},broken)))

    def test_portable_execution_and_import_all_scenes_preserve_grades(self):
        client=baseline.TestClient(baseline.server.app,base_url='http://127.0.0.1');client.headers['X-VLH-Token']=baseline.server.TOKEN
        before=client.get('/api/bootstrap').json()['passed']
        for case,count in enumerate([6,7,1,1]):
            with tempfile.TemporaryDirectory() as folder:
                root=Path(folder);files=w.bundle(baseline.server.ROOT,'A06',case)
                for name,data in files.items():(root/name).write_bytes(data)
                self.assertNotIn('student(',files['reference.py'].decode());self.assertNotIn('learning.',files['reference.py'].decode())
                result=subprocess.run([sys.executable,str(root/'reference.py')],capture_output=True,env={**os.environ,'PYTHONUTF8':'1'},timeout=20)
                self.assertEqual(result.returncode,0,result.stderr.decode())
                response=client.post('/api/lesson/A06/walkthrough/import',files={'file':('results.zip',(root/'results.zip').read_bytes(),'application/zip')});response.raise_for_status();own=response.json()
                self.assertEqual(len(own['results']),6);self.assertEqual(own['results']['step4']['shape'],[count,5])
                for frame in own['results'].values():self.assertTrue(frame['difference']['available']);self.assertEqual(frame['difference']['different'],0)
        self.assertEqual(client.get('/api/bootstrap').json()['passed'],before)

if __name__=='__main__':unittest.main(verbosity=2)
