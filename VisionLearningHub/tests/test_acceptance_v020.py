"""0.2.0 acceptance: reproducible lab examples, incorrect solutions, workers and notes."""
import json
from pathlib import Path
import unittest

import cv2
import numpy as np
import test_platform as baseline
from backend.courses import COURSES
from learning.curriculum import BY_ID, LESSONS
from learning.engine import fixture, check_result, execute

METHODS=['gray','histogram','threshold','otsu','adaptive','blur','median',
         'bilateral','equalize','sobel','hsv','canny']


class VisualAcceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        baseline.PlatformChecks.setUpClass.__func__(cls)

    wait_job=baseline.PlatformChecks.wait_job
    run_code=baseline.PlatformChecks.run_code

    def png(self,url):
        response=self.client.get(url)
        self.assertEqual(response.status_code,200)
        image=cv2.imdecode(np.frombuffer(response.content,np.uint8),cv2.IMREAD_UNCHANGED)
        self.assertIsNotNone(image)
        return image

    def test_01_displayed_code_reproduces_results(self):
        for method in METHODS:
            with self.subTest(method=method):
                result=self.client.post('/api/lab',json={'method':method,'kernel':5,'threshold':87,'low':20,'high':120,'hue_low':35,'hue_high':80,'block_size':31,'c':9}).json()
                scope={'image':self.png(result['input']),'cv2':cv2,'np':np}
                # The learner is told only to supply BGR image; no hidden gray variable.
                exec(result['code'],scope)
                np.testing.assert_array_equal(scope['result'],self.png(result['output']))

    def test_02_methods_scenes_and_parameter_boundaries(self):
        for source in ['standard','dim','noise','same_color']:
            for method in METHODS:
                with self.subTest(source=source,method=method):
                    response=self.client.post('/api/lab',json={'source':source,'method':method})
                    self.assertEqual(response.status_code,200,response.text)
                    result=response.json()
                    for key in ['input','middle','output']:
                        self.assertGreater(self.png(result[key]).size,0)
        for kernel in [1,15]:
            for method in ['blur','median','bilateral','sobel','hsv','canny']:
                with self.subTest(method=method,kernel=kernel):
                    self.assertEqual(self.client.post('/api/lab',json={'method':method,'kernel':kernel}).status_code,200)
        for block,c in [(3,0),(51,20)]:
            self.assertEqual(self.client.post('/api/lab',json={'method':'adaptive','block_size':block,'c':c}).status_code,200)
        raw=cv2.imencode('.png',np.full((8,12,3),90,np.uint8))[1].tobytes()
        upload=self.client.post('/api/upload',files={'file':('tiny.png',raw,'image/png')}).json()
        self.assertEqual(self.client.post('/api/lab',json={'source':'upload:'+upload['id'],'method':'adaptive','block_size':15}).status_code,400)
        self.assertEqual(self.client.post('/api/lab',json={'source':'upload:'+upload['id'],'method':'adaptive','block_size':3}).status_code,200)

    def test_03_new_graders_reject_wrong_answers(self):
        variants={
            'V01':[lambda im,p,t:np.zeros(256,np.int64),lambda im,p,t:t.astype(float)],
            'V02':[lambda im,p,t:255-t,lambda im,p,t:t.astype(float)],
            'V03':[lambda im,p,t:im.copy(),lambda im,p,t:t.astype(float)],
            'V04':[lambda im,p,t:{**t,'gx':-t['gx']},lambda im,p,t:{**t,'magnitude':np.full(im.shape,np.nan)},
                   lambda im,p,t:{**t,'gx':t['gx'].astype(np.int32)}],
            'V05':[lambda im,p,t:{**t,'total':t['total']+1},lambda im,p,t:{**t,'count':True}],
            'V06':[lambda im,p,t:{**t,'threshold':t['threshold']+1},lambda im,p,t:{**t,'mask':255-t['mask']}],
        }
        for key,answers in variants.items():
            im,p,truth=fixture(key,101,Path(baseline.TEMP.name)/'wrong'/key)
            for index,answer in enumerate(answers):
                with self.subTest(lesson=key,variant=index):
                    checks=check_result(key,im,p,truth,answer(im,p,truth['result']))
                    self.assertFalse(all(c['ok'] for c in checks),checks)

    def test_04_workers_and_new_course_backup(self):
        for key in ['V01','V02','V03','V04','V05','V06']:
            with self.subTest(lesson=key):
                job=self.run_code(key,BY_ID[key]['reference'])
                self.assertEqual(job['status'],'done',job)
                self.assertTrue(job['result']['passed'])
                self.assertEqual(len(job['result']['reports']),5)
                self.assertTrue(job['passed'][key])
                for report in job['result']['reports']:
                    self.assertIsNotNone(report['output'])
                    self.assertGreater(self.png(report['output']).size,0)
        # V06's previous pass must become stale when V01, a declared dependency, changes.
        self.client.put('/api/lesson/V01',json={'code':BY_ID['V01']['reference']+'\n# revision','note':''})
        self.assertFalse(self.client.get('/api/bootstrap').json()['passed']['V06'])
        for course in ['S12','S13','S14','S15']:
            response=self.client.put('/api/settings/course.'+course,json={'value':{'checks':[0,2],'note':'验收 '+course}})
            self.assertEqual(response.status_code,200)
        archive=self.client.get('/api/backup')
        self.assertEqual(archive.status_code,200)
        self.client.put('/api/settings/course.S15',json={'value':{'checks':[],'note':'changed'}})
        restored=self.client.post('/api/restore',files={'file':('v020.zip',archive.content,'application/zip')})
        self.assertEqual(restored.status_code,200,restored.text)
        boot=self.client.get('/api/bootstrap').json()
        for course in ['S12','S13','S14','S15']:
            self.assertEqual(boot['settings']['hub.course.'+course],{'checks':[0,2],'note':'验收 '+course})

    def test_05_course_prerequisites_precede_lessons(self):
        ordered=[lesson for course in COURSES for lesson in course['lessons']]
        positions={key:i for i,key in enumerate(ordered)}
        for key in ordered:
            for prerequisite in BY_ID[key]['prerequisites']:
                with self.subTest(lesson=key,prerequisite=prerequisite):
                    self.assertLess(positions[prerequisite],positions[key])


if __name__=='__main__':
    try:unittest.main(verbosity=2)
    finally:baseline.TEMP.cleanup()
