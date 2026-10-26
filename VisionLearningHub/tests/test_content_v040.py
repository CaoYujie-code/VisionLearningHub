"""Content graph, independent edge cases, rejection and additive upgrade acceptance."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import test_platform as baseline
import numpy as np
import cv2
from backend.courses import COURSES
from backend.workspace import Workspace, native_code
from learning.curriculum import LESSONS, BY_ID
from learning.advanced_lessons import ADVANCED_IDS
from learning import advanced_engine
from learning.storage import Store


class ContentAcceptance(unittest.TestCase):
    def solve(self,key,image,params):
        scope={};exec(BY_ID[key]['reference'],scope)
        return scope['solve'](image,copy.deepcopy(params))

    def test_01_content_graph_and_resources(self):
        self.assertEqual(len(COURSES),32)
        self.assertEqual(len(LESSONS),52)
        self.assertEqual(len({l['id'] for l in LESSONS}),52)
        catalog=json.loads((baseline.PROJECT/'content/resource_catalog.json').read_text(encoding='utf-8'))['resources']
        resources={r['id']:r for r in catalog}
        self.assertEqual(len(resources),35)
        self.assertEqual(len({r['url'] for r in catalog}),35)
        ordered=[key for course in COURSES for key in course['lessons']]
        self.assertEqual(len(ordered),52)
        self.assertEqual(set(ordered),set(BY_ID))
        for i,key in enumerate(ordered):
            for dep in BY_ID[key]['prerequisites']:
                self.assertLess(ordered.index(dep),i,(key,dep))
        for course in COURSES:
            self.assertTrue(all(r in resources for r in course['resources']))
        for resource in catalog:
            self.assertIn(resource['stage'],{c['id'] for c in COURSES})
            self.assertTrue(resource['url'].startswith('https://'))
        for course in COURSES:
            if int(course['id'][1:])>=16:
                self.assertGreaterEqual(len(course['sections']),3)
                self.assertGreaterEqual(len(course['checks']),3)

    def test_02_graders_reject_wrong_output_and_interface(self):
        with tempfile.TemporaryDirectory() as folder:
            for key in sorted(ADVANCED_IDS):
                image,params,truth=advanced_engine.fixture(key,101,folder)
                result=self.solve(key,image,params)
                self.assertTrue(all(c['ok'] for c in advanced_engine.check_result(key,image,params,truth,result)),key)
                target=truth['result']
                if isinstance(target,np.ndarray):
                    wrong=np.zeros_like(target)
                    invalid=target.astype(np.float64)
                elif key=='V10':wrong=[];invalid={}
                elif key=='V12':wrong={'top_left':[0,0]};invalid=[]
                elif key=='Y04':wrong=['clean'];invalid={}
                elif key=='Y05':wrong={'tp':2,'fp':1,'fn':0};invalid={'tp':True,'fp':2,'fn':1}
                else:wrong={'mean_ms':1,'p95_ms':1,'serial_fps':1000};invalid={'mean_ms':float('nan')}
                for answer in (wrong,invalid):
                    self.assertFalse(all(c['ok'] for c in advanced_engine.check_result(key,image,params,truth,answer)),key)

    def test_03_geometric_and_numeric_boundaries(self):
        mask=np.zeros((4,4),np.uint8);mask[1,1]=mask[2,2]=255
        self.assertEqual(self.solve('V10',mask,{'connectivity':4,'min_area':1}),[[1,1,1,1,1],[2,2,1,1,1]])
        self.assertEqual(self.solve('V10',mask,{'connectivity':8,'min_area':2}),[[1,1,2,2,2]])
        self.assertEqual(self.solve('V10',mask,{'connectivity':8,'min_area':3}),[])
        # Gamma endpoints, identity, and explicit power direction.
        image=np.array([[0,64,128,255]],np.uint8)
        np.testing.assert_array_equal(self.solve('V08',image,{'gamma':1}),image)
        self.assertGreater(self.solve('V08',image,{'gamma':.5})[0,1],64)
        previous=np.array([[255,0,50,70]],np.uint8);current=np.array([[0,255,70,50]],np.uint8)
        np.testing.assert_array_equal(self.solve('V14',current,{'previous':previous,'threshold':20}),[[255,255,0,0]])
        hsv=np.array([[[0,255,255],[179,255,255],[90,255,255],[0,0,255],[0,255,30]]],np.uint8)
        bgr=cv2.cvtColor(hsv,cv2.COLOR_HSV2BGR)
        np.testing.assert_array_equal(self.solve('V13',bgr,dict(hue_low=170,hue_high=10,s_min=100,v_min=100)),[[255,255,0,0,0]])

    def test_04_matching_orders_and_ties(self):
        # High-score broad box consumes truth0; input-order processing would yield two TPs.
        cases=[
            (dict(predictions=[[0,0,10,10,.1,0],[0,0,30,10,.9,0]],truth=[[0,0,10,10,0],[20,0,30,10,0]],iou_threshold=.3),dict(tp=1,fp=1,fn=1)),
            # Same score: first prediction wins; same IoU: first truth wins.
            (dict(predictions=[[0,0,30,10,.8,0],[0,0,10,10,.8,0]],truth=[[0,0,10,10,0],[20,0,30,10,0]],iou_threshold=.3),dict(tp=1,fp=1,fn=1)),
            (dict(predictions=[[20,0,30,10,.9,0],[0,0,10,10,.8,0]],truth=[[0,0,10,10,0],[20,0,30,10,0]],iou_threshold=.5),dict(tp=2,fp=0,fn=0)),
        ]
        for params,expected in cases:
            self.assertEqual(self.solve('Y05',None,params),expected)
        self.assertEqual(self.solve('L03',None,{'frames':[[1,2,3,4]]}),dict(mean_ms=10,p95_ms=10,serial_fps=100))

    def test_05_upgrade_preserves_old_source_notes_and_progress(self):
        old=[lesson for lesson in LESSONS if lesson['id'] not in ADVANCED_IDS and not lesson['id'].startswith('E')]
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);code=native_code(BY_ID['P01']['reference'])+'\n# learner annotation\n'
            with patch('learning.storage.LESSONS',old),patch('backend.workspace.LESSONS',old):
                store=Store(root/'data');store.save('P01',code,'my existing note')
                store.set_setting('hub.course.S00',json.dumps({'checks':[0],'note':'keep course note'}))
                workspace=Workspace(root/'workspace');workspace.initialize(store)
                store.record('P01',store.codes(),dict(verify=True,passed=True))
                store.connection.close()
            store=Store(root/'data')
            try:
                Workspace(root/'workspace').initialize(store)
                self.assertEqual(store.draft('P01'),(code,'my existing note'))
                self.assertEqual((root/'workspace/exercises/P01.py').read_text(encoding='utf-8'),code)
                self.assertTrue(store.passed('P01',store.codes()))
                self.assertEqual(json.loads(store.setting('hub.course.S00'))['note'],'keep course note')
                for key in ADVANCED_IDS:
                    self.assertTrue((root/'workspace/exercises'/f'{key}.py').is_file())
                    self.assertIn('TODO',store.draft(key)[0])
                    self.assertFalse(store.passed(key,store.codes()))
            finally:
                store.connection.close()

    def test_06_new_course_records_and_worker(self):
        baseline.PlatformChecks.setUpClass()
        client=baseline.PlatformChecks.client
        for course in COURSES:
            if int(course['id'][1:])<16:continue
            value={'checks':[0,2],'note':'进阶课程验收 '+course['id']}
            client.put('/api/settings/course.'+course['id'],json={'value':value}).raise_for_status()
            boot=client.get('/api/bootstrap').json()
            self.assertEqual(boot['settings']['hub.course.'+course['id']],value)
        case=baseline.PlatformChecks()
        for key in ['V10','Y05','L02']:
            job=case.run_code(key,BY_ID[key]['reference'])
            self.assertEqual(job['status'],'done',job)
            self.assertTrue(job['result']['passed'],job)


if __name__=='__main__':
    unittest.main(verbosity=2)
