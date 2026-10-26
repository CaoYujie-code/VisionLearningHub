"""Create an isolated data root and own the complete browser-test server lifetime."""
import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

PROJECT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--node',default='node');parser.add_argument('--suite',choices=['full','guides'],default='full');args=parser.parse_args()
base=PROJECT/'.test-data';base.mkdir(exist_ok=True)
root=Path(tempfile.mkdtemp(prefix='browser-v030-',dir=base))
with socket.socket() as probe:
    probe.bind(('127.0.0.1',0));port=probe.getsockname()[1]
env=os.environ.copy();env.update(VLH_DATA_ROOT=str(root),PYTHONUTF8='1',VLH_TEST_URL=f'http://127.0.0.1:{port}')
env.pop('VLH_WORKSPACE',None)
with (root/'server.log').open('wb') as log:
    process=subprocess.Popen([sys.executable,'app_server.py','--port',str(port),'--managed'],cwd=PROJECT,env=env,stdin=subprocess.PIPE,stdout=log,stderr=log,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    try:
        for _ in range(100):
            try:
                with urllib.request.urlopen(env['VLH_TEST_URL']+'/api/health',timeout=.5):break
            except Exception:
                if process.poll() is not None:raise RuntimeError('Test server exited')
                time.sleep(.1)
        else:raise RuntimeError('Test server failed to start')
        if args.suite=='full':subprocess.run([args.node,'tests/browser.mjs'],cwd=PROJECT,env=env,check=True,timeout=180)
        if args.suite=='full':subprocess.run([args.node,'tests/check_images.mjs'],cwd=PROJECT,env=env,check=True,timeout=40)
        if args.suite=='full':subprocess.run([args.node,'tests/projects_browser.mjs'],cwd=PROJECT,env=env,check=True,timeout=180)
        subprocess.run([args.node,'tests/guides_browser.mjs'],cwd=PROJECT,env=env,check=True,timeout=180)
    finally:
        process.stdin.close()
        try:process.wait(timeout=8)
        except subprocess.TimeoutExpired:process.terminate();process.wait(timeout=5)
print('Isolated browser service stopped')
