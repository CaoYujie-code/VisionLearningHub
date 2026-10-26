"""Acceptance for the explicitly isolated launcher workspace only."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import urllib.request

project = Path.cwd().resolve()
root = Path((project / '.test-data-location.txt').read_text(encoding='utf-8-sig').strip()).resolve()
assert root.parent == project / '.test-data' and root.name.startswith('acceptance-v020-')
os.environ.update(VLH_DATA_ROOT=str(root), PYTHONUTF8='1')
state = json.loads((root / 'server.json').read_text())
url = state['url']
assert url.startswith('http://127.0.0.1:')
port = url.rsplit(':', 1)[1]

def fetch(path):
    with urllib.request.urlopen(url + path, timeout=2) as response:
        return response.read()

def health():
    return json.loads(fetch('/api/health'))

def snapshot():
    html = fetch('/').decode()
    token = re.search(r'<meta name="vlh-token" content="([^"]+)"', html).group(1)
    request = urllib.request.Request(url + '/api/bootstrap', headers={'X-VLH-Token': token})
    with urllib.request.urlopen(request, timeout=3) as response:
        boot = json.load(response)
    return {key: value for key, value in boot.items() if key in ('settings', 'attempts', 'progress', 'drafts', 'notes')}

def launch(*args):
    subprocess.run([sys.executable, str(project / 'launch.py'), *args], check=True, timeout=30)

def stop():
    launch('--stop')
    for _ in range(40):
        try:
            health()
        except Exception:
            return
        time.sleep(.1)
    raise AssertionError('Owned test service did not stop')

before_health = health()
assert before_health['instance'] == state['instance']
before = snapshot()
assert before.get('settings'), 'Expected browser acceptance notes and settings'
try:
    launch('--no-browser', '--port', port)
    assert health()['instance'] == before_health['instance']
    print('PASS duplicate launch reuses the owned instance')
    stop()
    print('PASS owned instance stops gracefully')
    launch('--no-browser', '--port', port)
    assert health()['instance'] != before_health['instance']
    after = snapshot()
    assert before == after, 'Persisted learning state changed after restart'
    print('PASS restart preserves persisted bootstrap learning state')
finally:
    stop()
print('PASS final cleanup leaves no owned test service')
(project / 'validation' / 'lifecycle-results.json').write_text(json.dumps({
    'version': '0.2.0', 'passed': 4, 'comparedFields': sorted(before),
    'isolatedTestData': True, 'testServiceStopped': True,
}, indent=2), encoding='utf-8')
