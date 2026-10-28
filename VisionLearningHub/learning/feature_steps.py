"""E07 independent step contracts and checks. Submitted files, not function names, are assessed."""
import json
from pathlib import Path
import shutil
import traceback
import cv2
import numpy as np
from .feature_steps_source import STARTER,REFERENCE

IDS=('features','matches','geometry','compare','repair')
STANDARD=('matches','geometry')
CORNERS=np.float32([[0,0],[199,0],[199,159],[0,159]])
ROWS=[
 ('features','ORB关键点与描述子','先完成真实特征提取，观察目标与空场景。','results.json含template与records。每个特征对象含keypoints（N×6：[x,y,size,angle,response,octave]）和descriptors（N×32，整数0..255）。使用ORB的patchSize=31、WTA_K=2、scaleFactor=1.2、nlevels=8、edgeThreshold=8；特征数量可自定，模板和有目标图至少40点。空场景允许[]，坏图decode_failed。保存overlays/同名.png。','检查灰度、关键点与描述子逐行对应；不能用全0数组代替描述子。'),
 ('matches','Hamming匹配与筛选','独立学习二进制描述子匹配，再连接自己提取的特征。','读取_features.json。results.json的records含file和matches=[[queryIdx,trainIdx,distance],...]，完整输出Hamming最近邻通过严格ratio=0.75的匹配，不截断、不重复query。空描述子或不足2个候选返回[]，坏图原样记录。保存模板在左的横向匹配图overlays/同名.png。','ORB默认WTA_K=2用NORM_HAMMING；判断每个knn返回项长度后再取两个邻居。'),
 ('geometry','RANSAC与四角定位','用几何一致性判断目标是否存在，解释内点与误差。','读取_features.json与_matches.json。records每图含matrix（3×3或null）、corners（左上/右上/右下/左下）、decision、inliers（与匹配对应的0/1列表）、rmse（内点二维RMSE）。present至少8个内点且单点重投影误差≤4px，四角误差≤10px。missing统一matrix=null、corners=[]、inliers=[]、rmse=null。坏图decode_failed。保存overlays。','至少4点才能拟合，但本练习要求8个内点；空匹配和退化矩阵必须返回missing。'),
 ('compare','直接拟合与RANSAC对比','固定输入，比较无污染、30%和50%错误对应时的两种拟合。','读取_comparison.json的cases（file、a、b），用findHomography(method=0)与RANSAC分别拟合。records每项含file、direct_matrix、robust_matrix、direct_all_rmse、robust_all_rmse。RMSE均对全部输入对应点计算；平台另用私有四角真值评价定位，不能把全点RMSE当作定位准确率。','同一组点比较两种方法；含离群点时，鲁棒拟合的全点残差不一定更小。'),
 ('repair','维修错误的ORB匹配器','先复现距离类型与空输入故障，再修复并用边界输入检查。','读取_repair.json的cases，每项file、a、b表示两组32字节描述子，可能为空、null或只有一个候选。输出records，每项file与matches，规则同匹配块：Hamming、严格ratio=0.75。','故障代码含NORM_L2与直接解包两个邻居；先检查None、长度与距离定义，再用边界输入复测。'),
]

def blocks():
    return [dict(id=i,title=t,purpose=p,contract=c,hints=[h,'先查看失败事实，再改一个步骤；保存后重新检查当前块。'],command='feature_steps.py --block '+i,entry='feature_steps.py',standard=i in STANDARD,lesson='V12',resource='https://docs.opencv.org/4.x/dc/dc3/tutorial_py_matcher.html' if i in ('features','matches','repair') else 'https://docs.opencv.org/4.x/d1/de0/tutorial_py_feature_homography.html') for i,t,p,c,h in ROWS]

def readme():
    text='# E07独立分步练习\n\nfeature_steps.py是普通Python CLI；你可自行创建函数与模块，不导入平台库。标准上游练习不计自己的算法通过，最终仍需main.py完整验收。\n'
    for block in blocks():text+='\n## '+block['title']+'\n\n'+block['purpose']+'\n\n'+block['contract']+'\n\n    python '+block['command']+' --input data/feature_standard --output feature-output --config config.json\n'
    return text+'\nfeatures输出results.json复制为输入目录_features.json，再运行matches；matches输出复制为_matches.json，再运行geometry，即可连接自己的结果。注意不要覆盖原图。data/feature_standard包含教学上游数据以及对比/维修输入；这些内容明确是辅助输入。\n\n对比报告同时显示全点残差与独立四角误差；不能只凭一个较小数字决定方法。features/matches/geometry需保存overlays，其尺寸和存在性自动检查，关键点/连线语义需结合结果图复核。\n'

def payload(folder):
    from .project_runner import output_path
    p=output_path(folder,'results.json')
    if not p.is_file() or p.stat().st_size>8*1024*1024:raise ValueError('需要不超过8MB的results.json')
    data=json.loads(p.read_text(encoding='utf-8'))
    if not isinstance(data,dict) or not isinstance(data.get('records'),list):raise ValueError('results.json必须含records列表')
    return data

def pairs(a,b):
    if a is None or b is None or len(a)==0 or len(b)<2:return []
    raw=cv2.BFMatcher(cv2.NORM_HAMMING).knnMatch(np.asarray(a,np.uint8),np.asarray(b,np.uint8),k=2)
    return [[m.queryIdx,m.trainIdx,float(m.distance)] for v in raw if len(v)==2 for m,n in [v] if m.distance<.75*n.distance]

def prepare_experiments(inputs,seed):
    rng=np.random.default_rng(seed);cases=[];truth={}
    for i,noise in enumerate([0,.3,.5]):
        a=rng.uniform([5,5],[194,154],(60,2)).astype(np.float32)
        matrix=np.array([[1.03,.08,140+seed%17],[-.06,.95,110+seed%13],[.0002,-.0001,1]],float)
        b=cv2.perspectiveTransform(a[None],matrix)[0]+rng.normal(0,.15,a.shape)
        count=int(len(a)*noise);b[:count]=rng.uniform([0,0],[520,420],(count,2))
        name=f'outliers_{round(noise*100)}';cases.append(dict(file=name,a=a.tolist(),b=b.tolist()))
        truth[name]=cv2.perspectiveTransform(CORNERS[None],matrix)[0]
    (inputs/'_comparison.json').write_text(json.dumps(dict(cases=cases)),encoding='utf-8')
    a=rng.integers(0,256,(20,32),dtype=np.uint8);b=np.vstack([a^np.uint8(1),rng.integers(0,256,(20,32),dtype=np.uint8)])
    # L2 prefers small byte values; Hamming prefers a single changed bit in every byte.
    tricky_a=np.zeros((1,32),np.uint8);tricky_b=np.array([[128]*32,[3]*32,[7]*32],np.uint8)
    cases=[dict(file='binary_distance',a=tricky_a.tolist(),b=tricky_b.tolist()),dict(file='normal',a=a.tolist(),b=b.tolist()),dict(file='none',a=None,b=b.tolist()),dict(file='empty',a=[],b=[]),dict(file='one_neighbor',a=a.tolist(),b=b[:1].tolist())]
    (inputs/'_repair.json').write_text(json.dumps(dict(cases=cases)),encoding='utf-8')
    return truth

def validate_features(value,image,minimum):
    points=np.asarray(value.get('keypoints'),float);desc=np.asarray(value.get('descriptors'))
    if points.size==0:return minimum==0 and points.shape==(0,) and desc.shape==(0,), '空图关键点和描述子都应为[]'
    n=len(points)
    valid=points.shape==(n,6) and 40<=n<=4000 and desc.shape==(n,32) and np.isfinite(points).all() and np.issubdtype(desc.dtype,np.integer) and ((desc>=0)&(desc<=255)).all()
    if not valid:return False,f'期望40..4000个N×6关键点与N×32字节描述子；实际{points.shape}/{desc.shape}'
    valid=((points[:,0]>=0)&(points[:,0]<image.shape[1])&(points[:,1]>=0)&(points[:,1]<image.shape[0])&(points[:,2]>0)&(points[:,3]>=0)&(points[:,3]<360)&(points[:,5]>=0)&(points[:,5]<=7)&(points[:,5]%1==0)).all()
    valid=valid and len({(round(p[0],3),round(p[1],3),int(p[5])) for p in points})==n
    if not valid:return False,'关键点坐标、方向、金字塔层级越界或重复'
    keys=[cv2.KeyPoint(float(p[0]),float(p[1]),float(p[2]),float(p[3]),float(p[4]),int(p[5])) for p in points]
    _,actual=cv2.ORB_create(edgeThreshold=8).compute(cv2.cvtColor(image,cv2.COLOR_BGR2GRAY),keys)
    valid=actual is not None and actual.shape==desc.shape and np.array_equal(actual,desc)
    return bool(valid),f'{n}个关键点；按提交的位置、方向、尺度重算描述子，要求与真实图像一致'

def assess_step(block,inputs,outputs,truth,manifest,experiment_truth):
    from .project_runner import image_output,match_points
    data=payload(outputs);checks=[];facts=[]
    def add(name,ok,detail,hint=''):
        checks.append(dict(name=name,ok=bool(ok),detail=str(detail),hint=hint if not ok else ''))
    if block in ('compare','repair'):
        cases=json.loads((inputs/('_comparison.json' if block=='compare' else '_repair.json')).read_text(encoding='utf-8'))['cases'];expected={c['file']:c for c in cases}
    else:expected={k:v for k,v in truth.items() if not k.startswith('_')}
    records=data['records'];valid=all(isinstance(v,dict) and isinstance(v.get('file'),str) for v in records)
    valid=valid and len(records)==len(expected) and {v['file'] for v in records}==set(expected)
    add('每个输入恰好一条记录',valid,f'期望{len(expected)}条，实际{len(records)}条','检查是否遗漏空图/坏图、重复追加记录或混入辅助文件。')
    if not valid:return checks,facts,data
    lookup={v['file']:v for v in records}
    base=None
    if block in ('matches','geometry'):
        feature=json.loads((inputs/'_features.json').read_text(encoding='utf-8'));base=feature['template'];features={v['file']:v for v in feature['records']}
    if block=='geometry':matches={v['file']:v for v in json.loads((inputs/'_matches.json').read_text(encoding='utf-8'))['records']}
    if block=='features':
        ok,detail=validate_features(data.get('template',{}),image_output(inputs,'_template.png'),40)
        add('模板描述子对应真实图像',ok,detail,'使用灰度ORB；检查点与描述子是否仍保持同一行顺序。')
    for name,target in expected.items():
        value=lookup[name]
        if 'error' in target:
            add(name+' 坏图记录',value.get('error')=='decode_failed','要求decode_failed并继续其他输入');continue
        try:
            if block=='features':
                ok,detail=validate_features(value,image_output(inputs,name),40 if target['corners'] else 0)
                add(name+' 特征真实性',ok,detail,'核对BGR转灰度、ORB配置、dtype、关键点与描述子配对。')
                facts.append(dict(name=name+' 关键点数量',value=str(len(value.get('keypoints',[])))))
            elif block in ('matches','repair'):
                a,b=(target['a'],target['b']) if block=='repair' else (base['descriptors'],features[name]['descriptors'])
                expected_pairs=pairs(a,b);actual=value.get('matches')
                valid=isinstance(actual,list) and all(isinstance(m,list) and len(m)==3 and type(m[0]) is int and type(m[1]) is int and isinstance(m[2],(int,float)) and np.isfinite(m[2]) for m in actual)
                valid=valid and sorted(actual)==sorted(expected_pairs)
                add(name+' Hamming与ratio筛选',valid,f'应保留{len(expected_pairs)}对，实际{len(actual) if isinstance(actual,list) else "非列表"}对；完整匹配与距离逐项比对','ORB用Hamming；strict ratio=0.75；先处理None、空输入和不足两个邻居。')
                facts.append(dict(name=name+' 保留匹配',value=f'{len(actual) if isinstance(actual,list) else "?"} / 期望 {len(expected_pairs)}'))
            elif block=='geometry':
                corners=np.asarray(value.get('corners'),float);expected_corners=np.asarray(target['corners'],float)
                if not target['corners']:
                    valid=value.get('decision')=='missing' and corners.shape==(0,) and value.get('matrix') is None and value.get('rmse') is None and value.get('inliers')==[]
                    add(name+' 漏贴拒绝',valid,'无目标应返回missing、null矩阵/误差和空角点/内点','不要只用匹配数量判定存在。')
                    image=image_output(inputs,name);overlay=image_output(outputs,'overlays/'+name)
                    add(name+' 中间图交付',overlay is not None and overlay.shape==image.shape,'空场景也需交付同尺寸PNG','保存空场景图，保留拒识证据。')
                    continue
                matrix=np.asarray(value.get('matrix'),float);mask=np.asarray(value.get('inliers'));good=matches[name]['matches']
                valid=matrix.shape==(3,3) and np.isfinite(matrix).all() and abs(np.linalg.det(matrix))>1e-10 and corners.shape==(4,2) and np.isfinite(corners).all()
                if not valid:raise ValueError('需要非退化3×3矩阵和有序4×2角点')
                projected=cv2.perspectiveTransform(CORNERS[None],matrix)[0]
                error=float(np.max(np.linalg.norm(corners-expected_corners,axis=1)))
                add(name+' 四角位置与矩阵一致',value.get('decision')=='present' and error<=10 and np.max(abs(corners-projected))<.05,f'最大四角误差{error:.3f}px，要求≤10px','检查query→train方向、模板角点顺序、RANSAC矩阵及退化输入。')
                valid=mask.shape==(len(good),) and np.isin(mask,[0,1]).all() and mask.sum()>=8
                if not valid:raise ValueError('内点mask须与每对匹配对应且至少8个内点')
                a=np.float32([base['keypoints'][m[0]][:2] for m in good]);b=np.float32([features[name]['keypoints'][m[1]][:2] for m in good]);delta=cv2.perspectiveTransform(a[None],matrix)[0]-b
                residual=np.linalg.norm(delta[mask.astype(bool)],axis=1);rmse=float(np.sqrt(np.mean(residual**2)));reported=value.get('rmse')
                add(name+' 内点与重投影误差',np.max(residual)<=4 and isinstance(reported,(int,float)) and np.isfinite(reported) and abs(reported-rmse)<.03,f'重算RMSE={rmse:.3f}px；内点{int(mask.sum())}/{len(good)}','只在内点上算二维RMSE；不能直接填写0，也不要把L2范数直接除点数。')
                facts.append(dict(name=name+' 定位',value=f'四角最大误差{error:.2f}px；内点RMSE {rmse:.2f}px'))
            elif block=='compare':
                a=np.float32(target['a']);b=np.float32(target['b']);direct,_=cv2.findHomography(a,b,0)
                for method in ('direct','robust'):
                    matrix=np.asarray(value.get(method+'_matrix'),float)
                    if matrix.shape!=(3,3) or not np.isfinite(matrix).all() or abs(np.linalg.det(matrix))<1e-10:raise ValueError('对比需要两个有限非退化3×3矩阵')
                    projected=cv2.perspectiveTransform(a[None],matrix)[0];rmse=float(np.sqrt(np.mean(np.sum((projected-b)**2,axis=1))))
                    corners=cv2.perspectiveTransform(CORNERS[None],matrix)[0];error=float(np.max(np.linalg.norm(corners-experiment_truth[name],axis=1)))
                    reported=value.get(method+'_all_rmse');valid=isinstance(reported,(int,float)) and np.isfinite(reported) and abs(reported-rmse)<.03
                    if method=='direct':valid=valid and np.max(abs(projected-cv2.perspectiveTransform(a[None],direct)[0]))<.1
                    else:valid=valid and error<4
                    add(name+' '+method+'拟合与实测误差',valid,f'全点RMSE {rmse:.2f}px；独立四角最大误差 {error:.2f}px','直接拟合使用全部对应点；鲁棒拟合拒绝离群点。全点残差与独立定位误差是不同指标。')
                    facts.append(dict(name=name+' '+method,value=f'全点RMSE {rmse:.2f}px / 四角最大误差 {error:.2f}px'))
        except (ValueError,TypeError,IndexError,KeyError,cv2.error) as error:add(name+' 输出协议',False,str(error),'先核对当前任务的输入输出字段、数组尺寸和空值约定。')
        if block in ('features','matches','geometry'):
            image=image_output(inputs,name);overlay=image_output(outputs,'overlays/'+name)
            shape=(image.shape[0],image.shape[1]+(200 if block=='matches' else 0),3)
            add(name+' 中间图交付',overlay is not None and overlay.shape==shape,f'要求PNG尺寸{shape}；标注语义需目视复核','保存关键点图、模板在左的匹配连线图或四角定位图，避免覆盖原输入。')
    return checks,facts,data

def upstream(inputs,case,source,block,input_source,truth,manifest):
    from .project_runner import run_main,write_sources
    from .project_catalog import source_bundle
    upstream_source=source
    if input_source=='standard':
        upstream_source=case/'teaching';write_sources(upstream_source,source_bundle('E07',True))
    for stage in (['features'] if block=='matches' else ['features','matches'] if block=='geometry' else []):
        output=case/('upstream-'+stage);run_main(upstream_source,inputs,output,stage)
        checks,_,_=assess_step(stage,inputs,output,truth,manifest,{})
        if not all(v['ok'] for v in checks):
            first=next(v for v in checks if not v['ok'])
            raise ValueError('上游'+stage+'未通过：'+first['name']+'；'+first['detail']+'。可修复上游，或切换标准输入单独学习。')
        shutil.copyfile(output/'results.json',inputs/('_features.json' if stage=='features' else '_matches.json'))

def execute(request):
    from .engine import LimitedLog
    from .project_catalog import source_bundle
    from .project_runner import parse_files,write_sources,run_main,image_output
    from .project_data import prepare,contact_sheet,write
    from .project_guides import GUIDE_VERSION
    from .storage import fingerprint
    import contextlib
    block=request['project_block'];input_source=request.get('block_source','own');root=Path(request['folder']);source=root/'source'
    files=parse_files(request['codes']['E07']);write_sources(source,files)
    if 'feature_steps.py' not in files:raise ValueError('请先点击添加细分入口；已有源码不会覆盖')
    reports=[];log=LimitedLog()
    with contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
        for seed in (17,207):
            case=root/str(seed);inputs=case/'input';output=case/'output';truth,manifest=prepare('E07',seed,inputs)
            experiment=prepare_experiments(inputs,seed);preview=contact_sheet(inputs,manifest,case/'input.png')
            report=dict(seed=seed,input=preview,output=None,checks=[],summary='',params=dict(block=block,input_source=input_source),facts=[],artifacts=[])
            try:
                upstream(inputs,case,source,block,input_source,truth,manifest)
                run_main(source,inputs,output,block)
                checks,facts,data=assess_step(block,inputs,output,truth,manifest,experiment)
                report.update(checks=checks,facts=facts,summary=json.dumps(data,ensure_ascii=False)[:24000])
                for entry in manifest:
                    if image_output(output,'overlays/'+entry['file']) is not None:
                        report['artifacts'].append(dict(label=entry['file']+' · '+block,output=str(output/'overlays'/entry['file'])))
                if report['artifacts']:report['output']=report['artifacts'][0]['output']
            except Exception as error:
                report.update(checks=[dict(name='分步运行',ok=False,detail=str(error),hint='先检查当前分支及输入来源；允许使用标准上游数据。')],summary=traceback.format_exc(),error=dict(type=type(error).__name__,message=str(error)))
            report['passed']=bool(report['checks']) and all(v['ok'] for v in report['checks']);reports.append(report)
    return dict(lesson='E07',verify=False,passed=all(v['passed'] for v in reports),reports=reports,log=log.getvalue(),input=reports[0]['input'],output=reports[0]['output'],project_block=block,block_source=input_source,guide_version=GUIDE_VERSION,source_digest=fingerprint('E07',request['codes']))

def export_standard(folder):
    import tempfile
    from .project_data import prepare
    from .project_runner import write_sources
    from .project_catalog import source_bundle
    folder=Path(folder);destination=folder/'data/feature_standard'
    root=folder.resolve()
    for parent in (folder/'data',destination):
        if parent.is_symlink() or not parent.resolve().is_relative_to(root):raise ValueError('标准输入目录不能链接到工程外部')
    if destination.exists() and any(p.is_symlink() or not p.resolve().is_relative_to(root) for p in destination.rglob('*')):raise ValueError('标准输入含异常链接')
    if (destination/'_matches.json').exists():return
    with tempfile.TemporaryDirectory(prefix='vision-feature-') as temp:
        case=Path(temp);source=case/'source';write_sources(source,source_bundle('E07',True))
        truth,manifest=prepare('E07',17,destination);prepare_experiments(destination,17)
        upstream(destination,case,source,'geometry','own',truth,manifest)
