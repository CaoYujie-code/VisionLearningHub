"""Candidate selection must honor raster rules, original indices and no-solution branches."""
import copy,io,json,os,subprocess,sys,tempfile,unittest,zipfile
from pathlib import Path
import test_platform as baseline
import cv2
import numpy as np
from learning import walkthrough as w
from learning.curriculum import BY_ID
from learning.engine import layout_metrics,check_result
from test_visual_expansion import execute

def run(params,image=None):
    scope=dict(np=np,cv2=cv2,image=np.full((200,220,3),245,np.uint8) if image is None else image,params=params)
    for step in w.definition('T10')['steps']:exec(step['code'],scope)
    return scope

class CandidateChecks(unittest.TestCase):
    def test_previous_41_revisions_and_new_coverage(self):
        old=json.loads((Path(__file__).parent/'data/visual-v0170-revisions.json').read_text())
        self.assertEqual(len(old),41)
        for key,value in old.items():self.assertEqual(w.revision(key),value)
        self.assertEqual(len(w.CATALOG),42)
        self.assertEqual(sum(len(v['steps']) for v in w.CATALOG.values()),124)
        self.assertEqual(sum(len(v['control']['values']) for v in w.CATALOG.values()),129)

    def test_four_scenes_match_formal_dependency_contract(self):
        t09={};exec(BY_ID['T09']['reference'],t09)
        for case,selected in [(0,2),(1,0),(2,-1),(3,1)]:
            image,params,scope=execute('T10',case)
            self.assertEqual(scope['selected'],selected)
            self.assertEqual(scope['selection'].tolist(),[[selected,[1,1,0,2][case]]])
            for i,layout in enumerate(params['candidates']):
                ref=t09['solve'](image,{**params,'layout':layout})
                self.assertEqual(scope['scores'][i].tolist(),[i,ref['coverage'],ref['overlap']])
            calls=[]
            def student(key,img,child):
                self.assertEqual(key,'T09');self.assertIsNot(child,params);calls.append(child['layout'])
                return t09['solve'](img,child)
            formal={'student':student};exec(BY_ID['T10']['reference'],formal)
            before=copy.deepcopy(params);self.assertEqual(formal['solve'](image,params),selected);self.assertEqual(params,before)
            self.assertEqual(len(calls),len(params['candidates']) if selected<0 else selected+1)
            self.assertTrue(all(row['ok'] for row in check_result('T10',image,params,{},scope['selected'])))

    def test_outside_overlap_is_not_discarded_by_target_crop(self):
        _,params,s=execute('T10',0)
        np.testing.assert_allclose(s['scores'],[[0,.9,0],[1,1,.1],[2,1,0],[3,1,.1]])
        np.testing.assert_array_equal(s['checks'],[[0,0,1,0],[1,1,0,0],[2,1,1,1],[3,1,0,0]])
        x,y,width,height=params['target'];c=s['candidate_counts'][3]
        self.assertEqual(np.count_nonzero(c[y:y+height,x:x+width]>1),0)
        self.assertEqual(np.count_nonzero(c>1),1000)

    def test_inclusive_thresholds_and_nearby_rejections(self):
        _,params,_=execute('T10',0)
        left,right=params['candidates'][2]
        params['candidates']=[[left,(np.asarray(right)-[2,0]).tolist()]]
        s=run(params);np.testing.assert_allclose(s['scores'],[[0,.98,.02]]);self.assertEqual(s['selected'],0)
        s['scores']=np.asarray([[0,.98,.02],[1,.979999,0],[2,1,.020001],[3,1,0]],float)
        for step in w.definition('T10')['steps'][2:4]:exec(step['code'],s)
        self.assertEqual(s['valid_indices'],[0,3]);self.assertEqual(s['selection'].tolist(),[[0,2]])

    def test_empty_candidates_empty_layout_and_no_solution_do_not_index_last(self):
        for candidates in [[],[[]]]:
            s=run(dict(target=[40,40,100,100],candidates=candidates))
            self.assertEqual(s['scores'].shape,(len(candidates),3));self.assertEqual(s['checks'].shape,(len(candidates),4))
            self.assertEqual(s['selected'],-1);self.assertNotIn('chosen',s)
            self.assertEqual(s['selection'].tolist(),[[-1,0]])
            self.assertFalse(np.any(np.all(s['output']==[220,170,70],axis=2)))
        _,_,s=execute('T10',2)
        self.assertEqual(s['selected'],-1);self.assertNotIn('chosen',s)
        self.assertFalse(np.any(np.all(s['output']==[70,70,225],axis=2)))

    def test_multiple_valid_candidates_keep_original_indices(self):
        image,params,_=execute('T10',0)
        gap,overlap,valid,outer=params['candidates']
        for candidates,indices in [([gap,valid,outer,valid],[1,3]),([valid,gap,valid,outer],[0,2])]:
            s=run({**params,'candidates':candidates},image)
            self.assertEqual(s['valid_indices'],indices);self.assertEqual(s['selected'],indices[0])
            for i in indices:self.assertTrue(all(row['ok'] for row in check_result('T10',image,{**params,'candidates':candidates},{},i)))

    def test_wide_counts_rounding_and_formal_evaluator_agree(self):
        image,params,_=execute('T10',0);left=params['candidates'][2][0]
        params['candidates']=[[left]*300,[(np.asarray(left)+[.6,.4]).tolist()]]
        s=run(params,image)
        self.assertEqual(s['candidate_counts'][0].dtype,np.int32);self.assertEqual(s['candidate_counts'][0].max(),300)
        for i,layout in enumerate(params['candidates']):
            expected=layout_metrics(image,layout,params['target'])
            self.assertEqual(s['scores'][i].tolist(),[i,expected['coverage'],expected['overlap']])

    def test_portable_scripts_import_all_four_scenes_without_grades(self):
        client=baseline.TestClient(baseline.server.app,base_url='http://127.0.0.1');client.headers['X-VLH-Token']=baseline.server.TOKEN
        before=client.get('/api/bootstrap').json()['passed']
        for case in (0,1,2,3):
            with tempfile.TemporaryDirectory() as folder:
                root=Path(folder);files=w.bundle(baseline.server.ROOT,'T10',case)
                for name,data in files.items():(root/name).write_bytes(data)
                self.assertNotIn('student(',files['reference.py'].decode());self.assertNotIn('learning.',files['reference.py'].decode())
                process=subprocess.run([sys.executable,str(root/'reference.py')],capture_output=True,env={**os.environ,'PYTHONUTF8':'1'},timeout=20)
                self.assertEqual(process.returncode,0,process.stderr.decode())
                result=client.post('/api/lesson/T10/walkthrough/import',files={'file':('results.zip',(root/'results.zip').read_bytes(),'application/zip')});result.raise_for_status()
                own=result.json();self.assertEqual(len(own['results']),5)
                for frame in own['results'].values():self.assertTrue(frame['difference']['available']);self.assertEqual(frame['difference']['different'],0)
                self.assertEqual(own['results']['step4']['cells'],[[[2,0,-1,1][case],[1,1,0,2][case]]])
        self.assertEqual(client.get('/api/bootstrap').json()['passed'],before)

if __name__=='__main__':unittest.main(verbosity=2)
