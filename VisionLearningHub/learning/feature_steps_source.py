"""Editable ordinary Python CLI sources for E07; no platform imports in exported code."""
CLI = """
if __name__ == '__main__':
    import argparse
    from pathlib import Path
    parser=argparse.ArgumentParser()
    parser.add_argument('--block',choices=['features','matches','geometry','compare','repair'],required=True)
    parser.add_argument('--input',default='data/feature_standard')
    parser.add_argument('--output',default='feature-output')
    parser.add_argument('--config',default='config.json')
    args=parser.parse_args()
    output=Path(args.output);output.mkdir(parents=True,exist_ok=True)
    run_step(args.block,Path(args.input),output,json.loads(Path(args.config).read_text(encoding='utf-8')))
"""
STARTER = '''"""E07细分练习。函数和模块由你设计，平台只读取results.json和overlays。
完整字段约定见FEATURE_STEPS.md。这里只实现当前分支即可，不必导入未完成的pipeline。
features: 模板/场景的ORB keypoints、descriptors；matches: 读取_features.json输出matches。
geometry: 读取_features.json和_matches.json，输出matrix、corners、decision、inliers、rmse。
compare: 读取_comparison.json，对每组点输出direct_matrix、robust_matrix和各自all_rmse。
repair: 修复下面故意写错的匹配逻辑，读取_repair.json输出每个case的matches。
"""
import json
import cv2
import numpy as np

def run_step(block,input_dir,output_dir,config):
    if block == 'repair':
        cases=json.loads((input_dir/'_repair.json').read_text(encoding='utf-8'))['cases']
        records=[]
        for case in cases:
            a=np.asarray(case['a'],np.uint8);b=np.asarray(case['b'],np.uint8)
            # 故障：ORB距离类型不对，而且没有处理空描述子与不足两个邻居。
            pairs=cv2.BFMatcher(cv2.NORM_L2).knnMatch(a,b,k=2)
            good=[[m.queryIdx,m.trainIdx,float(m.distance)] for m,n in pairs if m.distance<.75*n.distance]
            records.append({'file':case['file'],'matches':good})
        (output_dir/'results.json').write_text(json.dumps({'records':records}),encoding='utf-8')
        return
    raise NotImplementedError('请按FEATURE_STEPS.md实现当前分支；可创建自己的辅助模块')
'''+CLI
REFERENCE = '''import json
import cv2
import numpy as np

def read_image(path):
    image=cv2.imdecode(np.fromfile(str(path),np.uint8),cv2.IMREAD_COLOR)
    if image is None:raise ValueError('decode_failed')
    return image

def write_image(path,image):
    path.parent.mkdir(parents=True,exist_ok=True)
    ok,data=cv2.imencode('.png',image)
    if not ok:raise ValueError('encode_failed')
    data.tofile(str(path))

def points(value):
    return [cv2.KeyPoint(float(p[0]),float(p[1]),float(p[2]),float(p[3]),float(p[4]),int(p[5])) for p in value]

def extract(image):
    orb=cv2.ORB_create(nfeatures=1800,edgeThreshold=8,fastThreshold=8)
    keys,descriptors=orb.detectAndCompute(cv2.cvtColor(image,cv2.COLOR_BGR2GRAY),None)
    return {'keypoints':[[*k.pt,k.size,k.angle,k.response,k.octave] for k in keys],
            'descriptors':descriptors.tolist() if descriptors is not None else []}

def match(a,b):
    if a is None or b is None or len(a)==0 or len(b)<2:return []
    pairs=cv2.BFMatcher(cv2.NORM_HAMMING).knnMatch(np.asarray(a,np.uint8),np.asarray(b,np.uint8),k=2)
    return [[m.queryIdx,m.trainIdx,float(m.distance)] for pair in pairs if len(pair)==2 for m,n in [pair] if m.distance<.75*n.distance]

def run_step(block,input_dir,output_dir,config):
    records=[]
    if block=='repair':
        for case in json.loads((input_dir/'_repair.json').read_text(encoding='utf-8'))['cases']:
            records.append({'file':case['file'],'matches':match(case['a'],case['b'])})
    elif block=='compare':
        for case in json.loads((input_dir/'_comparison.json').read_text(encoding='utf-8'))['cases']:
            a=np.float32(case['a']);b=np.float32(case['b']);record={'file':case['file']}
            for name,method in [('direct',0),('robust',cv2.RANSAC)]:
                matrix,_=cv2.findHomography(a,b,method,3)
                projected=cv2.perspectiveTransform(a[None],matrix)[0]
                record[name+'_matrix']=matrix.tolist()
                record[name+'_all_rmse']=float(np.sqrt(np.mean(np.sum((projected-b)**2,axis=1))))
            records.append(record)
    else:
        template=read_image(input_dir/'_template.png')
        base=extract(template) if block=='features' else json.loads((input_dir/'_features.json').read_text(encoding='utf-8'))['template']
        if block!='features':lookup={v['file']:v for v in json.loads((input_dir/'_features.json').read_text(encoding='utf-8'))['records']}
        if block=='geometry':matches={v['file']:v for v in json.loads((input_dir/'_matches.json').read_text(encoding='utf-8'))['records']}
        for path in sorted(input_dir.glob('*.png')):
            if path.name.startswith('_'):continue
            try:image=read_image(path)
            except ValueError:
                records.append({'file':path.name,'error':'decode_failed'});continue
            data=extract(image) if block=='features' else lookup[path.name]
            if block=='features':
                result=data;overlay=cv2.drawKeypoints(image,points(data['keypoints']),None,color=(0,255,255))
            elif block=='matches':
                good=match(base['descriptors'],data['descriptors']);result={'matches':good}
                overlay=cv2.drawMatches(template,points(base['keypoints']),image,points(data['keypoints']),[cv2.DMatch(int(a),int(b),float(d)) for a,b,d in good],None,flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS)
            else:
                good=matches[path.name]['matches'];matrix=None;mask=[];corners=[];rmse=None;overlay=image.copy()
                if len(good)>=8:
                    a=np.float32([base['keypoints'][int(m[0])][:2] for m in good]);b=np.float32([data['keypoints'][int(m[1])][:2] for m in good])
                    candidate,inliers=cv2.findHomography(a,b,cv2.RANSAC,3)
                    if candidate is not None and inliers is not None and int(inliers.sum())>=8:
                        polygon=cv2.perspectiveTransform(np.float32([[[0,0],[199,0],[199,159],[0,159]]]),candidate)[0]
                        if np.isfinite(polygon).all() and cv2.isContourConvex(polygon) and abs(cv2.contourArea(polygon))>1000:
                            matrix=candidate;corners=polygon.tolist();mask=inliers.ravel().tolist()
                            delta=cv2.perspectiveTransform(a[None],matrix)[0]-b
                            rmse=float(np.sqrt(np.mean(np.sum(delta[np.asarray(mask,bool)]**2,axis=1))))
                            cv2.polylines(overlay,[np.int32(polygon)],True,(0,255,255),2)
                result={'matrix':matrix.tolist() if matrix is not None else None,'inliers':mask,'rmse':rmse,'corners':corners,'decision':'present' if corners else 'missing'}
            cv2.putText(overlay,block,(5,18),0,.5,(0,255,255),1)
            write_image(output_dir/'overlays'/path.name,overlay)
            records.append({'file':path.name,**result})
    payload={'records':records}
    if block=='features':payload['template']=base
    (output_dir/'results.json').write_text(json.dumps(payload,ensure_ascii=False),encoding='utf-8')
'''+CLI
