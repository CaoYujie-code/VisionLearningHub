"""Text diagnosis examples must retain original indices and contract semantics."""
import json,tempfile,unittest
from pathlib import Path
import test_platform as baseline
import cv2
import numpy as np
from learning import walkthrough as w
from learning.curriculum import BY_ID
from test_visual_expansion import execute

def run_text(key,params):
    scope=dict(np=np,cv2=cv2,image=np.zeros((240,400,3),np.uint8),params=params)
    for step in w.definition(key)['steps']:exec(step['code'],scope)
    return scope

class TextDiagnosticChecks(unittest.TestCase):
    def test_previous_39_definitions_and_coverage(self):
        old=json.loads((Path(__file__).parent/'data/visual-v0150-revisions.json').read_text())
        self.assertEqual(len(old),39)
        for key,revision in old.items():self.assertEqual(w.revision(key),revision)
        self.assertEqual(len(w.CATALOG),44)
        self.assertEqual(sum(len(v['steps']) for v in w.CATALOG.values()),137)
        self.assertEqual(sum(len(v['control']['values']) for v in w.CATALOG.values()),137)

    def test_label_repair_stages_and_reason_codes(self):
        for stage,expected in [(0,[2,3,4,5,6,7,9]),(1,[5,6,7,9]),(2,[])]:
            _,params,scope=execute('Y01',stage)
            self.assertEqual(scope['invalid'],expected)
            self.assertEqual(scope['invalid_rows'].shape,(len(expected),1))
            self.assertEqual(scope['parse_table'][1].tolist(),[1,0,0])
            self.assertNotIn(1,scope['reasons'])
            self.assertEqual(len(params['labels']),10)
        _,_,scope=execute('Y01',0)
        np.testing.assert_array_equal(scope['parse_table'][2:5,2],[1,2,3])
        self.assertEqual(scope['reasons'][7],'框超出边界')

    def test_label_nonfinite_noninteger_and_dimensions_match_contract(self):
        labels=['0 0.5 0.5 1 1','-1 0.5 0.5 0.2 0.2','0.5 0.5 0.5 0.2 0.2','0 inf 0.5 0.2 0.2','0 0.5 0.5 nan 0.2','0 0.5 0.5 0 0.2','0 0.5 0.5 -0.2 0.2','0 1e999 0.5 0.2 0.2','x 0.5 0.5 0.2 0.2','0 0.5 0.5 0.2']
        params=dict(labels=labels,classes=2);scope=run_text('Y01',params)
        self.assertEqual(scope['invalid'],list(range(1,10)))
        reference={};exec(BY_ID['Y01']['reference'],reference)
        self.assertEqual(scope['invalid'],reference['solve'](None,params))
        for key in ['parse_table','check_table','invalid_rows']:self.assertTrue(np.isfinite(scope[key]).all())

    def test_label_whole_box_and_tolerated_boundary(self):
        labels=['0 0.95 0.5 0.2 0.2','0 0.1 0.1 0.2 0.2','0 0.0999999995 0.1 0.2 0.2','0 0.099999998 0.1 0.2 0.2']
        scope=run_text('Y01',dict(labels=labels,classes=1))
        self.assertEqual(scope['invalid'],[0,3])
        np.testing.assert_array_equal(scope['check_table'][:,3],[0,1,1,0])

    def test_empty_and_blank_labels_preserve_no_fake_rows(self):
        for labels in [[],['',' ','\t']]:
            scope=run_text('Y01',dict(labels=labels,classes=2))
            self.assertEqual(scope['invalid'],[])
            self.assertEqual(scope['invalid_rows'].shape,(0,1));self.assertEqual(scope['check_table'].shape,(0,4))
            self.assertEqual(scope['parse_table'].shape,(len(labels),3))
            self.assertEqual(np.count_nonzero(scope['output']),0)

    def test_log_samples_distinguish_none_empty_and_message(self):
        for value,expected,last in [(0,dict(error_count=0,warning_count=1,last_error=None),-1),(1,dict(error_count=2,warning_count=2,last_error=''),7),(2,dict(error_count=3,warning_count=2,last_error='codec failed'),9)]:
            _,params,scope=execute('L01',value)
            self.assertEqual(scope['result'],expected);self.assertEqual(scope['last_index'],last)
            self.assertEqual(scope['parsed_table'][2,2],1)
            self.assertEqual(scope['trace_rows'][-1].tolist(),[len(params['lines'])-1,expected['error_count'],expected['warning_count'],last])

    def test_log_whitespace_unknown_levels_and_remaining_message(self):
        lines=['ERROR','ERROR\tignored','error lower',' ERROR leading','INFO ERROR in body','DEBUG ERROR unknown','WARN note','ERROR  camera failed now ','INFO done']
        params=dict(lines=lines);scope=run_text('L01',params)
        expected=dict(error_count=1,warning_count=1,last_error=' camera failed now ')
        self.assertEqual(scope['result'],expected);self.assertEqual(scope['last_index'],7)
        reference={};exec(BY_ID['L01']['reference'],reference)
        self.assertEqual(scope['result'],reference['solve'](None,params))
        empty=run_text('L01',dict(lines=[]));self.assertEqual(empty['result'],dict(error_count=0,warning_count=0,last_error=None));self.assertEqual(empty['trace_rows'].shape,(0,4))

    def test_original_text_and_portable_parameters_are_identical(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            for key,field in [('Y01','labels'),('L01','lines')]:
                for value in w.definition(key)['control']['values']:
                    demo=w.demonstration(root,key,value);files=w.bundle(root,key,value)
                    params=json.loads(files['params.json'])
                    self.assertEqual(demo['source_text']['lines'],params[field])
                    self.assertEqual(demo['parameters'][field],params[field])
                    for step in w.definition(key)['steps']:
                        if step.get('columns'):self.assertEqual(demo['results'][step['id']]['columns'],step['columns'])
            self.assertIsNone(w.demonstration(root,'T11')['source_text'])
            self.assertEqual(w.demonstration(root,'L01',1)['source_text']['lines'][7],'ERROR ')

if __name__=='__main__':unittest.main(verbosity=2)
