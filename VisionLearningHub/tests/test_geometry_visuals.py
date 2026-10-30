"""Numeric oracles, boundary cases, imports and compatibility for visual geometry."""
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
import test_platform as baseline
import cv2
import numpy as np
from learning import walkthrough as w
from learning.walkthrough_display import validate_shape
from test_visual_expansion import execute

class GeometryVisualChecks(unittest.TestCase):
    def test_previous_23_revisions_and_saved_progress_survive(self):
        old=json.loads((Path(__file__).parent/'data/visual-v0100-revisions.json').read_text())
        self.assertEqual(len(old),23)
        for key,revision in old.items():self.assertEqual(w.revision(key),revision)
        self.assertEqual(len(w.CATALOG),31)
        self.assertEqual(sum(len(v['steps']) for v in w.CATALOG.values()),84)
        self.assertEqual(sum(len(v['control']['values']) for v in w.CATALOG.values()),95)

    def test_filters_empty_output_and_roi_statistics(self):
        for threshold,expected in [(0,[0,1,2,3,4,5]),(80,[3,4,5]),(150,[])]:
            _,_,scope=execute('P01',threshold)
            np.testing.assert_array_equal(scope['selected'].ravel(),expected)
        for threshold in (64,128,192):
            _,_,scope=execute('P02',threshold)
            np.testing.assert_array_equal(scope['summary'],[[127.5,(223-threshold)*120,120,192]])
        with tempfile.TemporaryDirectory() as folder:
            result=w.demonstration(folder,'P01',150)['results']['step3']
            self.assertEqual(result['shape'],[0,1]);self.assertIsNone(result['minimum']);self.assertIsNone(result['maximum'])
            self.assertEqual(result['cells'],[]);self.assertTrue(Path(result['output']).is_file())
        for shape,mode in [((0,0),'matrix'),((0,9),'matrix'),((0,1),'image'),((1,0),'matrix'),((0,),'histogram')]:
            with self.assertRaises(ValueError):validate_shape(shape,np.dtype('int32'),mode)

    def test_moments_rotation_and_degenerate_contours(self):
        item=w.definition('T07')
        rectangle=np.array([[[0,0]],[[10,0]],[[10,20]],[[0,20]]],np.int32)
        scope=dict(np=np,cv2=cv2,contours=[rectangle,np.array([[[1,1]]],np.int32)])
        exec(item['steps'][1]['code'],scope)
        np.testing.assert_allclose(scope['center_table'],[[5,10,200]])
        for angle in (0,90,180):
            _,params,scope=execute('T08',angle);points=np.asarray(params['points'])
            expected={0:points,90:np.column_stack([-points[:,1],points[:,0]]),180:-points}[angle]
            np.testing.assert_allclose(scope['transformed'],expected+[220,150],atol=1e-10)
            np.testing.assert_allclose(np.linalg.norm(scope['transformed'][1:]-scope['transformed'][:-1],axis=1),np.linalg.norm(points[1:]-points[:-1],axis=1))

    def test_raster_coverage_counts_and_gap_are_independent(self):
        for shift in (0,30,80):
            _,_,scope=execute('T09',shift)
            np.testing.assert_allclose(scope['quality'],[[1-shift/240,shift/240]])
            self.assertEqual(np.count_nonzero(scope['counts']==2),shift*160)
            self.assertEqual(np.count_nonzero(scope['counts'][80:240,80:320]==0),shift*160)

    def test_temporal_alignment_and_outlier_effect(self):
        centers=np.array([[70,70],[170,90],[270,140]])
        estimates=[]
        for value in (0,20,100):
            _,_,scope=execute('T12',value)
            self.assertEqual(scope['aligned_table'].shape,(7,6))
            self.assertTrue(np.all(np.abs(scope['median_centers']-centers)<1.6))
            estimates.append(scope['mean_centers'])
        np.testing.assert_allclose(estimates[-1]-estimates[0],np.tile([100/7,50/7],(3,1)),atol=1e-10)

    def test_iou_and_nms_threshold_ties_empty_and_stable_order(self):
        for value,expected in [(0,7200/23600),(50,3200/27600),(150,0)]:
            _,_,scope=execute('A04',value);self.assertAlmostEqual(scope['iou_value'],expected)
        for threshold,expected in [(20,[0,3]),(50,[0,3,2]),(80,[0,1,3,2])]:
            _,_,scope=execute('A05',threshold);self.assertEqual(scope['kept'],expected)
            self.assertEqual(scope['order'],[0,1,3,4,2]);np.testing.assert_allclose(np.diag(scope['pairwise']),1)
        self.assertEqual(scope['iou']([0,0,0,0],[0,0,0,0]),0)
        scope.update(boxes=np.array([[0,0,2,1],[0,0,1,1]],float),order=[0,1],params={'iou_percent':50})
        exec(w.definition('A05')['steps'][2]['code'],scope);self.assertEqual(scope['kept'],[0,1])
        scope['order']=[];exec(w.definition('A05')['steps'][2]['code'],scope)
        self.assertEqual(scope['kept'],[]);self.assertEqual(scope['trace_table'].shape,(0,5))

    def test_numeric_comparison_tolerances_integer_extremes_and_empty(self):
        result=w.numeric_difference(np.array([[0,255]],np.uint8),np.array([[255,255]],np.uint8))
        self.assertEqual(result['different'],1);self.assertEqual(result['max_abs'],255);self.assertEqual(result['mean_abs'],127.5);self.assertEqual(result['first'],[0,0])
        for dtype,a,b in [('uint64',2**64-1,2**64-2),('int64',-2**63,2**63-1)]:
            result=w.numeric_difference(np.array([a],dtype=dtype),np.array([b],dtype=dtype))
            self.assertEqual(result['different'],1);self.assertEqual(result['max_abs'],float(abs(a-b)))
        result=w.numeric_difference(np.array([1.+1e-7,2.]),np.array([1.,2.]))
        self.assertEqual(result['different'],0);self.assertGreater(result['mean_abs'],0)
        self.assertFalse(w.numeric_difference(np.array([1],np.int32),np.array([1],np.int64))['available'])
        self.assertFalse(w.numeric_difference(np.array([1e308]),np.array([-1e308]))['available'])
        result=w.numeric_difference(np.empty((0,1),np.int32),np.empty((0,1),np.int32))
        self.assertEqual((result['different'],result['total'],result['mean_abs'],result['first']),(0,0,0,None))

    def test_import_empty_and_modified_arrays_without_changing_grade(self):
        client=baseline.TestClient(baseline.server.app,base_url='http://127.0.0.1');client.headers['X-VLH-Token']=baseline.server.TOKEN
        before=client.get('/api/bootstrap').json()['passed']
        def pack(key,value,arrays):
            data=io.BytesIO();demo=w.demonstration(baseline.server.ROOT,key,value)
            with zipfile.ZipFile(data,'w') as archive:
                archive.writestr('context.json',json.dumps(demo['context']))
                for name,array in arrays.items():
                    raw=io.BytesIO();np.save(raw,array,allow_pickle=False);archive.writestr(name+'.npy',raw.getvalue())
            return data.getvalue()
        raw=pack('P01',150,{'step3':np.empty((0,1),np.int32)})
        response=client.post('/api/lesson/P01/walkthrough/import',files={'file':('results.zip',raw)})
        response.raise_for_status();own=response.json();self.assertEqual(set(own['results']),{'step3'})
        self.assertEqual(own['results']['step3']['difference']['different'],0)
        raw=pack('A04',0,{'step3':np.array([[0.5]])})
        response=client.post('/api/lesson/A04/walkthrough/import',files={'file':('results.zip',raw)})
        response.raise_for_status();d=response.json()['results']['step3']['difference']
        self.assertEqual(d['different'],1);self.assertEqual(d['first'],[0,0]);self.assertAlmostEqual(d['max_abs'],.5-7200/23600)
        raw=pack('A04',0,{'step3':np.array([[0.5,0.1]])})
        response=client.post('/api/lesson/A04/walkthrough/import',files={'file':('results.zip',raw)})
        response.raise_for_status();self.assertFalse(response.json()['results']['step3']['difference']['available'])
        self.assertEqual(client.get('/api/bootstrap').json()['passed'],before)

if __name__=='__main__':unittest.main(verbosity=2)
