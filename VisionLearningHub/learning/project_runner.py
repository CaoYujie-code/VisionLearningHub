"""Run ordinary multi-file CLI projects and assess their filesystem deliverables."""
import contextlib
import io
import json
import os
from pathlib import Path
import re
import runpy
import sys
import traceback
import cv2
import numpy as np
from .project_catalog import PROJECT_BY_ID, source_bundle
from .project_data import prepare, contact_sheet, read, write, asset_sources, ASSETS

def parse_files(code):
    files=json.loads(code) if isinstance(code,str) else code
    if not isinstance(files,dict) or not 2<=len(files)<=32:
        raise ValueError('项目需要2至32个源码/配置文件')
    for name,content in files.items():
        if not isinstance(name,str) or not (name=='config.json' or re.fullmatch(r'[a-z][a-z0-9_]{0,47}\.py',name)):
            raise ValueError('仅允许项目根目录的小写Python模块名与config.json')
        if not isinstance(content,str):raise ValueError('文件内容必须为文本')
    if not {'main.py','config.json'}<=files.keys():raise ValueError('缺少main.py或config.json')
    if len(json.dumps(files,ensure_ascii=False))>100000:raise ValueError('项目源码总量不能超过100000字符')
    return dict(sorted(files.items()))

def serialize(files):
    return json.dumps(parse_files(files),ensure_ascii=False,sort_keys=True)

def write_sources(folder,files,overwrite=False):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    for name,code in parse_files(files).items():
        path=folder/name
        if path.is_symlink() or not path.resolve().is_relative_to(folder.resolve()):raise ValueError('项目文件链接越界')
        if overwrite or not path.exists():path.write_text(code,encoding='utf-8',newline='\n')

def load_sources(folder):
    folder=Path(folder);files={}
    for path in list(folder.glob('*.py'))+[folder/'config.json']:
        if path.is_symlink() or not path.resolve().is_relative_to(folder.resolve()):raise ValueError('项目源码链接越界')
        if path.stat().st_size>400000:raise ValueError('项目文件过大')
        files[path.name]=path.read_text(encoding='utf-8-sig')
    return parse_files(files)

def project_readme(key):
    p=PROJECT_BY_ID[key]
    return '# '+p['title']+'\n\n'+p['scenario']+'\n\n## 运行\n\n```sh\npython main.py --input data/sample --output output --config config.json\n```\n\n自行安装Python、numpy、opencv-python-headless；若已有课程环境可直接使用，无需再次安装。\n\n## 交付约定\n\n'+p['output']+'\n\n## 分阶段任务\n\n'+'\n'.join(f'{i+1}. {s}' for i,s in enumerate(p['stages']))+'\n\n你可以自定义函数和根目录Python模块；main.py负责命令行入口，config.json管理参数。data/sample为公开开发样例，data/holdout为不同条件的教学验收批次；与原图同源，不是独立现场数据。\n\n## 导入自己的图片\n\n将自己的PNG图片放在新目录，用--input指定它。E02需同目录_reference.png；E04需_sequence.json记录frames(file,timestamp_ms)和line_x。平台没有自己的图片真值，不计自动通关，请人工检查输出。\n\n## 边界\n\n'+p['limits']+'\n\n图片来源见 SOURCES.json 和 ASSET_NOTICE.md。\n'

def materialize(key,folder,files,include_holdout=False):
    folder=Path(folder);write_sources(folder,files)
    for name,text in [('README.md',project_readme(key)),('requirements.txt','numpy\nopencv-python-headless>=4,<5\n'),('SOURCES.json',json.dumps(asset_sources(),ensure_ascii=False,indent=2)),('ASSET_NOTICE.md',(ASSETS/'NOTICE.md').read_text(encoding='utf-8'))]:
        path=folder/name
        if path.is_symlink():raise ValueError('项目说明文件不能是链接')
        if not path.exists():path.write_text(text,encoding='utf-8')
    data=folder/'data'
    if data.is_symlink() or not data.resolve().is_relative_to(folder.resolve()):raise ValueError('项目数据目录越界')
    sample=data/'sample'
    if sample.is_symlink() or not sample.resolve().is_relative_to(folder.resolve()):raise ValueError('项目样例目录越界')
    if not (sample/'_manifest.json').exists():prepare(key,17,sample)
    from .project_guides import guide_readme
    guide_file=folder/'GUIDED_LEARNING.md'
    if guide_file.is_symlink():raise ValueError('引导说明不能是链接')
    if not guide_file.exists():guide_file.write_text(guide_readme(key),encoding='utf-8')
    if include_holdout:
        from .project_checkpoints import export_standard
        export_standard(key,folder)
        for seed in [101,207,333,440,995]:prepare(key,seed,data/'holdout'/str(seed))

def run_main(source,input_dir,output_dir,block=None):
    source=Path(source).resolve();input_dir=Path(input_dir).resolve();output_dir=Path(output_dir).resolve()
    output_dir.mkdir(parents=True,exist_ok=True)
    names={p.stem for p in source.glob('*.py')}
    saved={k:v for k,v in sys.modules.items() if k.split('.')[0] in names}
    for name in saved:del sys.modules[name]
    cwd=Path.cwd();argv=sys.argv[:];old_path=sys.path[:]
    try:
        sys.path.insert(0,str(source));os.chdir(source)
        entry=source/('checkpoint.py' if block else 'main.py')
        sys.argv=[str(entry),'--input',str(input_dir),'--output',str(output_dir),'--config',str(source/'config.json')]
        if block:sys.argv.extend(['--block',block])
        try:runpy.run_path(str(entry),run_name='__main__')
        except SystemExit as error:
            if error.code not in (None,0):raise RuntimeError(f'工程退出码：{error.code}') from error
    finally:
        os.chdir(cwd);sys.argv=argv;sys.path[:]=old_path
        for name in list(sys.modules):
            module_file=getattr(sys.modules[name],'__file__',None)
            if name.split('.')[0] in names or (module_file and Path(module_file).resolve().is_relative_to(source)):
                sys.modules.pop(name,None)
        sys.modules.update(saved)

def output_path(root,relative):
    path=Path(root)/relative
    if not path.resolve().is_relative_to(Path(root).resolve()) or path.is_symlink():raise ValueError('输出文件路径越界')
    return path

def image_output(folder,relative):
    path=output_path(folder,relative)
    if not path.is_file() or path.stat().st_size>12*1024*1024:return None
    return cv2.imdecode(np.fromfile(str(path),np.uint8),cv2.IMREAD_COLOR)

def match_points(points,targets,tolerance):
    try:arr=np.asarray(points,dtype=float).reshape(-1,2);expected=np.asarray(targets,dtype=float).reshape(-1,2)
    except (TypeError,ValueError):return None
    if len(arr)!=len(expected) or not np.isfinite(arr).all():return None
    mapping={};used=set()
    for i,target in enumerate(expected):
        distances=[np.linalg.norm(p-target) if j not in used else np.inf for j,p in enumerate(arr)]
        j=int(np.argmin(distances))
        if distances[j]>tolerance:return None
        mapping[i]=j;used.add(j)
    return mapping

def iou(a,b):
    x,y,w,h=a;u,v,r,s=b
    if min(w,h,r,s)<=0:return 0
    intersection=max(0,min(x+w,u+r)-max(x,u))*max(0,min(y+h,v+s)-max(y,v))
    return intersection/(w*h+r*s-intersection)

def assess(key,input_dir,output_dir,truth,manifest,scope="full"):
    checks=[]
    def add(name,ok,detail):checks.append(dict(name=name,ok=bool(ok),detail=str(detail)))
    path=output_path(output_dir,'results.json')
    if not path.is_file() or path.stat().st_size>1024*1024:
        return [dict(name='批处理交付',ok=False,detail='需要写入不超过1MB的results.json')],None
    payload=json.loads(path.read_text(encoding='utf-8'))
    records=payload.get('records') if isinstance(payload,dict) else None
    if not isinstance(records,list) or not all(isinstance(r,dict) and isinstance(r.get('file'),str) for r in records):
        return [dict(name='结果协议',ok=False,detail='results.json应为含records列表的对象，每项含file')],None
    expected={k:v for k,v in truth.items() if not k.startswith('_')}
    valid=len(records)==len(expected) and {r['file'] for r in records}==set(expected)
    add('每个输入恰好一条记录',valid,f'期望 {len(expected)} 条，得到 {len(records)} 条；不允许遗漏、重复或未知文件')
    if not valid:return checks,payload
    by_file={r['file']:r for r in records};tracking={};reverse={}
    for item in manifest:
        name=item['file'];target=expected[name];record=by_file[name]
        if 'error' in target:
            add(name+' 解码失败记录',record.get('error')=='decode_failed','坏文件不能中断整个批次');continue
        overlay=image_output(output_dir,'overlays/'+Path(name).stem+'.png')
        if scope=='full':add(name+' 可视化输出',overlay is not None and list(overlay.shape)==item['shape'],'必须保存同尺寸PNG叠加图')
        if key=='E01':
            mapping=match_points(record.get('centers'),target['centers'],8)
            add(name+' 数量与定位',type(record.get('count')) is int and record['count']==len(target['centers']) and mapping is not None,f"真值 {len(target['centers'])} 个；中心误差≤8px")
        elif key=='E02':
            boxes=np.asarray(record.get('boxes'),dtype=float)
            valid=boxes.size==0 and not target['boxes']
            if boxes.ndim==2 and boxes.shape[1]==4 and len(boxes)==len(target['boxes']) and np.isfinite(boxes).all():
                used=set();valid=True
                for box in target['boxes']:
                    scores=[iou(box,b) if j not in used else -1 for j,b in enumerate(boxes)]
                    j=int(np.argmax(scores));used.add(j);valid=valid and scores[j]>=.5
            add(name+' 缺陷定位',valid,f"真值 {len(target['boxes'])} 处，IoU≥0.5，一对一匹配")
            add(name+' 放行决策',record.get('decision')==('reject' if target['boxes'] else 'accept'),'有缺陷拒收，无缺陷放行')
        elif key=='E03':
            corners=np.asarray(record.get('corners'),dtype=float)
            if not target['corners']:
                add(name+' 空场景拒绝',corners.shape==(0,),'无单据时corners应为[]');continue
            valid=corners.shape==(4,2) and np.isfinite(corners).all()
            error=float(np.max(np.linalg.norm(corners-np.asarray(target['corners']),axis=1))) if valid else float('inf')
            add(name+' 四角位置与顺序',error<=7,f'最大误差 {error:.2f}px；要求≤7px')
            if scope!='full':continue
            rectified=image_output(output_dir,'rectified/'+Path(name).stem+'.png')
            valid=rectified is not None and rectified.shape==target['rectified'].shape
            error=float(np.mean(np.abs(rectified.astype(float)-target['rectified']))) if valid else float('inf')
            add(name+' 校正图交付',valid and error<24,f'要求240×320 BGR图、平均像素误差<24；得到 {error:.2f}')
        elif key=='E04':
            objects=record.get('objects',[])
            valid=isinstance(objects,list) and all(isinstance(o,dict) and type(o.get('id')) in (int,str) for o in objects)
            mapping=match_points([o.get('center') for o in objects], [o['center'] for o in target['objects']],6) if valid else None
            add(name+' 检测定位',mapping is not None,'每个可见物体恰好一个目标，中心误差≤6px')
            consistent=mapping is not None
            if mapping is not None:
                for i,j in mapping.items():
                    identity=target['objects'][i]['identity'];actual=str(objects[j]['id'])
                    if identity in tracking and tracking[identity]!=actual:consistent=False
                    if actual in reverse and reverse[actual]!=identity:consistent=False
                    tracking[identity]=actual;reverse[actual]=identity
            if scope=='full':add(name+' 身份连续',consistent,'同物体跨帧保持ID；不同物体不得共享ID')
        elif key in ('E05','E06','E07','E08'):
            from .project_extensions import assess_extra
            add(name+' 工程算法结果',assess_extra(key,record,target),'按场景的类别、尺寸、四角或拼图身份契约比较真值')
    if key=='E04' and scope=='full':
        events=payload.get('events');expected_events=truth['_events'];used=set()
        valid=isinstance(events,list) and len(events)==len(expected_events)
        frame_names=[entry['file'] for entry in manifest]
        if valid:
            for event in events:
                if not isinstance(event,dict) or event.get('file') not in frame_names:valid=False;break
                frame=frame_names.index(event['file']);identity=reverse.get(str(event.get('id')))
                matched=next((j for j,e in enumerate(expected_events) if j not in used and e['identity']==identity and e['direction']==event.get('direction') and abs(e['frame']-frame)<=1),None)
                if matched is None:valid=False;break
                used.add(matched)
        add('双向过线事件',valid,f'期望{len(expected_events)}次真实跨线；不重复计数，事件帧允许±1')
    return checks,payload

def preview_fixture(key,seed,folder):
    folder=Path(folder);input_dir=folder/f'dataset_{seed}'
    _,manifest=prepare(key,seed,input_dir)
    path=folder/f'input_{seed}.png';contact_sheet(input_dir,manifest,path)
    image=cv2.imdecode(np.fromfile(str(path),np.uint8),cv2.IMREAD_COLOR)
    return image,dict(image_path=str(path),input_dir=str(input_dir),files=len(manifest)),{}

def execute(request):
    if request.get('project_block'):
        from .project_checkpoints import execute as execute_checkpoint
        return execute_checkpoint(request)
    from .engine import LimitedLog
    key=request['lesson'];folder=Path(request['folder']);folder.mkdir(parents=True,exist_ok=True)
    if request.get('project_custom') and (request['verify'] or key not in ('E01','E03')):raise ValueError('自有图片只能探索')
    files=parse_files(request['codes'][key]);source=folder/'source';write_sources(source,files)
    reports=[];log=LimitedLog()
    with contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
        for seed in ([101,207,333,440,995] if request['verify'] else [17]):
            case=folder/str(seed);inputs=case/'input';outputs=case/'output'
            if request.get('project_custom'):
                image=cv2.imdecode(np.fromfile(request['project_custom'],np.uint8),cv2.IMREAD_COLOR)
                if image is None:raise ValueError('上传图片不可解码')
                write(inputs/'我的图片.png',image);truth={}
                manifest=[dict(file='我的图片.png',condition='用户图片探索：没有标注真值，不计通关',shape=list(image.shape))]
            else:
                truth,manifest=prepare(key,seed,inputs)
            input_image=contact_sheet(inputs,manifest,case/'input.png')
            report=dict(seed=seed,input=input_image,output=None,checks=[],summary='',params=dict(input_dir=str(inputs),output_dir=str(outputs),files=manifest))
            try:
                run_main(source,inputs,outputs)
                if request.get('project_custom'):
                    result_file=output_path(outputs,'results.json')
                    if not result_file.is_file() or result_file.stat().st_size>1024*1024:raise ValueError('需要交付results.json')
                    payload=json.loads(result_file.read_text(encoding='utf-8'));records=payload.get('records',[])
                    valid=isinstance(records,list) and len(records)==1 and isinstance(records[0],dict) and records[0].get('file')=='我的图片.png' and 'error' not in records[0]
                    overlay=image_output(outputs,'overlays/我的图片.png')
                    checks=[dict(name='自有图片工程交付',ok=valid and overlay is not None,detail='只检查结果文件与叠加图；没有人工真值，不评价算法正确性、不计通关')]
                else:
                    checks,payload=assess(key,inputs,outputs,truth,manifest)
                report['checks']=checks
                report['summary']=json.dumps(payload,ensure_ascii=False)[:24000]
                overlays=[e for e in manifest if image_output(outputs,'overlays/'+Path(e['file']).stem+'.png') is not None]
                if overlays:report['output']=contact_sheet(outputs/'overlays',overlays,case/'output.png')
            except Exception as error:
                report.update(checks=[dict(name='工程运行与交付',ok=False,detail=f'{type(error).__name__}: {error}')],summary=traceback.format_exc(),error=dict(type=type(error).__name__,message=str(error)))
            report['passed']=bool(report['checks']) and all(c['ok'] for c in report['checks']);reports.append(report)
    return dict(lesson=key,verify=request['verify'],passed=all(r['passed'] for r in reports),reports=reports,log=log.getvalue(),input=reports[0]['input'],output=reports[0]['output'])
