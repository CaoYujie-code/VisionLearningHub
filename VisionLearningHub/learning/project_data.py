"""Small reproducible engineering batches from attributed images and explicit synthetic changes."""
from pathlib import Path
import json
import hashlib
import cv2
import numpy as np

ASSETS=Path(__file__).resolve().parents[1]/'content/engineering'
CENTERS=np.float32([[44,54],[100,55],[156,52],[216,51],[276,53],[335,43],
                   [45,125],[102,128],[153,128],[205,124],[270,119],[336,125],
                   [43,196],[102,196],[154,198],[211,193],[273,194],[347,187],
                   [45,263],[113,267],[171,261],[243,263],[300,264],[358,268]])

def read(name):
    image=cv2.imdecode(np.fromfile(str(ASSETS/name),np.uint8),cv2.IMREAD_COLOR)
    if image is None:raise ValueError('工程素材缺失：'+name)
    return image

def write(path,image):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    ok,data=cv2.imencode('.png',image)
    if not ok:raise ValueError('PNG编码失败')
    data.tofile(str(path))

def asset_sources():
    return json.loads((ASSETS/'sources.json').read_text(encoding='utf-8'))

def verify_assets():
    for asset in asset_sources():
        if hashlib.sha256((ASSETS/asset['file']).read_bytes()).hexdigest()!=asset['sha256']:
            raise ValueError('工程素材校验失败：'+asset['file'])

def prepare(key,seed,folder):
    folder=Path(folder)
    if folder.is_symlink():raise ValueError('数据目录不能是链接')
    folder.mkdir(parents=True,exist_ok=True)
    if any(p.is_symlink() for p in folder.iterdir()):raise ValueError('数据文件不能是链接')
    rng=np.random.default_rng(seed);truth={};manifest=[]
    def add(index,image,annotation,condition):
        name=f'样本_{index:02}_{seed%97:02}.png'
        write(folder/name,image);truth[name]=annotation
        manifest.append(dict(file=name,condition=condition,shape=list(image.shape)))
    if key=='E01':
        original=read('coins.png')
        for i,(start,end) in enumerate([(0,303),(85,150),(150,225)]):
            image=original[start:end].copy()
            points=CENTERS[(CENTERS[:,1]>=start)&(CENTERS[:,1]<end)].copy();points[:,1]-=start
            if seed%2==0:
                image=cv2.flip(image,1);points[:,0]=image.shape[1]-1-points[:,0]
            image=np.clip(image.astype(float)*(.95+(seed%3)*.025)+(seed%5),0,255).astype(np.uint8)
            add(i,image,dict(centers=points.tolist()),'实拍硬币裁剪/水平翻转/轻微曝光变化')
        add(3,np.full((120,180,3),50+seed%20,np.uint8),dict(centers=[]),'程序生成空工位')
    elif key=='E02':
        base=cv2.resize(read('brick.png' if seed%2 else 'gravel.png'),(320,240))
        write(folder/'_reference.png',base)
        for i in range(4):
            gradient=np.linspace(-7,7,320)[None,:,None]
            image=np.clip(base.astype(float)+(seed%13)-6+gradient,0,255).astype(np.uint8)
            masks=[]
            if i==1:
                mask=np.zeros(base.shape[:2],np.uint8)
                x,y=35+seed%17,60+seed%21;cv2.rectangle(mask,(x,y),(x+95,y+6),255,-1);masks.append(mask)
            elif i==2:
                for x,y,r in [(65+seed%20,65,15),(225,165+seed%10,21)]:
                    mask=np.zeros(base.shape[:2],np.uint8);cv2.circle(mask,(x,y),r,255,-1);masks.append(mask)
            boxes=[]
            for mask in masks:
                # Guarantee strong local contrast, independent of the photographed texture.
                image[mask>0]=np.where(base[mask>0]<128,255,0)
                yy,xx=np.nonzero(mask);boxes.append([int(xx.min()),int(yy.min()),int(xx.max()-xx.min()+1),int(yy.max()-yy.min()+1)])
            add(i,image,dict(boxes=boxes),'公开实拍纹理 + 人工缺陷/曝光梯度；已对齐模板')
    elif key=='E03':
        for i in range(4):
            background=cv2.resize(read('brick.png'),(460,380))
            background=np.clip(background.astype(float)*.25,0,255).astype(np.uint8)
            if i==3:
                add(i,background,dict(corners=[],rectified=None),'无单据的纹理桌面');continue
            paper=np.full((320,240,3),225+seed%15,np.uint8)
            cv2.putText(paper,'VISION LAB',(18,40),0,.7,(30,30,30),2)
            cv2.putText(paper,f'ORDER {seed+i}',(18,75),0,.5,(35,35,35),1)
            for line in range(7):cv2.line(paper,(20,110+line*23),(int(rng.integers(120,220)),110+line*23),(45,45,45),2)
            cv2.rectangle(paper,(175,270),(210,303),(20,20,20),3)
            corners=np.float32([[65,28],[355,45],[390,348],[42,330]])+rng.integers(-12,13,(4,2)).astype(np.float32)
            matrix=cv2.getPerspectiveTransform(np.float32([[0,0],[239,0],[239,319],[0,319]]),corners)
            warped=cv2.warpPerspective(paper,matrix,(460,380))
            mask=cv2.warpPerspective(np.full((320,240),255,np.uint8),matrix,(460,380))
            image=background.copy();image[mask>0]=warped[mask>0]
            add(i,image,dict(corners=corners.tolist(),rectified=paper),'生成的单据内容投影到公开实拍桌面纹理')
    elif key=='E04':
        raw=read('coins.png');sprite=cv2.resize(raw[231:289,17:75],(44,44))
        yy,xx=np.mgrid[:44,:44];alpha=(xx-21.5)**2+(yy-21.5)**2<21**2
        frames=[];events=[];last={};line_x=210;step=24+seed%4
        for frame in range(12):
            image=np.full((240,420,3),18,np.uint8);objects=[]
            positions=[(0,45+step*frame,52),(1,375-step*frame,125),(2,95,202)]
            if seed==995:positions=positions[2:]
            for identity,x,y in positions:
                if identity==0 and frame==4:continue
                region=image[y-22:y+22,x-22:x+22];region[alpha]=sprite[alpha]
                objects.append(dict(identity=identity,center=[x,y]))
                if identity in last and (last[identity]>line_x)!=(x>line_x):
                    events.append(dict(frame=frame,identity=identity,direction='right' if x>line_x else 'left'))
                last[identity]=x
            name=f'frame_{frame:03}.png';write(folder/name,image)
            truth[name]=dict(objects=objects)
            frames.append(dict(file=name,timestamp_ms=frame*80+(frame%3)*3))
            manifest.append(dict(file=name,condition='硬币裁片生成的双向运动/单帧缺失/静止目标',shape=list(image.shape)))
        (folder/'_sequence.json').write_text(json.dumps(dict(frames=frames,line_x=line_x),indent=2),encoding='utf-8')
        truth['_events']=events
    else:raise KeyError(key)
    if key!='E04':
        (folder/'损坏图片.png').write_bytes(b'not a PNG: intentional decoder failure')
        truth['损坏图片.png']=dict(error='decode_failed')
        manifest.append(dict(file='损坏图片.png',condition='故意损坏的文件，要求记录错误并继续'))
    (folder/'_manifest.json').write_text(json.dumps(dict(project=key,seed=seed,files=manifest,source_note='少量公开实拍图的教学变体，不是独立现场测试集'),ensure_ascii=False,indent=2),encoding='utf-8')
    return truth,manifest

def contact_sheet(folder,manifest,target):
    thumbs=[]
    for entry in manifest[:8]:
        image=cv2.imdecode(np.fromfile(str(Path(folder)/entry['file']),np.uint8),cv2.IMREAD_COLOR)
        if image is None:continue
        h,w=image.shape[:2];scale=min(220/w,160/h);small=cv2.resize(image,(round(w*scale),round(h*scale)))
        tile=np.full((190,240,3),244,np.uint8);y=(160-small.shape[0])//2+8;x=(240-small.shape[1])//2
        tile[y:y+small.shape[0],x:x+small.shape[1]]=small
        cv2.putText(tile,str(len(thumbs)+1),(12,180),0,.5,(50,50,50),1);thumbs.append(tile)
    while len(thumbs)%2:thumbs.append(np.full((190,240,3),244,np.uint8))
    canvas=np.vstack([np.hstack(thumbs[i:i+2]) for i in range(0,len(thumbs),2)])
    write(target,canvas)
    return str(target)
