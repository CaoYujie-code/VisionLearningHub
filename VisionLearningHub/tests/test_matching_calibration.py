"""Independent numeric checks for pattern identity and affine calibration lessons."""
import json,tempfile,unittest
from pathlib import Path
import test_platform as baseline
import numpy as np
from learning import walkthrough as w
from test_visual_expansion import execute

class MatchingCalibrationChecks(unittest.TestCase):
    def test_previous_37_revisions_and_catalog(self):
        old=json.loads((Path(__file__).parent/'data/visual-v0140-revisions.json').read_text())
        self.assertEqual(len(old),37)
        for key,revision in old.items():self.assertEqual(w.revision(key),revision)
        self.assertEqual(len(w.CATALOG),41)
        self.assertEqual(sum(len(v['steps']) for v in w.CATALOG.values()),119)
        self.assertEqual(sum(len(v['control']['values']) for v in w.CATALOG.values()),125)

    def test_identity_stays_fixed_while_rotation_changes(self):
        for turns in (0,1,3):
            _,params,scope=execute('T11',turns)
            self.assertEqual(scope['identities'],[2,0,3,1])
            np.testing.assert_array_equal(scope['match_rows'][:,2],[(turns+i)%4 for i in range(4)])
            np.testing.assert_array_equal(scope['match_rows'][:,3],0)
            self.assertEqual(np.count_nonzero(scope['difference']),0)
            self.assertEqual(scope['best_template'],2);self.assertEqual(scope['best_k'],turns)
            self.assertEqual(np.count_nonzero(scope['scores']==0),1)

    def test_mse_uses_signed_difference_and_matches_scalar_oracle(self):
        _,_,scope=execute('T11',1)
        for j,template in enumerate(scope['templates']):
            for k in range(4):
                a=scope['patch'].ravel();b=np.rot90(template,k).ravel()
                expected=sum((int(x)-int(y))**2 for x,y in zip(a,b))/len(a)
                self.assertAlmostEqual(scope['scores'][j,k],expected)
        scope.update(patches=np.zeros((1,2,2),np.uint8),templates=np.full((1,2,2),255,np.uint8))
        exec(w.definition('T11')['steps'][1]['code'],scope)
        np.testing.assert_array_equal(scope['scores'],np.full((1,4),65025.))

    def test_empty_patches_and_ambiguous_templates_are_explicit(self):
        _,_,scope=execute('T11',0)
        scope['patches']=np.empty((0,48,48),np.uint8)
        exec(w.definition('T11')['steps'][3]['code'],scope)
        self.assertEqual(scope['identities'],[]);self.assertEqual(scope['match_rows'].shape,(0,4))
        scope.update(patches=np.zeros((1,2,2),np.uint8),templates=np.zeros((2,2,2),np.uint8))
        exec(w.definition('T11')['steps'][3]['code'],scope)
        np.testing.assert_array_equal(scope['match_rows'],[[0,0,0,0]])

    def test_affine_zero_noise_known_formula_and_noisy_scaling(self):
        outputs={}
        for noise in (0,2,8):
            _,params,scope=execute('T13',noise);outputs[noise]=scope
            expected=[[1.2*u+.25*v+30,-.1*u+.9*v+15] for u,v in params['checks']]
            np.testing.assert_allclose(scope['expected'],expected,atol=1e-12)
            self.assertEqual(scope['rank'],3);self.assertEqual(scope['check_rows'].shape,(4,7))
            np.testing.assert_allclose(scope['design'].T@(scope['fitted']-scope['platform']),0,atol=1e-8)
        np.testing.assert_allclose(outputs[0]['affine'],[[1.2,-.1],[.25,.9],[30,15]],atol=1e-12)
        np.testing.assert_allclose(outputs[0]['errors'],0,atol=1e-10)
        self.assertGreater(outputs[2]['errors'].max(),.1)
        np.testing.assert_allclose(outputs[8]['errors'],4*outputs[2]['errors'],atol=1e-10)

    def test_collinear_and_insufficient_points_stop_before_fit(self):
        for visual in ([[0,0],[1,1],[2,2],[3,3]],[[0,0],[1,2]],[[0,0]]):
            scope={'np':np,'visual':np.array(visual,float)}
            with self.assertRaisesRegex(ValueError,'共线'):exec(w.definition('T13')['steps'][1]['code'],scope)

    def test_check_truth_never_leaks_into_fitting_and_empty_checks_work(self):
        _,_,scope=execute('T13',2);before=scope['predicted'].copy();coefficients=scope['affine'].copy()
        scope['params']['expected_checks']=(scope['expected']+100).tolist()
        exec(w.definition('T13')['steps'][3]['code'],scope)
        np.testing.assert_array_equal(scope['predicted'],before);np.testing.assert_array_equal(scope['affine'],coefficients)
        self.assertGreater(scope['errors'].min(),100)
        scope['params'].update(checks=[],expected_checks=[])
        exec(w.definition('T13')['steps'][3]['code'],scope)
        self.assertEqual(scope['predicted'].shape,(0,2));self.assertEqual(scope['check_rows'].shape,(0,7))

    def test_display_columns_and_bundled_inputs_keep_numeric_values(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            for key in ['T11','T13']:
                for value in w.definition(key)['control']['values']:
                    demo=w.demonstration(root,key,value);files=w.bundle(root,key,value)
                    params=json.loads(files['params.json'])
                    self.assertEqual(params[w.definition(key)['control']['name']],value)
                    for step in w.definition(key)['steps']:
                        result=demo['results'][step['id']]
                        if step.get('columns'):self.assertEqual(result['columns'],step['columns'])
                        self.assertTrue(Path(result['output']).is_file())
                    if key=='T11':self.assertEqual(demo['results']['step3']['maximum'],0)
                    else:self.assertEqual(len(params['expected_checks']),4)

if __name__=='__main__':unittest.main(verbosity=2)
