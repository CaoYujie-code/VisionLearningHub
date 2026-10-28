"""Teaching examples must run outside the hub, and reading never changes grades."""
import ast
import io
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
import test_platform as baseline
from learning.curriculum import LESSONS
from learning.function_handbook import CATALOG, CARDS, guide
from backend.workspace import lesson_outline

class HandbookChecks(unittest.TestCase):
    def test_all_basic_lessons_have_specific_guidance(self):
        basic=[l for l in LESSONS if not l['id'].startswith('E')]
        self.assertEqual(set(CATALOG['lessons']),{l['id'] for l in basic})
        self.assertEqual(len(CARDS),40)
        self.assertEqual({k for l in CATALOG['lessons'].values() for k in l['cards']},set(CARDS))
        for lesson in basic:
            g=guide(lesson['id'])
            self.assertTrue(g['decision'] and g['question'] and g['cards'])
            self.assertEqual(lesson_outline(lesson)['function_guide'],g)
            for card in g['cards']:
                self.assertTrue(all(card[k] for k in ('signature','parameters','returns','use','avoid','pitfall','expect','experiment','docs')))
                self.assertTrue(card['docs'].startswith(('https://docs.opencv.org/','https://numpy.org/','https://docs.python.org/')))

    def test_every_example_runs_standalone_with_assertions(self):
        with tempfile.TemporaryDirectory() as temp:
            for key,card in CARDS.items():
                with self.subTest(key=key):
                    tree=ast.parse(card['example'])
                    self.assertTrue(any(isinstance(n,ast.Assert) for n in ast.walk(tree)))
                    for n in ast.walk(tree):
                        if isinstance(n,ast.Import):self.assertTrue(all(v.name in ('cv2','numpy','math') for v in n.names))
                        self.assertNotIsInstance(n,ast.ImportFrom)
                    file=Path(temp)/(key+'.py');file.write_text(card['example'],encoding='utf-8')
                    run=subprocess.run([sys.executable,'-X','utf8',str(file)],cwd=temp,capture_output=True,text=True,encoding='utf-8',timeout=10)
                    self.assertEqual(run.returncode,0,run.stdout+run.stderr)
                    self.assertTrue(run.stdout.strip())

    def test_export_is_complete_and_does_not_mutate_learning(self):
        client=baseline.TestClient(baseline.server.app,base_url='http://127.0.0.1')
        client.headers['X-VLH-Token']=baseline.server.TOKEN
        before=client.get('/api/lesson/T03').json()
        boot_before=client.get('/api/bootstrap').json()
        response=client.get('/api/lesson/T03/examples');self.assertEqual(response.status_code,200)
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            self.assertEqual(set(archive.namelist()),{'color.py','threshold.py','README.md'})
            text=archive.read('README.md').decode('utf-8')
            self.assertIn('| 参数 | 含义 | 选择与限制 |',text)
            self.assertIn('python threshold.py',text)
            self.assertIn('不适用/限制',text)
            for card in guide('T03')['cards']:
                self.assertEqual(archive.read(card['id']+'.py').decode('utf-8').replace('\r\n','\n'),card['example'])
        after=client.get('/api/lesson/T03').json()
        self.assertEqual((after['code'],after['note'],after['history']),(before['code'],before['note'],before['history']))
        self.assertEqual(client.get('/api/bootstrap').json()['passed'],boot_before['passed'])
        self.assertEqual(client.get('/api/lesson/E07/examples').status_code,404)
        self.assertEqual(client.get('/api/lesson/Z99/examples').status_code,404)

if __name__=='__main__':unittest.main(verbosity=2)
