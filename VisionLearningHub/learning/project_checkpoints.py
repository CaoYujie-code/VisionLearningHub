"""Checkpoint checks run in the same bounded worker as complete projects."""
import contextlib
import json
from pathlib import Path
import shutil
import traceback
import cv2
import numpy as np
from .project_catalog import PROJECT_IDS, source_bundle
from .project_guides import BLOCK_IDS, GUIDE_VERSION
from .project_data import prepare, contact_sheet
from .project_runner import parse_files, write_sources, run_main, assess, image_output, output_path

def validate_request(key,block,source,verify,custom=False):
    if key not in PROJECT_IDS or block not in BLOCK_IDS:raise ValueError('未知工程任务块')
    if source not in ('own','standard'):raise ValueError('未知任务块输入方式')
    if source=='standard' and block!='render':raise ValueError('只有可视化任务允许标准检测结果')
    if verify!=(block=='accept') or custom:raise ValueError('任务块与正式验收/自有图片设置不兼容')

def read_payload(outputs):
    path=output_path(outputs,'results.json')
    if not path.is_file() or path.stat().st_size>1024*1024:raise ValueError('需要写入不超过1MB的results.json')
    payload=json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(payload,dict) or not isinstance(payload.get('records'),list):raise ValueError('需要records列表')
    return payload

def assess_io(inputs,outputs,manifest):
    payload=read_payload(outputs);records=payload['records'];names=[e['file'] for e in manifest]
    valid=all(isinstance(r,dict) and isinstance(r.get('file'),str) for r in records)
    valid=valid and len(records)==len(names) and {r['file'] for r in records}==set(names)
    checks=[dict(name='读写记录完整性',ok=valid,detail='每个待检文件恰好一条记录；辅助文件不能进入待检列表')]
    if not valid:return checks,payload
    lookup={r['file']:r for r in records}
    for entry in manifest:
        record=lookup[entry['file']]
        if 'shape' not in entry:
            valid=record.get('error')=='decode_failed'
        else:
            image=cv2.imdecode(np.fromfile(str(inputs/entry['file']),np.uint8),cv2.IMREAD_COLOR)
            restored=image_output(outputs,'roundtrip/'+entry['file'])
            valid=record.get('shape')==entry['shape'] and record.get('dtype')=='uint8' and restored is not None and np.array_equal(restored,image)
        checks.append(dict(name=entry['file']+' 无损读写',ok=bool(valid),detail='检查shape、uint8、像素无损回读；坏文件必须记录decode_failed'))
    return checks,payload

def assess_render(inputs,outputs,manifest,expected):
    payload=read_payload(outputs)
    checks=[dict(name='检测结果传递',ok=payload['records']==expected['records'],detail='可视化阶段保留输入records，不更改检测结论')]
    for entry in manifest:
        if 'shape' not in entry:continue
        image=cv2.imdecode(np.fromfile(str(inputs/entry['file']),np.uint8),cv2.IMREAD_COLOR)
        overlay=image_output(outputs,'overlays/'+entry['file'])
        valid=overlay is not None and overlay.shape==image.shape and np.count_nonzero(np.any(overlay!=image,axis=2))>=10
        checks.append(dict(name=entry['file']+' 可视化交付格式',ok=bool(valid),detail='同尺寸PNG且包含可见标注；标注语义与位置需结合结果图目视复核'))
    return checks,payload

def execute(request):
    from .engine import LimitedLog
    from .project_runner import execute as complete
    key=request['lesson'];block=request['project_block'];input_source=request.get('block_source','own')
    validate_request(key,block,input_source,request['verify'],bool(request.get('project_custom')))
    if block in ('batch','accept'):
        clean={k:v for k,v in request.items() if k not in ('project_block','block_source')}
        response=complete(clean)
    else:
        folder=Path(request['folder']);source=folder/'source';write_sources(source,parse_files(request['codes'][key]))
        if not (source/'checkpoint.py').is_file():raise ValueError('请在分块引导中添加checkpoint.py，或继续使用独立挑战')
        reports=[];log=LimitedLog()
        with contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
            for seed in (17,207):
                case=folder/str(seed);inputs=case/'input';outputs=case/'output'
                truth,manifest=prepare(key,seed,inputs)
                preview=contact_sheet(inputs,manifest,case/'input.png')
                report=dict(seed=seed,input=preview,output=None,checks=[],summary='',params=dict(block=block,input_source=input_source))
                try:
                    expected=None
                    if block=='render':
                        upstream=case/'upstream-output'
                        if input_source=='standard':
                            teaching=case/'teaching-reference';write_sources(teaching,source_bundle(key,True))
                            run_main(teaching,inputs,upstream)
                        else:
                            run_main(source,inputs,upstream,'detect')
                            upstream_checks,_=assess(key,inputs,upstream,truth,manifest,scope='detect')
                            if not all(c['ok'] for c in upstream_checks):raise ValueError('自己的上游检测尚未通过；请修复检测块，或切换标准输入单独学习绘图')
                        expected=read_payload(upstream)
                        (inputs/'_detections.json').write_text(json.dumps(expected,ensure_ascii=False),encoding='utf-8')
                    run_main(source,inputs,outputs,block)
                    if block=='io':checks,payload=assess_io(inputs,outputs,manifest)
                    elif block=='detect':checks,payload=assess(key,inputs,outputs,truth,manifest,scope='detect')
                    else:checks,payload=assess_render(inputs,outputs,manifest,expected)
                    report.update(checks=checks,summary=json.dumps(payload,ensure_ascii=False)[:24000])
                    image_folder=outputs/('roundtrip' if block=='io' else 'overlays')
                    available=[e for e in manifest if image_output(image_folder,e['file']) is not None]
                    if available:report['output']=contact_sheet(image_folder,available,case/'output.png')
                except Exception as error:
                    report.update(checks=[dict(name='任务块运行',ok=False,detail=f'{type(error).__name__}: {error}')],summary=traceback.format_exc(),error=dict(type=type(error).__name__,message=str(error)))
                report['passed']=bool(report['checks']) and all(c['ok'] for c in report['checks']);reports.append(report)
        response=dict(lesson=key,verify=False,passed=all(r['passed'] for r in reports),reports=reports,log=log.getvalue(),input=reports[0]['input'],output=reports[0]['output'])
    response.update(project_block=block,block_source=input_source,guide_version=GUIDE_VERSION)
    return response

def export_standard(key,folder):
    """Provide labelled teaching input for standalone render practice, without overwriting files."""
    import tempfile
    folder=Path(folder);destination=folder/'data'/'standard'
    if destination.exists():return
    destination.mkdir(parents=True)
    with tempfile.TemporaryDirectory(prefix='vision-guide-') as temporary:
        root=Path(temporary);source=root/'source';write_sources(source,source_bundle(key,True))
        prepare(key,17,destination);run_main(source,destination,root/'output')
        shutil.copyfile(root/'output/results.json',destination/'_detections.json')
