"""Small deterministic supplemental inputs for the authored visual curriculum."""
import cv2
import numpy as np


def supplement(key,value,image,raw):
    params={}
    if key=='A01':params['sigma']=1.8
    elif key=='A02':params['low']=40
    elif key=='A03':params.update(corners=raw['corners'],size=raw['size'])
    elif key=='V02':params['c']=4
    elif key=='V05':
        x,y,w,h=raw['roi'];params['roi']=[min(x+value,image.shape[1]-w),y,w,h]
    elif key=='V07':
        image=np.full((200,320,3),(60,100,150),np.uint8)
        for y in range(20,180,8):
            for x in range(15,145,8):
                cv2.rectangle(image,(x,y),(x+3,y+3),(240,240,240),-1)
        cv2.circle(image,(230,95),56,(30,180,230),-1)
        cv2.line(image,(160,175),(300,25),(255,255,255),1)
        params['size']=[max(1,round(image.shape[1]*value/100)),max(1,round(image.shape[0]*value/100))]
    elif key=='V08':
        image=np.tile(np.linspace(0,255,360,dtype=np.uint8),(220,1))
        cv2.rectangle(image,(45,45),(140,170),90,-1);cv2.circle(image,(240,110),48,160,-1)
        params['gamma']=value/100
    elif key=='V09':
        yy,xx=np.mgrid[:240,:360]
        image=np.clip(35+xx*.17+yy*.04+np.random.default_rng(17).normal(0,3,(240,360)),0,255).astype(np.uint8)
        cv2.putText(image,'PART',(35,130),cv2.FONT_HERSHEY_SIMPLEX,1.6,90,2)
        cv2.rectangle(image,(230,55),(310,180),115,2)
        params['grid']=[8,8]
    elif key=='V10':params['min_area']=10
    elif key=='V12':
        image=np.random.default_rng(17).integers(75,90,(220,340),dtype=np.uint8)
        patch=np.full((40,48),175,np.uint8)
        cv2.rectangle(patch,(2,2),(45,37),40,1)
        cv2.putText(patch,'A',(8,30),cv2.FONT_HERSHEY_SIMPLEX,.9,30,2)
        cv2.circle(patch,(38,9),3,235,-1)
        image[90:130,170:218]=patch
        cv2.putText(image,'B',(30,60),cv2.FONT_HERSHEY_SIMPLEX,1.2,190,2)
        cv2.rectangle(image,(260,150),(310,195),130,2)
        params['template']=patch[value:patch.shape[0]-value,value:patch.shape[1]-value].copy()
    elif key=='V13':
        image=np.repeat(np.repeat(image,20,axis=0),3,axis=1)
        params['v_min']=100
    elif key=='V14':
        base=np.tile(np.linspace(40,70,320,dtype=np.uint8),(200,1))
        previous=base.copy();cv2.rectangle(previous,(60,60),(119,119),220,-1)
        image=(base+18).astype(np.uint8);cv2.rectangle(image,(140,60),(199,119),210,-1)
        params['previous']=previous
    if key=='P01':
        params['areas']=[20,50,79,80,81,120]
        image=np.full((200,360,3),245,np.uint8)
        for i,area in enumerate(params['areas']):
            cv2.rectangle(image,(20+i*55,170-area),(50+i*55,170),(170,100,30),-1)
            cv2.putText(image,str(i),(25+i*55,190),0,.5,(40,40,40),1)
    elif key=='P02':
        image=np.tile(np.arange(256,dtype=np.uint8),(180,1))
        params['roi']=[32,30,192,120]
    elif key=='T07':params['contours']=[c.tolist() for c in raw['contours']]
    elif key=='T08':
        image=np.full((320,460,3),245,np.uint8)
        params.update(points=raw['points'].tolist(),translation=[220,150])
    elif key=='T09':
        image=np.full((300,400,3),245,np.uint8)
        params.update(target=[80,80,240,160],layout=[[[80,80],[199,80],[199,239],[80,239]],[[200-value,80],[319-value,80],[319-value,239],[200-value,239]]])
    elif key=='T12':
        image=np.full((250,430,3),245,np.uint8)
        rng=np.random.default_rng(17);centers=np.array([[70,70],[170,90],[270,140]],float)
        frames=[]
        for i in range(7):
            frame=centers+rng.uniform(-1.5,1.5,centers.shape)
            if i==2:frame+=np.array([value,value*.5])
            frames.append(frame[rng.permutation(3)].tolist())
        params['frames']=frames
    elif key=='A04':
        image=np.full((250,420,3),245,np.uint8)
        params.update(box_a=[40,60,180,170],box_b=[90+value,90,230+value,200])
    elif key=='A05':
        image=np.full((220,360,3),245,np.uint8)
        params.update(boxes=[[40,40,140,140],[50,50,150,150],[60,60,160,160],[230,70,300,140],[230,70,300,140]],scores=[.9,.8,.7,.75,.75])
    elif key=='Y02':
        original=np.full((160,240,3),235,np.uint8)
        cv2.rectangle(original,(20,30),(120,100),(50,160,210),-1)
        cv2.circle(original,(200,125),22,(180,120,50),-1)
        scale=value/100;px,py=20,30
        resized=cv2.resize(original,None,fx=scale,fy=scale,interpolation=cv2.INTER_NEAREST)
        image=cv2.copyMakeBorder(resized,py,py,px,px,cv2.BORDER_CONSTANT,value=(50,50,50))
        boxes=np.array([[20,30,120,100],[-15,20,60,90],[180,100,270,180]],float)
        params.update(original=original,boxes=(boxes*scale+[px,py,px,py]).tolist(),scale=scale,pad=[px,py],original_size=[240,160])
    elif key=='Y03':
        image=np.full((160,360,3),245,np.uint8)
        params.update(truth=[1,1,1,1,0,0,0,0],scores=[.95,.8,.4,.2,.7,.6,.3,.1])
        for i,(truth,score) in enumerate(zip(params['truth'],params['scores'])):
            x=20+i*43;cv2.circle(image,(x,55),12,(40,140,220) if truth else (160,160,160),-1)
            cv2.putText(image,str(i),(x-5,25),0,.4,(30,30,30),1)
            cv2.putText(image,str(score),(x-12,105),0,.4,(30,30,30),1)
    elif key=='Y04':
        image=np.full((200,360,3),245,np.uint8)
        samples=[dict(group=g,split=split) for g,split in enumerate(['train','val','test']) for _ in range(2)]
        for g in range(value):samples.append(dict(group=g,split=['val','test'][g]))
        params['samples']=samples
        for i,sample in enumerate(samples):
            x=15+(i%4)*85;y=20+(i//4)*85
            cv2.rectangle(image,(x,y),(x+65,y+55),[(100,180,240),(150,210,130),(220,160,120)][sample['group']],-1)
            cv2.putText(image,f"G{sample['group']} {sample['split']}",(x,y+73),0,.35,(40,40,40),1)
    elif key=='Y05':
        image=np.full((220,380,3),245,np.uint8)
        params.update(predictions=[[40,40,90,140,.95,0],[40,40,140,140,.9,0],[210,60,310,160,.8,0],[215,60,315,160,.7,1]],truth=[[40,40,140,140,0],[210,60,310,160,1]])
    elif key=='L02':
        image=np.array([[[20,40,220],[20,200,40],[220,40,20]],[[40,60,230],[40,210,60],[230,60,40]],[[60,80,240],[60,220,80],[240,80,60]],[[80,100,250],[80,230,100],[250,100,80]]],dtype=np.uint8)
        height,width=image.shape[:2];stride=width*3+value
        buffer=np.full((height,stride),227,np.uint8);buffer[:,:width*3]=image.reshape(height,width*3)
        params.update(buffer=buffer.ravel().tolist(),height=height,width=width,stride=stride)
    elif key=='L03':
        image=np.full((240,380,3),245,np.uint8)
        frames=[[5,3,12,2],[5,3,13,2],[5,3,14,2],[5,3,14,2],[5,3,12,2],[5,3,13,2],[5,3,15,2],[5,3,15+value,2]]
        params['frames']=frames
        for i,frame in enumerate(frames):
            x=45
            for duration,color in zip(frame,[(210,170,90),(100,190,100),(80,120,230),(170,110,160)]):
                cv2.rectangle(image,(x,15+i*27),(x+duration,32+i*27),color,-1);x+=duration
            cv2.putText(image,str(i),(15,30+i*27),0,.4,(40,40,40),1)
    return image,params
