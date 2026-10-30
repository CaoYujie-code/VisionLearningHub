"""Independent numeric checks and backward compatibility for the second visual batch."""
import hashlib
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
from learning.advanced_engine import components
from learning.walkthrough_display import validate_shape


def execute(key,value):
    with tempfile.TemporaryDirectory() as folder:
        image,params=w.sample(key,value,Path(folder))
        scope=dict(np=np,cv2=cv2,image=image.copy(),params=params)
        for step in w.definition(key)['steps']:exec(step['code'],scope)
        return image,params,scope


class ExpandedVisualChecks(unittest.TestCase):
    def setUp(self):
        self.client=baseline.TestClient(baseline.server.app,base_url='http://127.0.0.1')
        self.client.headers['X-VLH-Token']=baseline.server.TOKEN

    def test_catalog_and_first_batch_revision_compatibility(self):
        self.assertEqual(self.client.get('/api/bootstrap').json()['walkthroughs'],list(w.CATALOG))
        self.assertEqual(len(w.CATALOG),31)
        self.assertEqual(sum(len(v['steps']) for v in w.CATALOG.values()),84)
        self.assertEqual(sum(len(v['control']['values']) for v in w.CATALOG.values()),95)
        snapshot=json.loads((Path(__file__).parent/'data/visual-v090-revisions.json').read_text(encoding='utf-8'))
        for key,expected in snapshot.items():
            self.assertEqual(w.revision(key),expected)
            data=dict(revision=expected,step=1,mode='write',notes={'step1':'existing observation'},done=[0],parameter=w.parameter(key))
            self.client.post('/api/lesson/'+key+'/walkthrough/progress',json=data).raise_for_status()
            self.assertEqual(self.client.get('/api/lesson/'+key+'/walkthrough').json()['progress'],data)

    def test_histogram_lut_and_integral_keep_native_values(self):
        image,_,scope=execute('V01',128)
        self.assertEqual(scope['histogram'].shape,(256,))
        self.assertEqual(int(scope['histogram'].sum()),image.size)
        for level in (0,64,128,192,255):self.assertEqual(scope['histogram'][level],int(np.count_nonzero(image==level)))
        image,params,scope=execute('V08',50)
        self.assertEqual(scope['table'][0],0);self.assertEqual(scope['table'][255],255)
        np.testing.assert_array_equal(scope['adjusted'],np.floor(255*(image.astype(float)/255)**.5).astype(np.uint8))
        image,params,scope=execute('V05',40)
        self.assertEqual(scope['integral'].shape,(image.shape[0]+1,image.shape[1]+1))
        self.assertFalse(np.any(scope['integral'][0]));self.assertFalse(np.any(scope['integral'][:,0]))
        x,y,width,height=params['roi'];self.assertEqual(scope['total'],image[y:y+height,x:x+width].sum(dtype=np.int64))
        self.assertEqual(scope['summary'][0,2],width*height)

    def test_perspective_mapping_and_label_connectivity(self):
        image,params,scope=execute('A03',0)
        mapped=cv2.perspectiveTransform(scope['source'][None,:,:],scope['matrix'])[0]
        np.testing.assert_allclose(mapped,scope['target'],atol=1e-4)
        self.assertEqual(scope['rectified'].shape,tuple(reversed(params['size']))+(3,))
        _,_,wrong=execute('A03',1);self.assertFalse(np.array_equal(wrong['rectified'],scope['rectified']))
        counts=[]
        for connection in (4,8):
            image,params,scope=execute('V10',connection)
            self.assertEqual(scope['rows'],components(image,connection,params['min_area']))
            counts.append(len(scope['rows']))
        self.assertEqual(counts,[3,2])

    def test_auxiliary_inputs_and_matching_coordinates(self):
        for trim in (0,2,4):
            _,params,scope=execute('V12',trim)
            self.assertEqual(scope['location'],(170+trim,90+trim))
            self.assertEqual(scope['response'].shape,(220-params['template'].shape[0]+1,340-params['template'].shape[1]+1))
            files=w.bundle(baseline.server.ROOT,'V12',trim)
            context=json.loads(files['context.json'])
            template=np.load(io.BytesIO(files['template.npy']),allow_pickle=False)
            self.assertEqual(context['additional_inputs']['template']['sha256'],hashlib.sha256(template.tobytes()).hexdigest())
        image,params,scope=execute('V14',40)
        difference=np.abs(image.astype(np.int16)-params['previous'].astype(np.int16))
        np.testing.assert_array_equal(scope['motion'],(difference>40).astype(np.uint8)*255)
        self.assertGreater(np.count_nonzero(scope['motion'][60:120,60:120]),0)
        self.assertGreater(np.count_nonzero(scope['motion'][60:120,140:200]),0)
        self.assertIn('previous.npy',w.bundle(baseline.server.ROOT,'V14',40))

    def test_distance_and_hue_experiments_have_correct_semantics(self):
        image,_,scope=execute('V11',5)
        ys,xs=np.nonzero(image)
        expected=np.zeros_like(scope['distance'])
        for y,x in zip(ys,xs):expected[y,x]=min(x-xs.min()+1,xs.max()-x+1,y-ys.min()+1,ys.max()-y+1)
        np.testing.assert_allclose(scope['distance'],expected,atol=1e-6)
        for saturation in (0,100,200):
            image,_,scope=execute('V13',saturation)
            hsv=cv2.cvtColor(image,cv2.COLOR_BGR2HSV);h,s,v=cv2.split(hsv)
            expected=(((h>=170)|(h<=10))&(s>=saturation)&(v>=100)).astype(np.uint8)*255
            np.testing.assert_array_equal(scope['red'],expected)

    def test_chart_rendering_and_import_shape_boundaries(self):
        for key,step,shape in [('V01','step1',[256]),('A03','step2',[3,3]),('V08','step1',[256]),('V05','step3',[1,3])]:
            data=self.client.get('/api/lesson/'+key+'/walkthrough').json()['demo']['results'][step]
            self.assertEqual(data['shape'],shape);self.assertFalse(data['spatial'])
            self.assertTrue(self.client.get(data['output']).content.startswith(b'\x89PNG'))
        for shape,mode in [((256,),'image'),((255,),'histogram'),((1,256),'curve'),((13,3),'matrix'),((3,3,3),'heatmap')]:
            with self.assertRaises(ValueError):validate_shape(shape,np.dtype('float32'),mode)
        with self.assertRaises(ValueError):validate_shape((3,3),np.dtype('float32'),'labels')
        with self.assertRaises(ValueError):validate_shape((256,),np.dtype('object'),'curve')

if __name__=='__main__':unittest.main(verbosity=2)
