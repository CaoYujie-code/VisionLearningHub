from pathlib import Path
import math
import cv2
import numpy as np


def fixture(key,seed,folder):
    rng=np.random.default_rng(seed)
    image=np.full((300,480,3),(246,244,239),np.uint8)
    params={};truth={}
    if key=='Y01':
        valid=['0 0.5 0.5 0.2 0.4','2 0.5 0.5 1 1',' ']
        invalid=['3 0.5 0.5 0.2 0.2','0.5 0.5 0.5 0.2 0.2','1 nan 0.5 0.2 0.2',
                 '1 0.1 0.5 0.6 0.2','0 0.5 0.5 0 0.2','0 0.5 0.5 0.2']
        pairs=[(v,False) for v in valid]+[(v,True) for v in invalid]
        rng.shuffle(pairs)
        if seed==995:pairs=[]
        params=dict(labels=[p[0] for p in pairs],classes=3)
        truth['result']=[i for i,p in enumerate(pairs) if p[1]]
        for i,line in enumerate(params['labels']):
            cv2.putText(image,f'{i}: {line}',(15,28+i*27),0,.45,(65,62,53),1)
    elif key=='Y02':
        w,h=int(rng.integers(340,630)),int(rng.integers(260,440))
        image=np.full((h,w,3),(245,244,238),np.uint8)
        boxes=np.array([[20,30,180,150],[w-110,h-130,w+25,h+20],[-20,10,70,80]],float)
        if seed==995:boxes=np.empty((0,4))
        scale=float(rng.uniform(.4,1.8));pad=rng.integers(10,60,2).astype(float)
        params=dict(boxes=(boxes*scale+np.tile(pad,2)).tolist(),scale=scale,pad=pad.tolist(),original_size=[w,h])
        target=boxes.copy();target[:,[0,2]]=np.clip(target[:,[0,2]],0,w);target[:,[1,3]]=np.clip(target[:,[1,3]],0,h)
        truth['result']=target
        for box in target:cv2.rectangle(image,tuple(box[:2].astype(int)),tuple(box[2:].astype(int)),(220,225,227),-1)
    elif key=='Y03':
        a=rng.integers(0,2,17);b=rng.integers(0,2,17)
        if seed==995:a=b=np.zeros(0,dtype=int)
        tp=int(np.count_nonzero((a==1)&(b==1)));fp=int(np.count_nonzero((a==0)&(b==1)));fn=int(np.count_nonzero((a==1)&(b==0)))
        params=dict(truth=a.tolist(),predicted=b.tolist())
        truth['result']=dict(tp=tp,fp=fp,fn=fn,precision=tp/(tp+fp) if tp+fp else 0.,recall=tp/(tp+fn) if tp+fn else 0.)
        for row,values in enumerate((a,b)):
            cv2.putText(image,'TRUTH' if row==0 else 'PREDICT',(18,60+row*100),0,.6,(60,60,50),1)
            for i,v in enumerate(values):cv2.circle(image,(22+i*26,90+row*100),9,(70,150,215) if v else (190,190,180),-1)
    elif key=='L01':
        lines=['INFO camera opened','WARN frame delayed','INFO ERROR is a word in this message','ERROR read frame failed',
               'DEBUG trace ignored','ERROR model input shape mismatch','WARN retrying capture']
        rng.shuffle(lines)
        if seed==995:lines=['INFO ready','','INFO no ERROR detected']
        errors=[line[6:] for line in lines if line.startswith('ERROR ')]
        params=dict(lines=lines)
        truth['result']=dict(error_count=len(errors),warning_count=sum(line.startswith('WARN ') for line in lines),last_error=errors[-1] if errors else None)
        for i,line in enumerate(lines):cv2.putText(image,line,(15,35+i*32),0,.46,(60,65,75),1)
    else:raise KeyError(key)
    path=Path(folder)/f'input_{seed}.png';path.parent.mkdir(parents=True,exist_ok=True)
    cv2.imencode('.png',image)[1].tofile(str(path));params['image_path']=str(path)
    return image,params,truth


def check_result(key,image,params,truth,result):
    checks=[]
    def add(name,ok,detail):checks.append(dict(name=name,ok=bool(ok),detail=str(detail)))
    expected=truth['result']
    if key=='Y01':
        valid=isinstance(result,(list,tuple)) and all(isinstance(v,(int,np.integer)) and not isinstance(v,(bool,np.bool_)) for v in result)
        add('标签校验',valid and list(result)==expected,f'期望非法行下标 {expected}，得到 {result}')
    elif key=='Y02':
        arr=np.asarray(result,float)
        add('坐标形状',arr.shape==expected.shape,f'期望 {expected.shape}，得到 {arr.shape}')
        if arr.shape==expected.shape:
            error=float(np.max(np.abs(arr-expected))) if arr.size else 0.
            add('逆变换与边界',math.isfinite(error) and error<1e-6,f'最大误差 {error:.6g}')
    else:
        add('返回字典',isinstance(result,dict),'按题目要求返回字段')
        if isinstance(result,dict):
            for name,value in expected.items():
                actual=result.get(name,'字段缺失')
                numeric=isinstance(actual,(int,float,np.number)) and not isinstance(actual,(bool,np.bool_))
                ok=(numeric and math.isfinite(float(actual)) and abs(float(actual)-value)<1e-9) if isinstance(value,(int,float)) else actual==value
                add(name,ok,f'期望 {value}，得到 {actual}')
    return checks


def preview(key,image,params,result):
    out=image.copy()
    if key=='Y02':
        for box in np.asarray(result,float).reshape(-1,4):
            cv2.rectangle(out,tuple(np.rint(box[:2]).astype(int)),tuple(np.rint(box[2:]).astype(int)),(210,100,35),2)
    elif key=='Y01' and isinstance(result,(list,tuple)):
        for i in result:
            if isinstance(i,int):cv2.rectangle(out,(5,8+i*27),(470,33+i*27),(70,80,220),1)
    return out
