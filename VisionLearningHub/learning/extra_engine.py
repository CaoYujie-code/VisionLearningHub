"""基础与算法课程的可重复素材、验收及可视化；不依赖主 engine。"""
from pathlib import Path
import math
import cv2
import numpy as np


def _canvas(h=300, w=480):
    return np.full((h, w, 3), (245, 248, 250), np.uint8)


def _iou(a, b):
    left, top = max(a[0], b[0]), max(a[1], b[1])
    right, bottom = min(a[2], b[2]), min(a[3], b[3])
    intersection = max(right-left, 0)*max(bottom-top, 0)
    union = (a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-intersection
    return intersection/union if union else 0.0


def _nms(boxes, scores, threshold):
    selected = []
    for candidate in sorted(range(len(boxes)), key=lambda i: (-scores[i], i)):
        if all(_iou(boxes[candidate], boxes[chosen]) <= threshold for chosen in selected):
            selected.append(candidate)
    return selected


def _normalize(cells):
    min_r, min_c = min(p[0] for p in cells), min(p[1] for p in cells)
    return tuple(sorted((r-min_r, c-min_c) for r, c in cells))


def _rotations(piece):
    points = [tuple(cell) for cell in piece]
    shapes = set()
    for _ in range(4):
        shapes.add(_normalize(points))
        points = [(c, -r) for r, c in points]
    return shapes


def _draw_board(board, result=None):
    rows, cols = len(board), len(board[0])
    tile = min(64, 350//max(rows, cols))
    image = _canvas(rows*tile+60, cols*tile+60)
    palette = [(126,198,93), (220,159,88), (120,154,239), (229,196,132),
               (190,125,208), (107,207,207), (202,180,100), (165,209,141)]
    assigned = {}
    for placement in result or []:
        for r, c in placement["cells"]:
            assigned[(r,c)] = placement["piece"]
    for r, row in enumerate(board):
        for c, value in enumerate(row):
            x,y=30+c*tile,30+r*tile
            color = (212,220,225) if value else (65,73,81)
            if (r,c) in assigned:
                color=palette[assigned[(r,c)] % len(palette)]
            cv2.rectangle(image,(x+1,y+1),(x+tile-2,y+tile-2),color,-1)
            label = str(assigned[(r,c)]) if (r,c) in assigned else ("." if value else "X")
            cv2.putText(image,label,(x+tile//3,y+tile*2//3),cv2.FONT_HERSHEY_SIMPLEX,.6,(30,40,50),1)
    return image


def fixture(key, seed, folder):
    rng = np.random.default_rng(seed)
    image = _canvas()
    params, truth = {}, {}
    if key == "P01":
        threshold = int(rng.integers(35, 80))
        areas = [int(n) for n in rng.integers(0, 140, 9)]
        areas[1:4] = [threshold-1, threshold, threshold+1]
        if seed == 995:
            areas = []
        params = dict(areas=areas, min_area=threshold)
        truth["expected"] = [i for i, value in enumerate(areas) if value >= threshold]
        image = _draw_areas(areas, threshold)
    elif key == "P02":
        h,w = int(rng.integers(170,250)), int(rng.integers(280,440))
        image = rng.integers(0,256,(h,w),np.uint8)
        x,y = int(rng.integers(10,80)),int(rng.integers(5,35))
        rw,rh = int(rng.integers(60,150)),int(rng.integers(40,100))
        threshold=int(rng.integers(80,200))
        if seed==995:
            image[:]=threshold
            rw,rh=1,1
        params=dict(roi=[x,y,rw,rh],threshold=threshold)
        roi=image[y:y+rh,x:x+rw]
        truth["expected"]=dict(mean=float(roi.mean()),bright_count=int(np.count_nonzero(roi>threshold)),shape=[rh,rw])
    elif key == "A01":
        h,w=int(rng.integers(170,250)),int(rng.integers(280,420))
        clean=np.full((h,w),45,np.float32)
        cv2.rectangle(clean,(w//6,h//5),(w*4//5,h*4//5),210,-1)
        cv2.circle(clean,(w//2,h//2),h//6,100,-1)
        image=np.clip(clean+rng.normal(0,23,clean.shape),0,255).astype(np.uint8)
        if seed==995:
            image[:]=137
        params=dict(kernel=int(rng.choice([3,5,7])),sigma=float(rng.choice([.7,1.1,1.8])))
        truth["expected"]=cv2.GaussianBlur(image,(params["kernel"],)*2,params["sigma"],borderType=cv2.BORDER_REFLECT_101)
    elif key == "A02":
        h,w=int(rng.integers(190,270)),int(rng.integers(300,440))
        image=_canvas(h,w)
        x,y=int(rng.integers(15,50)),int(rng.integers(20,60))
        cv2.rectangle(image,(x,y),(x+110,y+100),(28,60,180),-1)
        cv2.circle(image,(w-80,h//2),45,(70,160,50),-1)
        cv2.line(image,(20,h-30),(w-20,h-40),(55,70,85),3)
        # 弱边缘及与强边缘相连的渐变边：改变双阈值确实会改变答案。
        image[h-85:]=215
        for i,contrast in enumerate((18,28,38,48,58,68,78)):
            x0=12+i*(w-65)//7
            cv2.rectangle(image,(x0,h-75),(x0+23,h-15),(215-contrast,)*3,-1)
        levels=np.linspace(10,85,70,dtype=np.uint8)
        image[h-80:h-10,w-32:w-12]=(215-levels)[:,None,None]
        if seed==995:
            image[:]=150
        params=dict(low=int(rng.integers(30,80)),high=int(rng.integers(100,180)))
        smooth=cv2.GaussianBlur(cv2.cvtColor(image,cv2.COLOR_BGR2GRAY),(3,3),1,borderType=cv2.BORDER_REFLECT_101)
        truth["expected"]=cv2.Canny(smooth,params["low"],params["high"],apertureSize=3,L2gradient=True)
    elif key == "A03":
        image=_canvas(320,460)
        corners=np.array([[50,45],[405,30],[420,270],[35,285]],np.float32)
        corners+=rng.integers(-15,16,corners.shape).astype(np.float32)
        cv2.fillConvexPoly(image,corners.astype(np.int32),(45,160,85))
        for i in range(1,6):
            a=corners[0]+(corners[1]-corners[0])*i/6
            b=corners[3]+(corners[2]-corners[3])*i/6
            cv2.line(image,tuple(a.astype(int)),tuple(b.astype(int)),(170,220,180),2)
        cv2.circle(image,(145,125),32,(35,40,225),-1)
        cv2.putText(image,"TOP",(100,85),cv2.FONT_HERSHEY_SIMPLEX,.8,(250,250,250),2)
        if seed==995:
            corners=np.array([[0,0],[459,0],[459,319],[0,319]],np.float32)
        size=[int(rng.integers(220,340)),int(rng.integers(140,240))]
        params=dict(corners=corners.tolist(),size=size)
        w,h=size
        dst=np.array([[0,0],[w-1,0],[w-1,h-1],[0,h-1]],np.float32)
        matrix=cv2.getPerspectiveTransform(corners,dst)
        truth["expected"]=cv2.warpPerspective(image,matrix,(w,h),flags=cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT,borderValue=0)
    elif key == "A04":
        x,y=float(rng.integers(40,90)),float(rng.integers(30,70))
        a=[x,y,x+140,y+110]
        b=[x+float(rng.integers(20,90)),y+30,x+190,y+150]
        if seed==207:
            b=[x+170,y+5,x+230,y+90]
        elif seed==333:
            b=list(a)
        elif seed==440:
            b=[x+140,y,x+200,y+110]
        elif seed==995:
            a=[x,y,x,y+110]
            b=list(a)
        params=dict(box_a=a,box_b=b)
        truth["expected"]=_iou(a,b)
        image=_draw_boxes(image,[a,b],None)
    elif key == "A05":
        x,y=int(rng.integers(15,55)),int(rng.integers(20,65))
        boxes=[[x,y,x+110,y+100],[x+10,y+8,x+120,y+108],
               [x+180,y+20,x+280,y+120],[x+185,y+22,x+285,y+122],
               [x+40,y+150,x+130,y+215]]
        scores=[.85,.72,.91,.64,.55]
        threshold=float(rng.choice([.3,.5,.7]))
        if seed==207:
            scores[1]=scores[0]
        elif seed==333:
            # 完全相同的框且 IoU 恰好等于阈值：严格 > 才抑制。
            boxes=[boxes[0],list(boxes[0]),boxes[2]]
            scores=[.8,.8,.7]
            threshold=1.0
        elif seed==440:
            boxes=[boxes[0],list(boxes[0]),boxes[2],boxes[4]]
            scores=[.8,.8,.9,.4]
            threshold=0.0
        elif seed==995:
            boxes,scores=[],[]
        # 在普通场景打乱原下标，避免按固定顺序输出。
        if seed not in (333,440,995):
            order=rng.permutation(len(boxes))
            boxes=[boxes[i] for i in order]
            scores=[scores[i] for i in order]
        params=dict(boxes=boxes,scores=scores,iou_threshold=threshold)
        truth["expected"]=_nms(boxes,scores,threshold)
        image=_draw_boxes(image,boxes,scores)
    elif key == "A06":
        if seed==995:
            board=[[0,1,0],[1,1,1]]
            pieces=[[[0,0],[0,1]],[[0,0],[0,1]]]
            # 删除同色棋盘格，剩余黑白数不同；两个多米诺无解。
            solvable=False
        elif seed%2:
            rows,cols=(4,6) if seed==333 else (2,3)
            board=[[1]*cols for _ in range(rows)]
            pieces=[[[0,0],[1,0],[1,1]] for _ in range(rows*cols//3)]
            solvable=True
        else:
            rows,cols=3,4
            board=[[1]*cols for _ in range(rows)]
            if seed==440:
                board[0][0]=board[0][1]=0
            pieces=[[[0,0],[0,1]] for _ in range(sum(map(sum,board))//2)]
            solvable=True
        params=dict(board=board,pieces=pieces)
        truth["solvable"]=solvable
        image=_draw_board(board)
    else:
        raise KeyError(key)
    path=Path(folder)/f"input_{seed}.png"
    path.parent.mkdir(parents=True,exist_ok=True)
    ok, encoded=cv2.imencode(".png",image)
    if not ok:
        raise ValueError("素材编码失败")
    encoded.tofile(str(path))
    params["image_path"]=str(path)
    return image,params,truth


def _draw_areas(areas, threshold, kept=None):
    image=_canvas()
    for i,area in enumerate(areas):
        x=25+i*48
        color=(40,165,85) if kept is not None and i in kept else (180,155,90)
        cv2.rectangle(image,(x,250-int(area)),(x+30,250),color,-1)
        cv2.putText(image,str(i),(x+7,275),cv2.FONT_HERSHEY_SIMPLEX,.5,(40,50,60),1)
        cv2.putText(image,str(area),(x,240-int(area)),cv2.FONT_HERSHEY_SIMPLEX,.4,(40,50,60),1)
    cv2.line(image,(15,250-int(threshold)),(465,250-int(threshold)),(60,70,210),1)
    cv2.putText(image,f"min_area={threshold}",(15,25),cv2.FONT_HERSHEY_SIMPLEX,.6,(40,50,60),1)
    return image


def _draw_boxes(image, boxes, scores, kept=None):
    image=image.copy()
    for i,box in enumerate(boxes):
        a=tuple(int(round(v)) for v in box[:2]);b=tuple(int(round(v)) for v in box[2:])
        color=(40,165,85) if kept is not None and i in kept else (190,135,65)
        cv2.rectangle(image,a,b,color,3 if kept is not None and i in kept else 1)
        label=str(i)+(f":{scores[i]:.2f}" if scores is not None else "")
        cv2.putText(image,label,(a[0],max(16,a[1]-5)),cv2.FONT_HERSHEY_SIMPLEX,.5,color,1)
    return image


def _integer(value):
    return isinstance(value,(int,np.integer)) and not isinstance(value,(bool,np.bool_))


def check_result(key, image, params, truth, result):
    checks=[]
    def add(name,ok,detail=""):
        checks.append(dict(name=name,ok=bool(ok),detail=detail))
    try:
        if key in ("P01","A05"):
            islist=isinstance(result,(list,tuple)) and all(_integer(i) for i in result)
            add("返回原始整数下标列表",islist,"不能返回布尔掩膜、分数或框坐标。")
            if islist:
                add("筛选结果和顺序",list(result)==truth["expected"],f"预期 {truth['expected']}；实际 {list(result)}")
        elif key == "P02":
            add("返回统计字典",isinstance(result,dict))
            if isinstance(result,dict):
                target=truth["expected"]
                mean=result.get("mean")
                numeric=isinstance(mean,(int,float,np.number)) and not isinstance(mean,(bool,np.bool_))
                add("ROI 平均亮度",numeric and math.isfinite(float(mean)) and abs(float(mean)-target["mean"])<1e-6,
                    f"预期 {target['mean']:.6f}；实际 {mean}")
                count=result.get("bright_count")
                add("严格大于阈值的像素数",_integer(count) and count==target["bright_count"],f"预期 {target['bright_count']}；实际 {count}")
                add("ROI 形状为高、宽",list(result.get("shape",[]))==target["shape"],f"预期 {target['shape']}")
        elif key in ("A01","A02","A03"):
            expected=truth["expected"]
            valid=isinstance(result,np.ndarray) and result.dtype==np.uint8 and result.shape==expected.shape
            add("图像尺寸和 uint8 类型",valid,f"预期 shape={expected.shape}，dtype=uint8")
            if valid:
                error=np.abs(result.astype(np.float32)-expected.astype(np.float32))
                if key=="A02":
                    add("二值边缘格式",bool(np.isin(result,[0,255]).all()))
                    add("边缘像素与约定一致",bool(np.array_equal(result,expected)),f"不同像素数 {np.count_nonzero(result!=expected)}")
                else:
                    add("像素误差",bool(error.max()<=1),f"最大误差 {error.max():.3f}；允许 1 灰度级")
        elif key=="A04":
            numeric=isinstance(result,(int,float,np.number)) and not isinstance(result,(bool,np.bool_))
            add("有限数值",numeric and math.isfinite(float(result)))
            if numeric:
                add("连续坐标 IoU",math.isfinite(float(result)) and abs(float(result)-truth["expected"])<1e-9,
                    f"预期 {truth['expected']:.9f}；实际 {result}")
        elif key=="A06":
            if not truth["solvable"]:
                add("识别无解",result is None,"面积相等仍可能无解，本样例须返回 None。")
                return checks
            valid=isinstance(result,(list,tuple))
            add("返回放置列表",valid,"有解时返回每块的 piece 下标和 cells 坐标。")
            if not valid:
                return checks
            pieces=params["pieces"]
            target={(r,c) for r,row in enumerate(params["board"]) for c,value in enumerate(row) if value==1}
            seen_ids=set();occupied=set();shapes_ok=True;unique=True;inside=True
            for entry in result:
                if not isinstance(entry,dict) or not _integer(entry.get("piece")):
                    add("放置格式",False,"每项须为包含整数 piece 的字典。")
                    return checks
                index=entry["piece"]
                if not 0<=index<len(pieces):
                    add("块下标范围",False,f"非法下标 {index}")
                    return checks
                raw=entry.get("cells")
                if not isinstance(raw,(list,tuple)) or not raw or not all(isinstance(p,(list,tuple)) and len(p)==2 and all(_integer(v) for v in p) for p in raw):
                    add("格子坐标格式",False,"cells 必须是非空的整数 [行,列] 列表。")
                    return checks
                cells={tuple(p) for p in raw}
                unique=unique and index not in seen_ids and len(cells)==len(raw) and not bool(cells&occupied)
                inside=inside and cells<=target
                shapes_ok=shapes_ok and _normalize(cells) in _rotations(pieces[index])
                occupied.update(cells);seen_ids.add(index)
            add("每块恰好使用一次",seen_ids==set(range(len(pieces))) and len(result)==len(pieces))
            add("旋转和平移保持块形状",shapes_ok,"允许旋转，禁止镜像、拉伸或改造形状。")
            add("无重叠与重复格",unique)
            add("不落到边界或禁放格",inside)
            add("完整覆盖目标",occupied==target,f"覆盖 {len(occupied & target)}/{len(target)} 个目标格")
        else:
            raise KeyError(key)
    except (TypeError,ValueError,KeyError,IndexError,OverflowError) as error:
        add("结果格式可解析",False,f"{type(error).__name__}: {error}")
    return checks


def preview(key, image, params, result):
    if key in ("A01","A02","A03"):
        if isinstance(result,np.ndarray) and result.dtype==np.uint8 and result.ndim in (2,3):
            return result
    if key=="P01" and isinstance(result,(list,tuple)):
        return _draw_areas(params["areas"],params["min_area"],result)
    if key=="P02":
        out=cv2.cvtColor(image,cv2.COLOR_GRAY2BGR)
        x,y,w,h=params["roi"]
        cv2.rectangle(out,(x,y),(x+w-1,y+h-1),(40,220,90),2)
        return out
    if key=="A04":
        out=image.copy()
        label=f"IoU = {float(result):.4f}" if isinstance(result,(int,float,np.number)) else "Invalid IoU"
        cv2.putText(out,label,(15,285),cv2.FONT_HERSHEY_SIMPLEX,.65,(40,50,60),2)
        return out
    if key=="A05" and isinstance(result,(list,tuple)):
        return _draw_boxes(_canvas(),params["boxes"],params["scores"],result)
    if key=="A06":
        if result is None:
            out=_draw_board(params["board"])
            cv2.putText(out,"NO SOLUTION",(15,22),cv2.FONT_HERSHEY_SIMPLEX,.55,(50,60,190),1)
            return out
        try:
            return _draw_board(params["board"],result)
        except (ValueError,TypeError,KeyError,IndexError):
            return image.copy()
    return image.copy()
