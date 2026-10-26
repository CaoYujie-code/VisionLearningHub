"""Run the packaged extension in a separate VS Code profile, never install globally."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

PROJECT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--with-debugger',action='store_true')
parser.add_argument('--code',required=True,help='Path to desktop Code.exe')
args=parser.parse_args()
base=PROJECT/'.test-data';base.mkdir(exist_ok=True)
root=Path(tempfile.mkdtemp(prefix='vscode-',dir=base))
workspace=root/'workspace';(workspace/'.vscode').mkdir(parents=True)
(workspace/'.vscode/settings.json').write_text(json.dumps({'visionLearning.pythonPath':sys.executable}),encoding='utf-8')
profile=root/'profile';(profile/'User').mkdir(parents=True)
(profile/'User/settings.json').write_text(json.dumps({'telemetry.telemetryLevel':'off','update.mode':'none','extensions.autoUpdate':False,'extensions.autoCheckUpdates':False,'workbench.startupEditor':'none','security.workspace.trust.enabled':False}),encoding='utf-8')
with zipfile.ZipFile(PROJECT.parent/'releases/vision-learning-hub-0.3.0.vsix') as archive:
    archive.extractall(root/'package')
report=PROJECT/'validation/vscode-results.json';report.parent.mkdir(exist_ok=True)
env=os.environ.copy();env.pop('ELECTRON_RUN_AS_NODE',None);env['VLH_TEST_REPORT']=str(report)
startup=None
if os.name=='nt':
    startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
command=[args.code,str(workspace),'--new-window','--disable-extensions','--disable-workspace-trust','--skip-welcome','--skip-release-notes','--user-data-dir',str(profile),'--extensionDevelopmentPath',str(root/'package/extension'),'--extensionTestsPath',str(PROJECT/'extensions/vscode/test/host.cjs')]
if args.with_debugger:
    command.remove('--disable-extensions');env['VLH_TEST_DEBUG']='1'
    installed=Path.home()/'.vscode/extensions'
    for manifest in installed.glob('*/package.json'):
        try:
            item=json.loads(manifest.read_text(encoding='utf-8'))
            identifier=item['publisher']+'.'+item['name']
            if identifier not in ('ms-python.python','ms-python.debugpy','ms-python.vscode-python-envs','ms-python.vscode-pylance'):
                command += ['--disable-extension',identifier]
        except (ValueError,KeyError):pass
with (root/'host.log').open('wb') as log:
    result=subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT,startupinfo=startup,timeout=180)
print('Isolated host:',root)
if report.exists():print(report.read_text(encoding='utf-8'))
if result.returncode:
    print((root/'host.log').read_text(encoding='utf-8',errors='replace')[-8000:])
    raise SystemExit(result.returncode)
if not report.exists():raise RuntimeError('VS Code exited without completing tests')
assert not json.loads(report.read_text()).get('error')
