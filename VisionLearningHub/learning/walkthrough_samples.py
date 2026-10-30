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
    return image,params
