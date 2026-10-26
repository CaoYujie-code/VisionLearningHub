"""Deterministic, small grayscale fixtures for the visual fundamentals course."""
from pathlib import Path
import math

import cv2
import numpy as np


def fixture(key,seed,folder):
    rng=np.random.default_rng(seed)
    h,w=280,400
    yy,xx=np.mgrid[:h,:w]
    if key=='V06':
        image=np.full((h,w),65+seed%18,np.float32)
        cv2.rectangle(image,(46,38),(188,158),185+seed%32,-1)
        cv2.circle(image,(285,145),54,212-seed%24,-1)
        cv2.rectangle(image,(190,210),(345,250),168+seed%22,-1)
        image=np.clip(image+rng.normal(0,2.2,image.shape),0,255).astype(np.uint8)
    else:
        base=70+xx*.28+yy*.13+14*np.sin(yy/43)
        image=np.clip(base,0,255).astype(np.uint8)
        cv2.rectangle(image,(38,36),(157,136),226,-1)
        cv2.circle(image,(250,102),53,38,-1)
        cv2.rectangle(image,(205,188),(360,242),188,-1)
        cv2.line(image,(36,220),(365,160),242,3)
    params={};truth={}
    if key=='V01':
        if seed==995:image=np.full((h,w),128,np.uint8)
        truth['result']=np.histogram(image,bins=256,range=(0,256))[0]
    elif key=='V02':
        image=np.clip(image.astype(np.float32)+rng.normal(0,2.5,image.shape),0,255).astype(np.uint8)
        params=dict(block_size=15+4*(seed%4),c=2+seed%6)
        truth['result']=cv2.adaptiveThreshold(image,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                              cv2.THRESH_BINARY,params['block_size'],params['c'])
    elif key=='V03':
        yy_noise=rng.integers(2,h-2,1000);xx_noise=rng.integers(2,w-2,1000)
        image[yy_noise,xx_noise]=rng.choice([0,255],len(xx_noise))
        kernel=3+2*(seed%3);params=dict(kernel=kernel)
        truth['result']=cv2.medianBlur(image,kernel)
    elif key=='V04':
        kernel=3 if seed%2==0 else 5;params=dict(ksize=kernel)
        gx=cv2.Sobel(image,cv2.CV_32F,1,0,ksize=kernel)
        gy=cv2.Sobel(image,cv2.CV_32F,0,1,ksize=kernel)
        truth['result']={'gx':gx,'gy':gy,'magnitude':cv2.magnitude(gx,gy)}
    elif key=='V05':
        rw=int(rng.integers(35,100));rh=int(rng.integers(28,86))
        x=int(rng.integers(8,w-rw-8));y=int(rng.integers(8,h-rh-8))
        params['roi']=[x,y,rw,rh]
        region=image[y:y+rh,x:x+rw]
        truth['result']={'total':int(np.sum(region,dtype=np.int64)),
                         'mean':float(np.mean(region,dtype=np.float64)),
                         'count':rw*rh}
    elif key=='V06':
        threshold,mask=cv2.threshold(image,0,255,cv2.THRESH_BINARY|cv2.THRESH_OTSU)
        truth['result']={'threshold':float(threshold),'mask':mask}
    else:raise KeyError(key)
    path=Path(folder)/('input_%s.png'%seed);path.parent.mkdir(parents=True,exist_ok=True)
    ok,encoded=cv2.imencode('.png',image)
    if not ok:raise ValueError('无法生成灰度练习图')
    encoded.tofile(str(path));params['image_path']=str(path)
    return image,params,truth


def check_result(key,image,params,truth,result):
    checks=[]
    def add(name,ok,detail):checks.append(dict(name=name,ok=bool(ok),detail=str(detail)))
    expected=truth['result']
    if key=='V01':
        arr=np.asarray(result)
        shape=arr.shape==(256,);add('直方图形状',shape,f'期望 (256,)，得到 {arr.shape}')
        if shape:
            ok=np.issubdtype(arr.dtype,np.integer) and np.array_equal(arr,expected)
            add('各亮度计数',ok,f'计数总和应为 {image.size}')
    elif key in ('V02','V03'):
        valid=isinstance(result,np.ndarray) and result.shape==image.shape and result.dtype==np.uint8
        add('图像接口',valid,f'要求同尺寸 uint8 单通道数组，得到 {getattr(result,"shape",None)}')
        if valid:
            if key=='V02':add('自适应分割',np.array_equal(result,expected),'逐像素检查二值结果')
            else:add('中值滤波',np.array_equal(result,expected),'与同一窗口的中位数结果逐像素比较')
    elif key=='V04':
        add('梯度字段',isinstance(result,dict) and all(k in result for k in ('gx','gy','magnitude')),
            '需要返回 gx、gy 和 magnitude 三个数组')
        if isinstance(result,dict) and all(k in result for k in ('gx','gy','magnitude')):
            for name in ('gx','gy','magnitude'):
                try:arr=np.asarray(result[name])
                except (TypeError,ValueError):arr=np.empty((0,))
                target=expected[name]
                valid=(isinstance(result[name],np.ndarray) and arr.shape==target.shape
                       and np.issubdtype(arr.dtype,np.floating) and np.isfinite(arr).all())
                error=float(np.max(np.abs(arr-target))) if valid and arr.size else 0.
                detail=f'最大绝对误差 {error:.5g}，要求 < 0.001' if valid else '要求同尺寸、数值有限的浮点数组'
                add(name,valid and error<1e-3,detail)
    elif key=='V05':
        add('矩形统计字段',isinstance(result,dict) and all(k in result for k in expected),
            '需要返回 total、mean、count')
        if isinstance(result,dict):
            for name,target in expected.items():
                actual=result.get(name)
                numeric=isinstance(actual,(int,float,np.number)) and not isinstance(actual,(bool,np.bool_))
                valid=numeric and math.isfinite(float(actual)) and abs(float(actual)-target)<1e-8
                add(name,valid,f'期望 {target}，得到 {actual}')
    elif key=='V06':
        shape=isinstance(result,dict) and 'mask' in result and 'threshold' in result
        add('阈值结果字段',shape,'需要同时返回 threshold 和 mask')
        if shape:
            threshold=result['threshold'];mask=result['mask']
            numeric=isinstance(threshold,(int,float,np.number)) and not isinstance(threshold,(bool,np.bool_))
            add('Otsu 阈值',numeric and math.isfinite(float(threshold)) and abs(float(threshold)-expected['threshold'])<1e-5,
                f'期望 {expected["threshold"]:.5g}，得到 {threshold}')
            valid=isinstance(mask,np.ndarray) and mask.shape==image.shape and mask.dtype==np.uint8
            add('二值掩膜',valid and np.array_equal(mask,expected['mask']),'检查掩膜尺寸、类型和像素')
    return checks


def preview(key,image,params,result):
    canvas=cv2.cvtColor(image,cv2.COLOR_GRAY2BGR)
    if key=='V01':
        counts=np.asarray(result,dtype=float).reshape(-1)
        chart=np.full_like(image,246)
        peak=max(float(counts.max(initial=0)),1.)
        points=[]
        for i,value in enumerate(counts):
            x=round(i*(image.shape[1]-1)/255)
            y=image.shape[0]-1-round(float(value)/peak*(image.shape[0]-28))
            points.append([x,y])
        cv2.polylines(chart,[np.asarray(points,np.int32)],False,45,2)
        cv2.line(chart,(0,image.shape[0]-1),(image.shape[1]-1,image.shape[0]-1),120,1)
        return chart
    if key in ('V02','V03'):return result
    if key=='V04':
        magnitude=np.asarray(result['magnitude'],np.float32)
        scale=255/max(float(np.percentile(magnitude,99.5)),1.)
        return np.clip(magnitude*scale,0,255).astype(np.uint8)
    if key=='V05':
        x,y,w,h=params['roi'];cv2.rectangle(canvas,(x,y),(x+w-1,y+h-1),(30,130,230),2)
        return canvas
    if key=='V06':return result['mask']
    return canvas
