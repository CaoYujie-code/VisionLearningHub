"""Trusted course demonstrations and inert learner arrays; never execute uploaded code."""
import base64
import hashlib
import io
import json
from pathlib import Path
import time
import uuid
import zipfile

import cv2
import numpy as np

from .engine import fixture, write_image
from .walkthrough_display import validate_shape, data_preview, SPATIAL_MODES
from .walkthrough_samples import supplement

CATALOG = json.loads((Path(__file__).resolve().parents[1]/'content/walkthroughs.json').read_text(encoding='utf-8'))
SETTING = 'hub.walkthrough'


def definition(key):
    if key not in CATALOG:
        raise ValueError('本题暂未提供逐步图解；请使用函数与场景和原题练习')
    return CATALOG[key]


def revision(key):
    return hashlib.sha256(json.dumps(definition(key),ensure_ascii=False,sort_keys=True).encode()).hexdigest()[:16]


def parameter(key, value=None):
    control=definition(key)['control']
    if value is None:value=control['default']
    if type(value) is not int or value not in control['values']:raise ValueError('请选择课程列出的参数值')
    return value


def sample(key, value, folder):
    value=parameter(key,value)
    image,raw,_=fixture(key,17,folder)
    # Pass only the arguments used by the selected lesson, not unrelated fixture objects.
    image,params=supplement(key,value,image,raw)
    if key=='T02':
        x,y,w,h=raw['roi'];params['roi']=[min(x+value,image.shape[1]-w),y,w,h]
    if key=='T04':params.update(lower=raw['lower'],upper=[value,255,255])
    params[definition(key)['control']['name']]=value
    write_image(folder/'input.png',image)
    params['image_path']=str(folder/'input.png')
    return image,params


def signature(key,value,image,params=None):
    result=dict(lesson=key,revision=revision(key),parameter=value,input_sha256=hashlib.sha256(image.tobytes()).hexdigest())
    arrays={k:dict(sha256=hashlib.sha256(v.tobytes()).hexdigest(),shape=list(v.shape),dtype=str(v.dtype)) for k,v in (params or {}).items() if isinstance(v,np.ndarray)}
    if arrays:result['additional_inputs']=arrays
    return result


def display_array(value,mode):
    """Display transforms never replace raw values used by the algorithms."""
    custom=data_preview(value,mode)
    if custom is not None:return custom
    if mode=='signed':
        value=value.astype(np.float64)
        scale=max(float(np.max(np.abs(value))),1.)
        unit=np.clip(value/scale,-1,1)
        canvas=np.full((*value.shape,3),255.,np.float32)
        canvas[:,:,0]-=np.maximum(unit,0)*255
        canvas[:,:,2]-=np.maximum(-unit,0)*255
        canvas[:,:,1]-=np.abs(unit)*255
        return canvas.astype(np.uint8),f'仅预览：红=正，蓝=负，白=零；本图独立按 ±{scale:.3g} 缩放，不可跨图凭颜色比较强弱。'
    if mode=='magnitude':
        scale=max(float(np.max(value)),1.)
        return np.clip(value/scale*255,0,255).astype(np.uint8),f'仅预览：按本图最大值 {scale:.3g} 映射到 255；计算使用原始浮点幅值。'
    if value.dtype!=np.uint8:
        return np.clip(value,0,255).astype(np.uint8),'仅预览：非 uint8 数据截取到 0~255；请核对原始类型和范围。'
    return value,'原值显示；三通道按 BGR 编码为 PNG，单通道以灰度显示。'


def describe(value,mode,folder,name,detail=''):
    value=np.asarray(value)
    validate_shape(value.shape,value.dtype,mode)
    if value.size>2_000_000 or not np.isfinite(value).all():raise ValueError('步骤结果必须是有限数值，且不超过 200 万个数值')
    preview,note=display_array(value,mode)
    path=folder/(name+'.png');write_image(path,preview)
    return dict(output=str(path),shape=list(value.shape),dtype=str(value.dtype),minimum=float(value.min()),maximum=float(value.max()),nonzero=int(np.count_nonzero(value)),display_note=note,detail=detail,spatial=mode in SPATIAL_MODES,kind=mode,cells=value.tolist() if mode=='matrix' else None)


def demonstration(root,key,value=None):
    item=definition(key);value=parameter(key,value)
    folder=Path(root)/'previews'/'walkthrough'/key/(revision(key)+'-'+str(value));folder.mkdir(parents=True,exist_ok=True)
    image,params=sample(key,value,folder)
    namespace=dict(cv2=cv2,np=np,image=image.copy(),params=params)
    results={}
    for s in item['steps']:
        namespace['detail']=''
        # Code is shipped authored content. User code is never accepted here.
        exec(s['code'],namespace)
        results[s['id']]=describe(namespace[s['value']],s['display'],folder,s['id'],namespace['detail'])
    return dict(**item,revision=revision(key),parameter=value,input=describe(image,'image',folder,'input'),results=results,context=signature(key,value,image,params),parameters={k:(dict(shape=list(v.shape),dtype=str(v.dtype)) if isinstance(v,np.ndarray) else v) for k,v in params.items() if k!='image_path'})


def state(store,key):
    data=json.loads(store.setting(SETTING,'{}'))
    row=data.get(key)
    return row if row and row.get('revision')==revision(key) else dict(revision=revision(key),step=0,mode='guided',notes={},done=[],parameter=parameter(key))


def validate_progress(data):
    if not isinstance(data,dict) or any(k not in CATALOG for k in data):raise ValueError('逐步学习记录无效')
    for key,row in data.items():
        count=len(definition(key)['steps'])
        if not isinstance(row,dict) or set(row)!={'revision','step','mode','notes','done','parameter'}:raise ValueError('逐步学习字段无效')
        # Older content revisions may be restored, but state() resets their completion.
        if not isinstance(row['revision'],str) or len(row['revision'])!=16 or any(c not in '0123456789abcdef' for c in row['revision']):raise ValueError('逐步课程版本无效')
        if type(row['step']) is not int or not 0<=row['step']<count or row['mode'] not in ('guided','write'):raise ValueError('逐步位置无效')
        parameter(key,row['parameter'])
        if not isinstance(row['notes'],dict) or any(k not in {s['id'] for s in definition(key)['steps']} or not isinstance(v,str) or len(v)>4000 for k,v in row['notes'].items()):raise ValueError('观察笔记无效')
        if not isinstance(row['done'],list) or len(row['done'])>count or any(type(v) is not int or not 0<=v<count for v in row['done']) or len(set(row['done']))!=len(row['done']):raise ValueError('学习标记无效')


def save_state(store,key,row):
    validate_progress({key:row})
    if row['revision']!=revision(key):raise ValueError('课程已更新，请重新进入本题')
    data=json.loads(store.setting(SETTING,'{}'));data[key]=row
    store.set_setting(SETTING,json.dumps(data,ensure_ascii=False))
    return row


def bundle(root,key,value=None):
    """Portable lesson: same input, scaffold and opt-in reference; no platform imports."""
    item=definition(key);value=parameter(key,value)
    folder=Path(root)/'previews'/'walkthrough'/key/(revision(key)+'-'+str(value));folder.mkdir(parents=True,exist_ok=True)
    image,params=sample(key,value,folder);context=signature(key,value,image,params);params['image_path']='input.png'
    array_files={}
    for name in ('template','previous'):
        if isinstance(params.get(name),np.ndarray):
            raw=io.BytesIO();np.save(raw,params[name],allow_pickle=False)
            array_files[name+'.npy']=raw.getvalue();params[name]={'npy':name+'.npy'}
    buffer=io.BytesIO();np.save(buffer,image,allow_pickle=False)
    files={'input.npy':buffer.getvalue(),'input.png':(folder/'input.png').read_bytes(),
           'params.json':json.dumps(params,ensure_ascii=False,indent=2).encode('utf-8'),
           'context.json':json.dumps(context,ensure_ascii=False).encode('utf-8')}
    files.update(array_files)
    prelude='''from pathlib import Path
import io
import json
import zipfile
import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent
params = json.loads((ROOT / "params.json").read_text(encoding="utf-8"))
params["image_path"] = str(ROOT / "input.png")
image = np.load(ROOT / "input.npy", allow_pickle=False)
for name in ("template", "previous"):
    if name in params:
        params[name] = np.load(ROOT / params[name]["npy"], allow_pickle=False)
# 每次从头生成结果包，避免混入上次运行的旧步骤。
# 如中途报错，已写入的步骤仍可导入；未写入的步骤显示“尚未运行”。
'''
    for reference in (False,True):
        body=prelude+'\nwith zipfile.ZipFile(ROOT / "results.zip", "w", zipfile.ZIP_DEFLATED) as archive:\n    archive.write(ROOT / "context.json", "context.json")\n'
        for s in item['steps']:
            body+='\n    # '+s['id']+'：'+s['title']+'\n    # '+s['watch']+'\n'
            if reference:
                body+='\n'.join('    '+line for line in s['code'].splitlines())+'\n'
                body+=f'    raw = io.BytesIO()\n    np.save(raw, {s["value"]}, allow_pickle=False)\n    archive.writestr("{s["id"]}.npy", raw.getvalue())\n'
            else:
                body+='    # TODO：在这里手敲本步处理，暂不执行的步骤保持注释。\n'
                body+=f'    # 完成本步后，取消以下三行注释来保存变量 {s["value"]}。\n    # raw = io.BytesIO()\n    # np.save(raw, {s["value"]}, allow_pickle=False)\n    # archive.writestr("{s["id"]}.npy", raw.getvalue())\n'
        body+='\nprint("已生成", ROOT / "results.zip", "；回平台导入，查看实际保存的步骤。")\n'
        files['reference.py' if reference else 'practice.py']=body.encode('utf-8')
    lines=['# '+key+' 逐步图解与手敲实验','',item['scene'],'','目标：'+item['target'],'','适用边界：'+item['boundary'],'',
           '使用已有的 OpenCV / NumPy Python 环境。无需平台自定义函数。',
           '先编辑 practice.py，每完成一步取消该步保存代码的注释，再执行 python practice.py；在平台导入 results.zip。',
           '参考脚本需主动运行 python reference.py，会重新生成 results.zip。它是教学参考，不代表你独立完成。',
           '结果包是数据快照，平台不执行上传代码，也不据此授予题目通关。',
           '修改参数请在平台重新选择并下载另一份实验包，避免 context 与实际参数不一致。',
           '原始数组保存在结果 ZIP 的 .npy 中；图表、伪彩色和显示归一化不改变原数据。',
           'template.npy / previous.npy（若存在）分别为模板与上一帧，脚本使用 np.load 原生读取。',
           '个人代码请用 Git 或另行备份。平台学习备份不包含外部手敲脚本。','']
    for s in item['steps']:
        lines += ['## '+s['title'],'',s['why'],'','观察：'+s['watch'],'','排查：'+s['failure'],'','```python',s['code'],'```','']
        lines += ['- '+line for line in s['lines']]+['','先回答：'+s['question'],'','<details><summary>查看解释</summary>','',s['answer'],'','</details>','']
    files['README.md']='\n'.join(lines).encode('utf-8')
    return files


def files_json(root,key,value=None):
    return [dict(name=name,base64=base64.b64encode(raw).decode('ascii')) for name,raw in bundle(root,key,value).items()]


def archive_bundle(root,key,value=None):
    target=io.BytesIO()
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as archive:
        for name,raw in bundle(root,key,value).items():archive.writestr(name,raw)
    return target.getvalue()


def imported(root,key):
    path=Path(root)/'runs'/'walkthrough'/key/'latest.json'
    if not path.is_file():return None
    row=json.loads(path.read_text(encoding='utf-8'))
    row['stale']=row['revision']!=revision(key)
    for result in row['results'].values():result['output']=str(Path(root)/result['output'])
    return row


def import_results(root,key,raw):
    item=definition(key)
    if len(raw)>12*1024*1024:raise ValueError('结果包不能超过 12 MB')
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            infos=archive.infolist();names=[i.filename for i in infos]
            allowed={'context.json',*(s['id']+'.npy' for s in item['steps'])}
            if len(names)!=len(set(names)) or not set(names)<=allowed or 'context.json' not in names:raise ValueError('结果包包含未知、重复或缺失的文件')
            if sum(i.file_size for i in infos)>32*1024*1024 or any(i.file_size>16*1024*1024 for i in infos):raise ValueError('解压后的结果过大')
            if archive.getinfo('context.json').file_size>2048:raise ValueError('实验信息过大')
            context=json.loads(archive.read('context.json'))
            value=parameter(key,context.get('parameter'))
            # Compare the actual teaching input and version, never trust paths from a ZIP.
            demo=demonstration(root,key,value)
            if context!=demo['context']:raise ValueError('结果包与本题当前版本、输入或参数不匹配，请重新下载实验包')
            arrays={}
            for s in item['steps']:
                name=s['id']+'.npy'
                if name not in names:continue
                stream=io.BytesIO(archive.read(name))
                # Validate shape/type before np.load can allocate an attacker-declared array.
                ver=np.lib.format.read_magic(stream)
                if ver==(1,0):shape,_,dtype=np.lib.format.read_array_header_1_0(stream)
                elif ver==(2,0):shape,_,dtype=np.lib.format.read_array_header_2_0(stream)
                else:raise ValueError('仅支持标准 NPY 1/2 格式')
                validate_shape(shape,dtype,s['display'])
                size=1
                for n in shape:size*=n
                if size>2_000_000 or size*dtype.itemsize>16*1024*1024 or stream.tell()+size*dtype.itemsize!=len(stream.getvalue()):raise ValueError('步骤数组大小无效')
                stream.seek(0);arrays[s['id']]=np.load(stream,allow_pickle=False)
                if not np.isfinite(arrays[s['id']]).all():raise ValueError('步骤数组不能包含 NaN 或无穷大')
    except (zipfile.BadZipFile,KeyError,TypeError,AttributeError,EOFError,OverflowError,NotImplementedError,RuntimeError) as error:
        raise ValueError('结果包格式无效') from error
    folder=Path(root)/'runs'/'walkthrough'/key/uuid.uuid4().hex;folder.mkdir(parents=True,exist_ok=True)
    results={}
    for s in item['steps']:
        if s['id'] not in arrays:continue
        result=describe(arrays[s['id']],s['display'],folder,s['id'])
        # Preserve raw learner data for inspection/export, not just the PNG rendering.
        np.save(folder/(s['id']+'.npy'),arrays[s['id']],allow_pickle=False)
        result['output']=Path(result['output']).relative_to(root).as_posix()
        expected=demo['results'][s['id']]
        result['comparison']='尺寸和类型与演示相同；这不代表算法正确' if result['shape']==expected['shape'] and result['dtype']==expected['dtype'] else '尺寸或类型与演示不同，请先核对本步约定'
        results[s['id']]=result
    row=dict(revision=revision(key),parameter=value,stamp=time.time(),results=results)
    path=folder.parent/'latest.json';temp=path.with_suffix('.tmp');temp.write_text(json.dumps(row,ensure_ascii=False),encoding='utf-8');temp.replace(path)
    return imported(root,key)
