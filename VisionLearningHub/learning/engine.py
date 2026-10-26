"""学生代码工作进程、可重复的素材与基于几何真值的验收。"""
import contextlib
import copy
import io
import json
import math
import re
import sys
import traceback
from pathlib import Path

import cv2
import numpy as np
from . import extra_engine
from .extra_lessons import EXTRA_IDS
from .domain_lessons import DOMAIN_IDS
from . import domain_engine
from .vision_lessons import VISION_IDS
from . import vision_engine


def read_image(path):
    image = cv2.imdecode(np.fromfile(str(path), np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("无法读取图片，请选择 PNG 或 JPEG 图片")
    return image


def write_image(path, image):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    ok, data = cv2.imencode(".png", image)
    if not ok:
        raise ValueError("图片保存失败")
    data.tofile(str(path))


def json_value(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    raise TypeError(str(type(value)))


def scene(seed, empty=False):
    rng = np.random.default_rng(seed)
    image = np.full((420, 640, 3), (42, 145, 48), np.uint8)
    mask = np.zeros((420, 640), np.uint8)
    polys = []
    n = 0 if empty else (3 if seed % 3 == 0 else 4)
    for i in range(n):
        shape = (np.array([[0,0],[82,0],[82,58],[0,58]],float) if i % 2 == 0
                 else np.array([[0,0],[78,4],[85,42],[38,66],[-6,40]],float))
        shape -= shape.mean(axis=0)
        angle = rng.uniform(-0.35,0.35)
        r = np.array([[math.cos(angle),-math.sin(angle)],[math.sin(angle),math.cos(angle)]])
        center = np.array([150+(i%2)*300,110+(i//2)*200])+rng.integers(-22,23,2)
        poly = np.rint(shape@r.T+center).astype(np.int32)
        polys.append(poly)
        cv2.fillPoly(mask,[poly],255)
        cv2.fillPoly(image,[poly],(239,241,243))
        cv2.putText(image,str(i+1),tuple((center-12).astype(int)),cv2.FONT_HERSHEY_SIMPLEX,.65,(18,18,18),2)
        cv2.circle(image,tuple((center+[14,12]).astype(int)),7,(30,35,205),-1)
    return image, mask, polys


def layout_metrics(image, layout, target):
    count = np.zeros(image.shape[:2],np.int32)
    for points in layout:
        mask = np.zeros(image.shape[:2],np.uint8)
        cv2.fillPoly(mask,[np.rint(points).astype(np.int32)],1)
        count += mask
    x,y,w,h = target
    return dict(coverage=float(np.count_nonzero(count[y:y+h,x:x+w])/(w*h)),
                overlap=float(np.count_nonzero(count>1)/(w*h)))


def fixture(key, seed, folder, custom=None):
    if key in VISION_IDS:return vision_engine.fixture(key,seed,folder)
    if key in DOMAIN_IDS:return domain_engine.fixture(key,seed,folder)
    if key in EXTRA_IDS:return extra_engine.fixture(key,seed,folder)
    rng = np.random.default_rng(seed)
    image, mask, polys = scene(seed, empty=(seed==995))
    if custom:
        image = read_image(custom)
        h,w = image.shape[:2]
        if max(h,w)>1600:
            image=cv2.resize(image,None,fx=1600/max(h,w),fy=1600/max(h,w))
    elif key in ("T01","T02","T03"):
        # 读图和裁剪必须实际使用输入，不能靠记住固定尺寸或坐标通过。
        h,w=int(rng.integers(260,500)),int(rng.integers(400,780))
        image=cv2.resize(image,(w,h))
        image[0,0]=rng.integers(0,256,3,dtype=np.uint8)
        if key=="T03":
            ramp=np.linspace(0,255,w,dtype=np.uint8)
            image[h//2:]=np.broadcast_to(ramp[None,:,None],(h-h//2,w,3))
    h,w = image.shape[:2]
    params = dict(lower=[30,35,15],upper=[95,255,255],threshold=110+seed%70,
                  min_area=150,kernel=3,roi=[w//8,h//8,w//2,h//2])
    if key=="T02":
        params["roi"]=[int(rng.integers(0,max(1,w//3))),int(rng.integers(0,max(1,h//3))),
                       int(rng.integers(max(1,w//4),max(2,w//2))),
                       int(rng.integers(max(1,h//4),max(2,h//2)))]
    expected = {"mask":mask,"polys":polys}
    contours,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    params["contours"]=contours
    if key=="T05":
        image=mask.copy()
        yy=rng.integers(5,h-5,180);xx=rng.integers(5,w-5,180)
        image[yy,xx]=255-image[yy,xx]
    elif key=="T06":
        image=mask.copy()
        cv2.circle(image,(20,20),2,255,-1)
    elif key=="T08":
        points=np.array([[10,12],[80,15],[75,65],[20,70]],float)
        angle=float(rng.uniform(-175,175)); translation=rng.integers(80,200,2)
        params.update(points=points,angle=angle,translation=translation)
        rad=np.deg2rad(angle)
        matrix=np.array([[np.cos(rad),-np.sin(rad)],[np.sin(rad),np.cos(rad)]])
        expected["points"]=points@matrix.T+translation
    elif key in ("T09","T10"):
        target=[80,80,240,160]
        a=np.array([[80,80],[199,80],[199,239],[80,239]])
        b=np.array([[200,80],[319,80],[319,239],[200,239]])
        valid=[a,b]
        bad=[a,b+[-42,0]]
        gap=[a,b+[28,0]]
        candidates=[valid,bad,gap]
        if seed%5==0:
            candidates=[bad,gap]
        rng.shuffle(candidates)
        params.update(target=target,candidates=candidates,layout=candidates[seed%len(candidates)])
    elif key=="T11":
        templates=[]
        for i in range(4):
            tile=np.full((48,48),235,np.uint8)
            cv2.putText(tile,str(i+2),(7,35),cv2.FONT_HERSHEY_SIMPLEX,1.1,20,2)
            cv2.rectangle(tile,(3,3),(12+i*5,8),40,-1)
            templates.append(tile)
        order=rng.permutation(4).tolist()
        patches=[np.rot90(templates[i],int(rng.integers(4))).copy() for i in order]
        params.update(templates=templates,patches=patches)
        expected["identities"]=order
        image=np.full((200,360,3),245,np.uint8)
        for i,(t,patch) in enumerate(zip(templates,patches)):
            for y,tile in ((30,t),(120,patch)):
                image[y:y+48,15+i*85:63+i*85]=cv2.cvtColor(tile,cv2.COLOR_GRAY2BGR)
            cv2.putText(image,str(i),(15+i*85,22),0,.5,(50,50,50),1)
    elif key=="T12":
        centers=np.array([[90,90],[240,170],[420,110],[550,280]],float)
        frames=[]
        for i in range(9):
            frame=centers+rng.uniform(-1.8,1.8,centers.shape)
            if i==2: frame+=np.array([15,-15])
            frames.append(frame[rng.permutation(4)].tolist())
        params["frames"]=frames
        expected["centers"]=centers
    elif key=="T13":
        visual=np.array([[0,0],[600,0],[0,400],[600,400],[250,150],[430,280]],float)
        if seed==995:
            visual=np.array([[i*50,i*20] for i in range(6)],float)
            expected["degenerate"]=True
        affine=np.array([[.25,-.02],[.04,.32],[10,24]])
        platform=np.column_stack([visual,np.ones(6)])@affine
        checks=rng.uniform([20,20],[580,380],(5,2))
        params.update(visual=visual,platform=platform,checks=checks)
        expected["points"]=np.column_stack([checks,np.ones(5)])@affine
    source=Path(folder)/("input_%s.png"%seed)
    write_image(source,image)
    params["image_path"]=str(source)
    return image,params,expected


def check_result(key, image, params, truth, result):
    if key in VISION_IDS:return vision_engine.check_result(key,image,params,truth,result)
    if key in DOMAIN_IDS:return domain_engine.check_result(key,image,params,truth,result)
    if key in EXTRA_IDS:return extra_engine.check_result(key,image,params,truth,result)
    checks=[]
    def check(name,ok,detail):
        checks.append(dict(name=name,ok=bool(ok),detail=str(detail)))
    def mask_check(value,target):
        check("掩膜接口",isinstance(value,np.ndarray) and value.shape==target.shape
              and value.dtype==np.uint8,"要求同尺寸 uint8 单通道数组")
        if not checks[-1]["ok"]: return
        check("二值取值",np.all(np.isin(value,[0,255])),"只允许 0 / 255")
        a=value>0;b=target>0
        union=np.count_nonzero(a|b)
        iou=np.count_nonzero(a&b)/union if union else 1.0
        check("区域重合 IoU",iou>=.96,f"{iou:.4f} / 要求 ≥ 0.96（教学素材）")
    def match_centers(items, detailed):
        truth_contours,_=cv2.findContours(truth["mask"],cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        check("碎片数量",len(items)==len(truth_contours),f"得到 {len(items)}，期望 {len(truth_contours)}")
        if len(items)!=len(truth_contours): return
        used=set()
        for c in truth_contours:
            m=cv2.moments(c); center=np.array([m["m10"]/m["m00"],m["m01"]/m["m00"]])
            costs=[np.linalg.norm(np.asarray(item["center"],float)-center) if i not in used else np.inf
                   for i,item in enumerate(items)]
            j=int(np.argmin(costs));used.add(j)
            check(f"碎片 {len(used)} 中心",costs[j]<=3,f"误差 {costs[j]:.2f} px，允许 3 px")
            if detailed:
                pts=np.asarray(items[j]["points"],float).reshape(-1,2)
                target=cv2.approxPolyDP(c,.018*cv2.arcLength(c,True),True).reshape(-1,2)
                if len(pts)!=len(target):
                    check("顶点数量",False,f"得到 {len(pts)}，期望 {len(target)}")
                else:
                    errors=[]
                    for order in (pts,pts[::-1]):
                        for shift in range(len(pts)):
                            errors.append(np.max(np.linalg.norm(np.roll(order,shift,axis=0)-target,axis=1)))
                    error=min(errors)
                    check("角点几何",error<=4,f"匹配后的最大误差 {error:.2f} px，允许 4 px")
                area=abs(float(items[j]["area"])); target_area=cv2.contourArea(c)
                check("面积",abs(area-target_area)<=max(5,target_area*.03),
                      f"{area:.1f} / 参考 {target_area:.1f}")
    if key=="T01":
        h,w,c=image.shape
        for name,expected in dict(width=w,height=h,channels=c,pixel=image[0,0].tolist()).items():
            check(name,result.get(name)==expected,f"得到 {result.get(name)}，期望 {expected}")
    elif key=="T02":
        x,y,w,h=params["roi"];target=image[y:y+h,x:x+w]
        check("ROI 内容",isinstance(result,np.ndarray) and np.array_equal(result,target),
              f"要求尺寸 {target.shape}，内容与指定工作区一致")
    elif key=="T03":
        gray=cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)
        mask_check(result,np.where(gray>params["threshold"],255,0).astype(np.uint8))
    elif key in ("T04","T05"):
        mask_check(result,truth["mask"])
    elif key=="T06":
        items=[]
        for c in result:
            c=np.asarray(c,np.float32).reshape(-1,1,2);m=cv2.moments(c)
            if abs(m["m00"])<1e-9: raise ValueError("返回了零面积轮廓")
            items.append(dict(center=[m["m10"]/m["m00"],m["m01"]/m["m00"]]))
        match_centers(items,False)
        predicted=np.zeros_like(truth["mask"])
        for c in result: cv2.fillPoly(predicted,[np.rint(c).astype(np.int32)],255)
        mask_check(predicted,truth["mask"])
    elif key=="T07":
        match_centers(result,True)
    elif key in ("T08","T13"):
        target=truth["points"];arr=np.asarray(result,float)
        check("输出尺寸",arr.shape==target.shape,f"期望 {target.shape}，得到 {arr.shape}")
        if arr.shape==target.shape:
            error=float(np.max(np.linalg.norm(arr-target,axis=1)))
            check("独立点误差",np.isfinite(error) and error<1e-5,f"最大距离 {error:.6g}")
    elif key=="T09":
        expected=layout_metrics(image,params["layout"],params["target"])
        for name,value in expected.items():
            error=abs(float(result[name])-value)
            check(name,error<.005,f"得到 {result[name]:.4f}，参考 {value:.4f}")
    elif key=="T10":
        valid=[i for i,layout in enumerate(params["candidates"])
               if (lambda v:v["coverage"]>=.98 and v["overlap"]<=.02)(
                   layout_metrics(image,layout,params["target"]))]
        integer=isinstance(result,(int,np.integer)) and not isinstance(result,(bool,np.bool_))
        check("索引类型",integer,"返回整数索引；无解时返回整数 -1")
        check("合法候选",integer and (result in valid if valid else result==-1),
              f"返回 {result}，允许 {valid if valid else [-1]}")
    elif key=="T11":
        check("图块身份",list(result)==truth["identities"],
              f"得到 {list(result)}，期望 {truth['identities']}")
    elif key=="T12":
        arr=np.asarray(result,float);target=truth["centers"]
        check("中心数量",arr.shape==target.shape,f"期望 {target.shape}")
        if arr.shape==target.shape:
            error=float(np.max(np.linalg.norm(arr-target,axis=1)))
            check("静止中心误差",error<2.2,f"最大偏移 {error:.2f} px，允许 2.2 px")
    elif key=="T14":
        mask_check(result["mask"],truth["mask"])
        match_centers(result["pieces"],True)
    return checks


def preview(key,image,params,result):
    if key in VISION_IDS:return vision_engine.preview(key,image,params,result)
    if key in DOMAIN_IDS:return domain_engine.preview(key,image,params,result)
    if key in EXTRA_IDS:return extra_engine.preview(key,image,params,result)
    canvas=cv2.cvtColor(image,cv2.COLOR_GRAY2BGR) if image.ndim==2 else image.copy()
    if key in ("T02","T03","T04","T05"): return result
    if key=="T06":
        cv2.drawContours(canvas,[np.asarray(c,np.int32) for c in result],-1,(40,190,255),2)
    elif key in ("T07","T14"):
        pieces=result["pieces"] if key=="T14" else result
        for i,p in enumerate(pieces):
            pts=np.rint(p["points"]).astype(np.int32).reshape(-1,2)
            cv2.polylines(canvas,[pts],True,(25,165,245),2)
            for j,pt in enumerate(pts):
                cv2.circle(canvas,tuple(pt),4,(220,70,90),-1)
                cv2.putText(canvas,str(j),tuple(pt+[5,-5]),0,.4,(90,30,210),1)
            center=tuple(np.rint(p["center"]).astype(int))
            cv2.circle(canvas,center,5,(40,65,230),-1)
            cv2.putText(canvas,str(i+1),center,0,.6,(30,30,30),2)
    elif key in ("T08","T13"):
        canvas[:]=(245,245,245)
        points=np.rint(result).astype(np.int32)
        if key=="T08": cv2.polylines(canvas,[points],True,(70,165,30),2)
        for i,pt in enumerate(points):
            cv2.circle(canvas,tuple(pt),5,(30,80,210),-1)
            cv2.putText(canvas,str(i),tuple(pt+[6,-6]),0,.5,(60,60,60),1)
    elif key in ("T09","T10"):
        canvas[:]=245
        x,y,w,h=params["target"];cv2.rectangle(canvas,(x,y),(x+w-1,y+h-1),(140,140,140),2)
        layout=params["layout"] if key=="T09" else (params["candidates"][int(result)] if result>=0 else [])
        colors=[(100,195,230),(210,170,90),(150,210,140)]
        for i,points in enumerate(layout):
            layer=canvas.copy();cv2.fillPoly(layer,[np.asarray(points,np.int32)],colors[i%3])
            canvas=cv2.addWeighted(layer,.6,canvas,.4,0)
    elif key=="T12":
        canvas[:]=245
        for frame in params["frames"]:
            for point in frame: cv2.circle(canvas,tuple(np.rint(point).astype(int)),3,(180,180,180),-1)
        for point in result: cv2.circle(canvas,tuple(np.rint(point).astype(int)),6,(30,140,30),2)
    return canvas


class LimitedLog(io.StringIO):
    def write(self,s):
        remaining=24000-self.tell()
        if remaining>0: super().write(s[:remaining])
        return len(s)


def compact_value(value,depth=0):
    """先限制数据规模再序列化，打印大图时不会先展开数十万个像素。"""
    if isinstance(value,np.ndarray):
        if value.size<=16:return value.tolist()
        return {"shape":list(value.shape),"dtype":str(value.dtype),
                "前12项":value.reshape(-1)[:12].tolist()}
    if isinstance(value,np.generic):return value.item()
    if depth>=4:return "…"
    if isinstance(value,dict):
        return {str(k)[:80]:compact_value(v,depth+1) for k,v in list(value.items())[:12]}
    if isinstance(value,(list,tuple)):
        values=[compact_value(v,depth+1) for v in value[:12]]
        return values+([f"…共 {len(value)} 项"] if len(value)>12 else [])
    if isinstance(value,str):return value[:600]
    if value is None or isinstance(value,(bool,int,float)):return value
    return f"<{type(value).__name__}>"


def error_info(error):
    locations=[]
    for frame in traceback.extract_tb(error.__traceback__):
        if re.fullmatch(r"[TPAYLV]\d{2}\.py",Path(frame.filename).name):
            locations.append(dict(lesson=Path(frame.filename).stem,line=frame.lineno))
    if isinstance(error,SyntaxError) and error.filename:
        locations.append(dict(lesson=Path(error.filename).stem,line=error.lineno or 1))
    location=locations[-1] if locations else {}
    return dict(type=type(error).__name__,message=str(error),**location)


@contextlib.contextmanager
def exercise_imports(folder, codes):
    """Make standard imports resolve to the exact submitted code snapshot."""
    snapshot = Path(folder) / 'source'
    package = snapshot / 'exercises'; package.mkdir(parents=True, exist_ok=True)
    (package / '__init__.py').write_text('', encoding='utf-8')
    for key, code in codes.items():
        if re.fullmatch(r'[A-Z]\d{2}', key):
            (package / (key + '.py')).write_text(code, encoding='utf-8')
    saved = {k: v for k, v in sys.modules.items() if k == 'exercises' or k.startswith('exercises.')}
    for key in saved: del sys.modules[key]
    sys.path.insert(0, str(snapshot))
    try:
        yield
    finally:
        sys.path.remove(str(snapshot))
        for key in list(sys.modules):
            if key == 'exercises' or key.startswith('exercises.'): del sys.modules[key]
        sys.modules.update(saved)


def execute(request):
    folder=Path(request["folder"]);folder.mkdir(parents=True,exist_ok=True)
    key=request["lesson"];codes=request["codes"];stack=[];log=LimitedLog()
    def student(name,image,params):
        if name in stack: raise ValueError("检测到循环调用："+" → ".join(stack+[name]))
        if name not in codes: raise ValueError(f"请先完成并保存 {name}")
        stack.append(name)
        try:
            scope={"np":np,"cv2":cv2,"read_image":read_image,"student":student,"__name__":"student"}
            exec(compile(codes[name],name+".py","exec"),scope)
            if not callable(scope.get("solve")): raise ValueError("需要定义 solve(image, params) 函数")
            return scope["solve"](image,params)
        finally: stack.pop()
    seeds=[17] if not request["verify"] else [101,207,333,440,995]
    reports=[]
    with exercise_imports(folder, codes), contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
        for seed in seeds:
            image,params,truth=fixture(key,seed,folder,request.get("custom") if not request["verify"] else None)
            report=dict(seed=seed,input=params["image_path"],output=None,
                        params=compact_value(params),checks=[],summary="")
            try:
                # 学生可以就地处理自己的数组；验收始终使用原始输入及参数。
                result=student(key,image.copy(),copy.deepcopy(params))
            except Exception as error:
                expected_error=bool(truth.get("degenerate") and isinstance(error,ValueError))
                report["checks"]=[dict(name="退化标定" if expected_error else "运行 / 接口",
                    ok=expected_error,detail=str(error))]
                if not expected_error:
                    report.update(summary=traceback.format_exc(),error=error_info(error))
            else:
                if truth.get("degenerate"):
                    report["checks"]=[dict(name="退化标定",ok=False,detail="共线标定点应抛出 ValueError")]
                elif request.get("custom") and not request["verify"]:
                    report["checks"]=[dict(name="自选图片探索",ok=True,detail="没有人工真值，本次仅运行，不计入通关")]
                else:
                    try:
                        report["checks"]=check_result(key,image,params,truth,result)
                    except Exception as error:
                        report["checks"]=[dict(name="返回值接口",ok=False,
                            detail=f"{type(error).__name__}: {error}；请对照本关的返回值约定")]
                # 显示失败不应覆盖验收结论，更不能被当成学生正确拒绝了退化输入。
                try:
                    output=str(folder/f"result_{seed}.png")
                    write_image(output,preview(key,image,params,result))
                    report["output"]=output
                except Exception as error:
                    report["preview_note"]=f"无法生成结果图：{type(error).__name__}: {error}"
                report["summary"]=json.dumps(compact_value(result),ensure_ascii=False)[:2400]
            report["passed"]=bool(report["checks"]) and all(c["ok"] for c in report["checks"])
            reports.append(report)
    passed=bool(reports) and all(report["passed"] for report in reports)
    return dict(lesson=key,verify=request["verify"],passed=passed,reports=reports,
                log=log.getvalue(),input=reports[0]["input"],output=reports[0]["output"],
                custom=bool(request.get("custom")) and not request["verify"])


def worker(request_path):
    request_path=Path(request_path)
    try:
        data=execute(json.loads(request_path.read_text(encoding="utf-8")))
    except Exception:
        data={"fatal":traceback.format_exc(),"passed":False}
    output=request_path.parent/"response.json"
    temp=output.with_suffix(".tmp")
    temp.write_text(json.dumps(data,ensure_ascii=False,default=json_value),encoding="utf-8")
    temp.replace(output)
