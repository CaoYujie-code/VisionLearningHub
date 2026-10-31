"""Independent teaching oracles for detection evaluation and deployment fundamentals."""
import io,json,hashlib,tempfile,unittest
from pathlib import Path
import test_platform as baseline
import numpy as np
from learning import walkthrough as w
from test_visual_expansion import execute

class DetectionVisualChecks(unittest.TestCase):
    def test_previous_31_definitions_and_catalog(self):
        old=json.loads((Path(__file__).parent/'data/visual-v0110-revisions.json').read_text())
        self.assertEqual(len(old),31)
        for key,revision in old.items():self.assertEqual(w.revision(key),revision)
        self.assertEqual(len(w.CATALOG),37)
        self.assertEqual(sum(len(v['steps']) for v in w.CATALOG.values()),103)
        self.assertEqual(sum(len(v['control']['values']) for v in w.CATALOG.values()),113)

    def test_letterbox_inverse_clipping_and_portable_original(self):
        for value in (50,100,150):
            image,params,scope=execute('Y02',value)
            self.assertEqual(image.shape,(int(160*value/100)+60,int(240*value/100)+40,3))
            np.testing.assert_allclose(scope['restored'],[[20,30,120,100],[-15,20,60,90],[180,100,270,180]])
            np.testing.assert_allclose(scope['clipped'],[[20,30,120,100],[0,20,60,90],[180,100,240,160]])
            self.assertEqual(scope['output'].shape,(160,240,3))
            files=w.bundle(baseline.server.ROOT,'Y02',value)
            original=np.load(io.BytesIO(files['original.npy']),allow_pickle=False)
            np.testing.assert_array_equal(original,params['original'])
            context=json.loads(files['context.json']);self.assertEqual(context['additional_inputs']['original']['sha256'],hashlib.sha256(original.tobytes()).hexdigest())
        scope['boxes']=np.empty((0,4))
        for step in w.definition('Y02')['steps'][1:]:exec(step['code'],scope)
        self.assertEqual(scope['clipped'].shape,(0,4))

    def test_binary_metrics_and_zero_denominators(self):
        for threshold,expected in [(25,[3,3,1,.5,.75]),(50,[2,2,2,.5,.5]),(90,[1,0,3,1.,.25])]:
            _,_,scope=execute('Y03',threshold);np.testing.assert_allclose(scope['metrics'],[expected]);self.assertEqual(scope['confusion'].sum(),8)
        scope.update(truth=np.zeros(3,np.int32),predicted=np.zeros(3,np.int32))
        for step in w.definition('Y03')['steps'][1:]:exec(step['code'],scope)
        np.testing.assert_array_equal(scope['metrics'],[[0,0,0,0,0]])

    def test_group_leakage_counts_distinct_splits(self):
        for value,expected in [(0,[]),(1,[0]),(2,[0,1])]:
            _,params,scope=execute('Y04',value)
            self.assertEqual(scope['leaked'],expected);self.assertEqual(int(scope['counts'].sum()),len(params['samples']))
        scope=dict(np=np,params={'samples':[{'group':7,'split':'train'}]*3})
        for step in w.definition('Y04')['steps']:exec(step['code'],scope)
        self.assertEqual(scope['leaked'],[])

    def test_detection_equality_duplicate_class_and_unmatched_targets(self):
        for threshold,expected,matched in [(50,[2,2,0],[0,3]),(60,[2,2,0],[1,3]),(95,[1,3,1],[1])]:
            _,_,scope=execute('Y05',threshold)
            np.testing.assert_array_equal(scope['counts'],[expected])
            self.assertEqual([int(row[0]) for row in scope['trace'] if row[4]],matched)
            self.assertEqual(scope['ious'][0,0],.5);self.assertEqual(scope['ious'][2,1],1)
        scope.update(predictions=np.empty((0,6)),targets=np.empty((0,5)),ious=np.empty((0,0)))
        for step in w.definition('Y05')['steps'][2:]:exec(step['code'],scope)
        np.testing.assert_array_equal(scope['counts'],[[0,0,0]])
        scope.update(predictions=np.array([[0,0,1,1,.9,0]]),targets=np.empty((0,5)),ious=np.empty((1,0)))
        for step in w.definition('Y05')['steps'][2:]:exec(step['code'],scope)
        np.testing.assert_array_equal(scope['counts'],[[0,1,0]])

    def test_stride_recovery_independent_copy_and_wrong_reshape(self):
        for padding in (0,1,4):
            original,params,scope=execute('L02',padding)
            np.testing.assert_array_equal(scope['restored'],original)
            self.assertEqual(np.array_equal(scope['wrong'],original),padding==0)
            np.testing.assert_array_equal(scope['layout'],[[4,3,3,9,1,0]])
            self.assertTrue(scope['restored'].flags.owndata)
            scope['buffer'][:]=0;np.testing.assert_array_equal(scope['restored'],original)

    def test_latency_linear_percentile_and_reciprocal_of_mean(self):
        for spike in (0,50,200):
            _,_,scope=execute('L03',spike)
            mean=(188+spike)/8;p95=25+.65*spike
            np.testing.assert_allclose(scope['summary'],[[mean,p95,1000/mean]])
            self.assertNotAlmostEqual(scope['serial_fps'],float(np.mean(1000/scope['totals'])))
        scope['totals']=np.array([10.])
        exec(w.definition('L03')['steps'][2]['code'],scope)
        np.testing.assert_allclose(scope['summary'],[[10,10,100]])

    def test_column_names_only_for_matching_width_and_old_frames_supported(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            for key in ['Y02','Y03','Y04','Y05','L02','L03']:
                demo=w.demonstration(root,key)
                for s in w.definition(key)['steps']:
                    if s.get('columns'):self.assertEqual(demo['results'][s['id']]['columns'],s['columns'])
            result=w.describe(np.ones((2,2)),'matrix',root,'wrong',columns=['a','b','c'])
            self.assertIsNone(result['columns'])
            result=w.describe(np.empty((0,1),np.int32),'matrix',root,'empty',columns=['组号'])
            self.assertEqual(result['columns'],['组号']);self.assertIsNone(result['minimum'])
            self.assertIsNone(w.demonstration(root,'A04')['results']['step3']['columns'])

if __name__=='__main__':unittest.main(verbosity=2)
