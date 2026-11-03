"""Check the complete detector against native prerequisites and explicit failure scenes."""
import copy,json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
import test_platform as baseline
import cv2
import numpy as np
from learning import walkthrough as w
from learning.curriculum import BY_ID
from test_visual_expansion import execute

class DetectorChecks(unittest.TestCase):
    def test_previous_42_revisions_and_coverage(self):
        old=json.loads((Path(__file__).parent/'data/visual-v0180-revisions.json').read_text())
        self.assertEqual(len(old),42)
        for key,value in old.items():self.assertEqual(w.revision(key),value)
        self.assertEqual(len(w.CATALOG),43)
        self.assertEqual(sum(len(v['steps']) for v in w.CATALOG.values()),131)
        self.assertEqual(sum(len(v['control']['values']) for v in w.CATALOG.values()),133)

    def test_four_scenes_match_formal_dependency_pipeline(self):
        references={}
        for key in ['T04','T05','T06','T07']:
            scope={};exec(BY_ID[key]['reference'],scope);references[key]=scope['solve']
        for case,count in enumerate([3,3,0,1]):
            image,params,s=execute('T14',case);original=image.copy();before=copy.deepcopy(params);calls=[]
            def student(key,data,child):
                calls.append(key)
                if key in ('T05','T06'):self.assertEqual(data.ndim,2)
                if key=='T07':self.assertIsNot(child,params);self.assertIn('contours',child)
                return references[key](data,child)
            scope={'student':student};exec(BY_ID['T14']['reference'],scope);result=scope['solve'](image,params)
            self.assertEqual(calls,['T04','T05','T06','T07']);self.assertEqual(params,before);np.testing.assert_array_equal(image,original)
            np.testing.assert_array_equal(result['mask'],s['result']['mask']);self.assertEqual(len(result['pieces']),count)
            self.assertEqual(len(s['pieces']),count)
            for expected,actual in zip(result['pieces'],s['pieces']):
                self.assertEqual(expected['center'],actual['center']);self.assertEqual(expected['area'],actual['area']);np.testing.assert_array_equal(expected['points'],actual['points'])
            np.testing.assert_array_equal(s['foreground'],255-s['background'])
            for key in ['background','foreground','opened','cleaned']:
                self.assertEqual(s[key].dtype,np.uint8);self.assertEqual(s[key].shape,image.shape[:2]);self.assertTrue(np.isin(s[key],[0,255]).all())

    def test_noise_holes_and_printed_content_have_distinct_roles(self):
        image,_,s=execute('T14',1)
        for x,y in [(15,20),(330,30),(320,245)]:self.assertEqual(s['foreground'][y,x],255);self.assertEqual(s['opened'][y,x],0)
        for x,y in [(80,60),(70,210)]:self.assertEqual(s['foreground'][y,x],0);self.assertEqual(s['cleaned'][y,x],255)
        for bgr in [[15,15,15],[25,30,215]]:
            where=np.all(image==bgr,axis=2);self.assertTrue(where.any());self.assertTrue(np.all(s['foreground'][where]==255))
        self.assertGreater(s['removed'],0);self.assertGreater(s['added'],0)

    def test_close_operation_exposes_real_merge_failure(self):
        _,params,s=execute('T14',3)
        self.assertEqual(params['expected_pieces'],2);self.assertEqual(len(s['joined_before']),2);self.assertEqual(len(s['joined_after']),1)
        self.assertTrue(np.all(s['opened'][100,140:142]==0));self.assertTrue(np.all(s['cleaned'][100,140:142]==255))
        self.assertEqual(len(s['pieces']),1);np.testing.assert_allclose(s['pieces'][0]['center'],[140.5,129.5])

    def test_empty_scene_and_degenerate_contours_never_invent_geometry(self):
        _,_,s=execute('T14',2)
        self.assertGreater(np.count_nonzero(s['foreground']),0);self.assertEqual(np.count_nonzero(s['cleaned']),0)
        self.assertEqual(s['pieces'],[]);self.assertEqual(s['geometry'].shape,(0,5))
        self.assertEqual(set(s['result']),{'mask','pieces'})
        s['contours']=[np.array([[[1,1]],[[2,2]],[[3,3]]],np.int32)]
        exec(w.definition('T14')['steps'][5]['code'],s)
        self.assertEqual(s['pieces'],[]);self.assertEqual(s['geometry'].shape,(0,5))

    def test_geometric_area_boundary_does_not_use_pixel_count(self):
        image,params,s=execute('T14',0);mask=np.zeros(image.shape[:2],np.uint8);mask[10:21,10:21]=255
        self.assertEqual(np.count_nonzero(mask),121)
        s.update(cleaned=mask,params={**params,'min_area':100});exec(w.definition('T14')['steps'][4]['code'],s)
        self.assertEqual(len(s['contours']),1);self.assertEqual(cv2.contourArea(s['contours'][0]),100)
        s['params']['min_area']=101;exec(w.definition('T14')['steps'][4]['code'],s);self.assertEqual(s['contours'],[])

    def test_expected_count_is_explanatory_not_algorithm_input(self):
        for case in (0,3):
            image,params,s=execute('T14',case);changed=dict(cv2=cv2,np=np,image=image.copy(),params={**params,'expected_pieces':999})
            for step in w.definition('T14')['steps']:exec(step['code'],changed)
            for name in ['foreground','opened','cleaned','geometry','output']:np.testing.assert_array_equal(changed[name],s[name])
            self.assertIn('999',changed['detail'])

    def test_portable_execution_all_scenes_imports_real_arrays_without_grades(self):
        client=baseline.TestClient(baseline.server.app,base_url='http://127.0.0.1');client.headers['X-VLH-Token']=baseline.server.TOKEN
        before=client.get('/api/bootstrap').json()['passed']
        for case,count in enumerate([3,3,0,1]):
            with tempfile.TemporaryDirectory() as folder:
                root=Path(folder);files=w.bundle(baseline.server.ROOT,'T14',case)
                for name,data in files.items():(root/name).write_bytes(data)
                self.assertNotIn('student(',files['reference.py'].decode());self.assertNotIn('learning.',files['reference.py'].decode())
                result=subprocess.run([sys.executable,str(root/'reference.py')],capture_output=True,env={**os.environ,'PYTHONUTF8':'1'},timeout=20);self.assertEqual(result.returncode,0,result.stderr.decode())
                response=client.post('/api/lesson/T14/walkthrough/import',files={'file':('results.zip',(root/'results.zip').read_bytes(),'application/zip')});response.raise_for_status();own=response.json()
                self.assertEqual(len(own['results']),7);self.assertEqual(own['results']['step6']['shape'],[count,5])
                for frame in own['results'].values():self.assertTrue(frame['difference']['available']);self.assertEqual(frame['difference']['different'],0)
                if case==2:self.assertIsNone(own['results']['step6']['minimum']);self.assertEqual(own['results']['step4']['nonzero'],0)
        self.assertEqual(client.get('/api/bootstrap').json()['passed'],before)

if __name__=='__main__':unittest.main(verbosity=2)
