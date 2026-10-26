"""Deterministic fixtures and contract checks for the extended curriculum."""
from pathlib import Path
from collections import deque
import cv2
import numpy as np


def components(mask, connectivity, minimum):
    """Independent flood-fill oracle: does not rely on OpenCV component labels."""
    seen = np.zeros(mask.shape, bool)
    rows = []
    offsets = [(0,1),(0,-1),(1,0),(-1,0)]
    if connectivity == 8:
        offsets += [(1,1),(1,-1),(-1,1),(-1,-1)]
    for y, x in zip(*np.nonzero(mask)):
        if seen[y,x]:
            continue
        queue = deque([(int(y),int(x))]); seen[y,x] = True; points = []
        while queue:
            py, px = queue.popleft(); points.append((py,px))
            for dy, dx in offsets:
                ny,nx = py+dy,px+dx
                if 0 <= ny < mask.shape[0] and 0 <= nx < mask.shape[1] and mask[ny,nx] and not seen[ny,nx]:
                    seen[ny,nx] = True; queue.append((ny,nx))
        if len(points) >= minimum:
            ys,xs = zip(*points)
            rows.append([min(xs),min(ys),max(xs)-min(xs)+1,max(ys)-min(ys)+1,len(points)])
    return sorted(rows,key=lambda row:(row[1],row[0]))


def fixture(key, seed, folder):
    rng = np.random.default_rng(seed)
    image = rng.integers(0,256,(48+seed%7,72+seed%11),dtype=np.uint8)
    params = {}; truth = {}
    if key == 'V07':
        image = rng.integers(0,256,(*image.shape,3),dtype=np.uint8)
        params = dict(size=[23+seed%13,19+seed%5], mode='nearest' if seed%2 else 'area')
        result = cv2.resize(image,tuple(params['size']),interpolation=cv2.INTER_NEAREST if params['mode']=='nearest' else cv2.INTER_AREA)
    elif key == 'V08':
        image[0,:3] = [0,128,255]
        params = dict(gamma=[.4,.8,1.,1.7,2.4][seed%5])
        result = np.floor(255*(image.astype(np.float64)/255)**params['gamma']).astype(np.uint8)
    elif key == 'V09':
        image = (image//8+55).astype(np.uint8)
        params = dict(clip_limit=1.5+seed%4,grid=[3+seed%4,2+seed%3])
        result = cv2.createCLAHE(params['clip_limit'],tuple(params['grid'])).apply(image)
    elif key == 'V10':
        image = np.zeros((35,49),np.uint8)
        if seed != 995:
            image[2:6,3:8] = 255; image[6:10,8:13] = 255  # diagonal contact
            image[18:28,24:39] = 255; image[21:24,28:32] = 0  # hole
            image[0,45] = 255  # border speckle
        params = dict(connectivity=4 if seed%2 else 8,min_area=[1,20,21][seed%3])
        result = components(image,params['connectivity'],params['min_area'])
    elif key == 'V11':
        image = np.zeros((41,55),np.uint8)
        x,y,w,h = 3+seed%4,5+seed%3,13+seed%8,17+seed%5
        if seed != 995:
            image[y:y+h,x:x+w] = 255
        result = np.zeros(image.shape,np.float32)
        if seed != 995:
            yy,xx = np.mgrid[:h,:w]
            result[y:y+h,x:x+w] = np.minimum.reduce([xx+1,w-xx,yy+1,h-yy])
    elif key == 'V12':
        th,tw = 9+seed%4,11+seed%6
        template = rng.integers(0,256,(th,tw),dtype=np.uint8)
        x = int(rng.integers(0,image.shape[1]-tw+1)); y = int(rng.integers(0,image.shape[0]-th+1))
        if seed == 995:
            x,y = image.shape[1]-tw,image.shape[0]-th
        image[y:y+th,x:x+tw] = template
        params = dict(template=template)
        result = dict(top_left=[x,y])
    elif key == 'V13':
        hsv = np.zeros((8,180,3),np.uint8); hsv[:,:,0] = np.arange(180)
        hsv[:,:,1] = np.array([0,60,120,255,255,255,255,255])[:,None]
        hsv[:,:,2] = np.array([255,255,255,0,80,160,255,255])[:,None]
        image = cv2.cvtColor(hsv,cv2.COLOR_HSV2BGR)
        params = dict(hue_low=170 if seed%2 else 35,hue_high=10 if seed%2 else 90,s_min=100,v_min=100)
        # Round-trip BGR is the actual input, not the preconversion HSV array.
        h,s,v = cv2.split(cv2.cvtColor(image,cv2.COLOR_BGR2HSV))
        a,b = params['hue_low'],params['hue_high']
        chosen = ((h>=a)&(h<=b)) if a<=b else ((h>=a)|(h<=b))
        result = (chosen & (s>=100) & (v>=100)).astype(np.uint8)*255
    elif key == 'V14':
        previous = rng.integers(0,256,image.shape,dtype=np.uint8)
        threshold = 15+seed%40
        image[0,:4] = [0,255,100,100]; previous[0,:4] = [255,0,100-threshold,100]
        if seed == 995:
            previous = image.copy()
        params = dict(previous=previous,threshold=threshold)
        result = (np.abs(image.astype(np.int16)-previous.astype(np.int16))>threshold).astype(np.uint8)*255
    elif key == 'Y04':
        group = f'capture-{seed}'
        samples = [dict(group=group,split='train'),dict(group='clean',split='train'),dict(group=group,split='val'),dict(group='clean',split='train')]
        result = [group]
        if seed%2 == 0:
            samples += [dict(group='batch-b',split='val'),dict(group='batch-b',split='test')]
            result = sorted(result+['batch-b'])
        if seed == 995:
            samples = []; result = []
        rng.shuffle(samples); params = dict(samples=samples)
    elif key == 'Y05':
        # Hand-derived counts; fixtures exercise equality, class mismatch and duplicate detections.
        cases = [
            ([[0,0,10,10,.8,0],[0,0,10,10,.9,0],[20,0,30,10,.7,0]],[[0,0,10,10,0],[20,0,30,10,1]],.5,(1,2,1)),
            ([[0,0,5,10,.9,0]],[[0,0,10,10,0]],.5,(1,0,0)),
            ([[0,0,10,10,.1,0],[0,0,30,10,.9,0]],[[0,0,10,10,0],[20,0,30,10,0]],.3,(1,1,1)),
            ([[0,0,10,10,.9,0]],[],.5,(0,1,0)),
            ([],[],.5,(0,0,0)),
        ]
        index = {101:0,207:1,333:2,440:3,995:4}.get(seed,0)
        predictions,targets,threshold,counts = cases[index]
        scale = 1+seed%3; shift = seed%9
        predictions = [[*(v*scale+shift for v in row[:4]),*row[4:]] for row in predictions]
        targets = [[*(v*scale+shift for v in row[:4]),*row[4:]] for row in targets]
        params = dict(predictions=predictions,truth=targets,iou_threshold=threshold)
        result = dict(zip(('tp','fp','fn'),counts))
    elif key == 'L02':
        h,w = 6+seed%5,9+seed%4; stride = w*3+(0 if seed==995 else 1+seed%7)
        image = rng.integers(0,256,(h,w,3),dtype=np.uint8)
        buffer = np.full((h,stride),227,np.uint8); buffer[:,:w*3] = image.reshape(h,w*3)
        params = dict(buffer=buffer.reshape(-1),height=h,width=w,stride=stride)
        result = image.copy()
    elif key == 'L03':
        frames = rng.integers(1,20,(9+seed%6,4)).tolist()
        frames[-1][2] = 130+seed%23
        if seed == 995:
            frames = [[1,2,3,4]]
        totals = sorted(sum(row) for row in frames)
        mean = sum(totals)/len(totals); pos = .95*(len(totals)-1); lo = int(pos); hi = min(lo+1,len(totals)-1)
        p95 = totals[lo] + (totals[hi]-totals[lo])*(pos-lo)
        params = dict(frames=frames)
        result = dict(mean_ms=mean,p95_ms=p95,serial_fps=1000/mean)
    else:
        raise KeyError(key)
    truth['result'] = result
    path = Path(folder)/f'input_{seed}.png'; path.parent.mkdir(parents=True,exist_ok=True)
    ok,encoded = cv2.imencode('.png',image)
    if not ok:
        raise ValueError('无法生成练习图片')
    encoded.tofile(str(path)); params['image_path'] = str(path)
    return image,params,truth


def check_result(key,image,params,truth,result):
    checks = []
    def add(name, ok, detail):
        checks.append(dict(name=name,ok=bool(ok),detail=detail))
    target = truth['result']
    if isinstance(target,np.ndarray):
        valid = isinstance(result,np.ndarray) and result.shape==target.shape and result.dtype==target.dtype
        add('数组接口',valid,f'要求 shape={target.shape}、dtype={target.dtype}')
        if valid:
            same = np.allclose(result,target,atol=1e-5,rtol=0) if key=='V11' else np.array_equal(result,target)
            add('像素与数值',same,'按输入、边界和参数逐像素核验；距离图允许 1e-5 误差')
            if key=='L02':
                add('独立连续缓冲区',result.flags.c_contiguous and result.flags.owndata and not np.shares_memory(result,params['buffer']), '返回 copy 后的独立连续数组')
    elif key=='L03':
        add('统计字段',isinstance(result,dict) and all(k in result for k in target),'返回 mean_ms、p95_ms、serial_fps')
        if isinstance(result,dict):
            for name,value in target.items():
                actual = result.get(name)
                numeric = isinstance(actual,(int,float,np.number)) and not isinstance(actual,(bool,np.bool_))
                add(name,numeric and np.isfinite(actual) and abs(actual-value)<1e-7,f'期望 {value:.8g}')
    elif key=='Y05':
        valid = isinstance(result,dict) and all(isinstance(result.get(k),(int,np.integer)) and not isinstance(result.get(k),(bool,np.bool_)) for k in target)
        add('计数字段',valid,'tp、fp、fn 都须为整数')
        if valid:
            for k,v in target.items():
                add(k,result[k]==v,f'期望 {v}，得到 {result[k]}')
    else:
        valid = isinstance(result,type(target))
        add('返回类型',valid,f'要求 {type(target).__name__}')
        if valid:
            add('排序与结果',result==target,f'期望 {target}')
    return checks


def preview(key,image,params,result):
    if isinstance(result,np.ndarray):
        if key=='V11':
            return cv2.normalize(result,None,0,255,cv2.NORM_MINMAX).astype(np.uint8)
        return result
    canvas = cv2.cvtColor(image,cv2.COLOR_GRAY2BGR) if image.ndim==2 else image.copy()
    if key=='V10':
        for x,y,w,h,area in result:
            cv2.rectangle(canvas,(x,y),(x+w-1,y+h-1),(0,180,255),1)
    elif key=='V12':
        x,y = result['top_left']; h,w = params['template'].shape
        cv2.rectangle(canvas,(x,y),(x+w-1,y+h-1),(0,180,255),1)
    elif key=='Y05':
        canvas = np.full((90,120,3),245,np.uint8)
        for row in params['truth']:
            cv2.rectangle(canvas,tuple(map(int,row[:2])),tuple(map(int,row[2:4])),(40,160,40),1)
        for row in params['predictions']:
            cv2.rectangle(canvas,tuple(map(int,row[:2])),tuple(map(int,row[2:4])),(40,40,220),1)
    return canvas
