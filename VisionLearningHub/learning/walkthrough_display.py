"""Display native arrays without confusing numeric data with photographs."""
import cv2
import numpy as np

CHART_MODES={'histogram','curve','matrix'}
SPATIAL_MODES={'image','signed','magnitude','heatmap','labels'}


def validate_shape(shape,dtype,mode):
    if dtype.kind not in 'uif' or dtype.hasobject or dtype.itemsize>8:
        raise ValueError('步骤结果需要标准数值类型，不支持对象或复数')
    if not shape or any(type(n) is not int or n<=0 or n>2000 for n in shape):
        raise ValueError('步骤数组维度为空或超限')
    if mode in ('histogram','curve'):
        if tuple(shape)!=(256,):raise ValueError('直方图 / 查找表必须是长度为 256 的一维数组')
    elif mode=='matrix':
        if len(shape)!=2 or shape[0]>12 or shape[1]>8:raise ValueError('数值表最多支持 12 行、8 列')
    elif mode in ('signed','magnitude','heatmap','labels'):
        if len(shape)!=2:raise ValueError('本步骤需要二维数值数组')
        if mode=='labels' and dtype.kind not in 'ui':raise ValueError('区域标签必须是整数数组')
    elif mode=='image':
        if len(shape) not in (2,3) or (len(shape)==3 and shape[2]!=3):raise ValueError('图像步骤需要二维灰度或三通道数组')
    else:raise ValueError('未知步骤显示方式')


def data_preview(value,mode):
    if mode=='matrix':
        rows,cols=value.shape
        canvas=np.full((max(130,50+rows*42),max(260,70+cols*122),3),250,np.uint8)
        for r in range(rows):
            cv2.putText(canvas,f'r{r}',(6,65+r*42),cv2.FONT_HERSHEY_SIMPLEX,.45,(70,80,90),1)
            for c in range(cols):
                if r==0:cv2.putText(canvas,f'c{c}',(65+c*122,25),cv2.FONT_HERSHEY_SIMPLEX,.45,(70,80,90),1)
                cv2.rectangle(canvas,(53+c*122,37+r*42),(175+c*122,79+r*42),(215,220,225),1)
                cv2.putText(canvas,f'{float(value[r,c]):.5g}',(59+c*122,65+r*42),cv2.FONT_HERSHEY_SIMPLEX,.42,(40,55,80),1)
        return canvas,'数值表：r 表示行、c 表示列；图中文字保留约 5 位有效数字，精确原值见下方可展开表格。'
    if mode in ('histogram','curve'):
        canvas=np.full((310,590,3),250,np.uint8);left,top,width,height=65,35,490,225
        maximum=max(float(value.max()),1.) if mode=='histogram' else 255.
        cv2.line(canvas,(left,top),(left,top+height),(100,110,125),1)
        cv2.line(canvas,(left,top+height),(left+width,top+height),(100,110,125),1)
        for level in (0,64,128,192,255):
            x=left+round(level/255*width)
            cv2.putText(canvas,str(level),(x-10,top+height+22),cv2.FONT_HERSHEY_SIMPLEX,.4,(70,80,90),1)
        cv2.putText(canvas,f'{maximum:.4g}',(4,top+5),cv2.FONT_HERSHEY_SIMPLEX,.4,(70,80,90),1)
        cv2.putText(canvas,'0',(30,top+height),cv2.FONT_HERSHEY_SIMPLEX,.4,(70,80,90),1)
        cv2.putText(canvas,'COUNT' if mode=='histogram' else 'OUTPUT',(4,18),cv2.FONT_HERSHEY_SIMPLEX,.4,(70,80,90),1)
        cv2.putText(canvas,'INPUT GRAY',(left+180,302),cv2.FONT_HERSHEY_SIMPLEX,.45,(70,80,90),1)
        points=np.array([(left+round(i/255*width),top+height-round(float(np.clip(v/maximum,0,1))*height)) for i,v in enumerate(value)],np.int32)
        if mode=='histogram':
            for x,y in points:cv2.line(canvas,(int(x),top+height),(int(x),int(y)),(190,110,45),1)
            return canvas,f'直方图：横轴灰度 0~255，纵轴像素次数；本图纵轴上限 {maximum:.5g}，不同图的纵轴可能不同。'
        cv2.line(canvas,(left,top+height),(left+width,top),(180,185,190),1)
        cv2.polylines(canvas,[points],False,(190,110,45),2)
        return canvas,'映射曲线：横轴输入灰度、纵轴输出灰度，均为 0~255；灰线为恒等映射，超出显示范围的数值截在边界。'
    if mode=='labels':
        if value.min()<0:raise ValueError('区域标签不能为负数')
        labels=value.astype(np.uint64)
        colors=np.stack([((labels%251)*71+40)%256,((labels%251)*139+70)%256,((labels%251)*193+110)%256],axis=-1).astype(np.uint8)
        colors[labels==0]=0
        return colors,'区域标签伪彩色：黑色为背景 0，其他颜色辅助区分本次编号（编号多时可能重复），不代表类别或跨帧身份。'
    if mode=='heatmap':
        low,high=float(value.min()),float(value.max())
        unit=np.zeros(value.shape,np.uint8) if high<=low else np.clip((value.astype(float)-low)/(high-low)*255,0,255).astype(np.uint8)
        return cv2.applyColorMap(unit,cv2.COLORMAP_VIRIDIS),f'仅预览：本图原值 [{low:.5g}, {high:.5g}] 映射为暗紫→亮黄；不同图独立缩放，不能直接凭颜色比较数值。'
    return None
