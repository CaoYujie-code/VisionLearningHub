"""Synchronize a stable release version without committing, tagging or publishing."""
import argparse
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('version',help='Stable version, for example 0.3.2')
args=parser.parse_args()
if not re.fullmatch(r'(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)',args.version):
    parser.error('Use a stable major.minor.patch version')
current=json.loads((ROOT/'extensions/vscode/package.json').read_text(encoding='utf-8'))['version']
if tuple(map(int,args.version.split('.'))) <= tuple(map(int,current.split('.'))):
    parser.error('New version must be greater than '+current)
changes={}
for name in ['package.json','package-lock.json','extensions/vscode/package.json','extensions/vscode/package-lock.json']:
    file=ROOT/name;data=json.loads(file.read_text(encoding='utf-8'));data['version']=args.version
    if 'packages' in data:data['packages']['']['version']=args.version
    changes[file]=json.dumps(data,ensure_ascii=False,indent=2)+'\n'
file=ROOT/'backend/server.py'
changes[file]=re.sub(r"'version': '[0-9]+\.[0-9]+\.[0-9]+'",f"'version': '{args.version}'",file.read_text(encoding='utf-8'))
file=ROOT/'frontend/main.tsx'
changes[file]=file.read_text(encoding='utf-8').replace('EDITION · '+current,'EDITION · '+args.version)
for file in [ROOT.parent/'README.md',ROOT/'README.md']:
    changes[file]=file.read_text(encoding='utf-8').replace('**'+current+'：','**'+args.version+'：').replace('当前版本：'+current,'当前版本：'+args.version).replace('vision-learning-hub-'+current+'.vsix','vision-learning-hub-'+args.version+'.vsix')
for file,content in changes.items():
    file.write_text(content,encoding='utf-8',newline='\n')
    print(file.relative_to(ROOT.parent))
print('Version updated. Review changes, build, test, commit, then push tag v'+args.version+'.')
