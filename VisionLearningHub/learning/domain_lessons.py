"""不依赖 GPU 的检测数据与 Linux 日志基础练习。"""
from .extra_lessons import _lesson

DOMAIN_LESSONS=[
_lesson('Y01','YOLO 标签检查','在训练之前找出类别或坐标错误的标签。',
    "params['labels'] 是标签行列表，格式 class cx cy width height；params['classes'] 为类别数。返回非法行的原下标列表。空白行忽略。类别为整数且在范围内，坐标有限，宽高>0，中心及整个框位于[0,1]。",
    '训练不能修复错误标注。YOLO 检测标签以原图宽高归一化；中心坐标不同于左上角。先检查字段数和数值类型，再检查类别范围、宽高及框边界。NaN 和无穷不是合法坐标。此课采用框完全在图内的约定，不检查图片文件与类别名称映射。',
    ['用 split 拆开一行，空白行可以跳过。','先用 float 读取并检查 math.isfinite，类别必须等于自己的整数值。','检查 cx±w/2、cy±h/2；浮点边界可容许 1e-9。'],
    '''
    import math
    def solve(image, params):
        invalid=[]
        for i,line in enumerate(params["labels"]):
            if not line.strip():
                continue
            try:
                cls,cx,cy,w,h=map(float,line.split())
                valid=all(math.isfinite(v) for v in (cls,cx,cy,w,h))
                valid=valid and cls.is_integer() and 0<=cls<params["classes"]
                valid=valid and w>0 and h>0
                valid=valid and cx-w/2>=-1e-9 and cy-h/2>=-1e-9
                valid=valid and cx+w/2<=1+1e-9 and cy+h/2<=1+1e-9
            except (ValueError,OverflowError):
                valid=False
            if not valid:
                invalid.append(i)
        return invalid
    ''', ['逐行检查标签字段','校验类别、有限数值及归一化框','返回非法行下标'],('P01',)),
_lesson('Y02','还原 letterbox 坐标','把模型输入中的检测框还原到原始图像。',
    "params['boxes'] 为 N×4 的 xyxy 框，['scale'] 为统一缩放比例，['pad']=[pad_x,pad_y]，['original_size']=[width,height]。先减 padding 再除 scale，最后按原图边界截断。返回 N×4 浮点数组，空输入返回(0,4)。",
    'Letterbox 保持宽高比，缩放后用 padding 补齐模型输入。画回原图时要执行逆变换，顺序是减去补边再除比例。x 按宽度截断，y 按高度截断。这里使用连续边界 [0,width] 与 [0,height]；不要混入像素下标最大值 width-1。不同模型预处理约定可能不同，要查看模型清单。',
    ['np.asarray(boxes,float).reshape(-1,4) 能统一空输入形状。','每行减 [px,py,px,py]，再除 scale。','分别对第0/2列和第1/3列 clip。'],
    '''
    import numpy as np
    def solve(image, params):
        boxes=np.asarray(params["boxes"],float).reshape(-1,4)
        px,py=params["pad"]
        out=(boxes-np.array([px,py,px,py]))/params["scale"]
        w,h=params["original_size"]
        out[:,[0,2]]=np.clip(out[:,[0,2]],0,w)
        out[:,[1,3]]=np.clip(out[:,[1,3]],0,h)
        return out
    ''',['统一数组形状','先减补边，再除缩放比例','截断坐标并返回'],('P02',)),
_lesson('Y03','理解 precision 与 recall','区分误报和漏报，从已知样本计算评价指标。',
    "params['truth']、['predicted'] 是等长的0/1列表。返回字典 tp、fp、fn、precision、recall；分母为0时约定指标为0。",
    'Precision=TP/(TP+FP)，回答报出的正例有多少正确；Recall=TP/(TP+FN)，回答实际正例找回多少。此课按样本二分类统计，不是完整目标检测 mAP。检测评价还需要类别、IoU 和一对一匹配，不能把每个检测框直接套入这两个列表。',
    ['用 zip 对齐真实值与预测值。','分别数 (1,1)、(0,1)、(1,0)。','在除法前处理分母为0。'],
    '''
    def solve(image, params):
        pairs=list(zip(params["truth"],params["predicted"]))
        tp=sum(t==1 and p==1 for t,p in pairs)
        fp=sum(t==0 and p==1 for t,p in pairs)
        fn=sum(t==1 and p==0 for t,p in pairs)
        return {"tp":tp,"fp":fp,"fn":fn,
                "precision":tp/(tp+fp) if tp+fp else 0.0,
                "recall":tp/(tp+fn) if tp+fn else 0.0}
    ''',['统计TP、FP和FN','按约定处理零分母','返回两个指标与计数'],('P01',)),
_lesson('L01','从日志定位异常','先识别日志级别，再从记录中提取错误信息。',
    "params['lines'] 是离线示例日志，每行以 INFO/WARN/ERROR 和一个空格开始。忽略空行及未知级别。返回 error_count、warning_count、last_error（最后一条ERROR后的文本，没有则为None）。",
    '这是离线日志解析练习，可以在 Windows 运行；通过本题不代表已完成真实 Linux 操作。日志中的级别字段决定严重程度，正文包含 ERROR 并不代表该行是错误。真实设备诊断时应结合时间、进程、退出码和前后文，避免只看最后一行。',
    ['line.partition(" ") 可分离级别和正文。','只比较级别字段，不在整行搜索 ERROR。','遍历时更新 last_error，初值为 None。'],
    '''
    def solve(image, params):
        errors=warnings=0
        last=None
        for line in params["lines"]:
            level,separator,message=line.partition(" ")
            if not separator:
                continue
            if level=="ERROR":
                errors+=1
                last=message
            elif level=="WARN":
                warnings+=1
        return {"error_count":errors,"warning_count":warnings,"last_error":last}
    ''',['解析级别字段','分别累计错误和警告','保留最后一条错误正文'],('P01',))
]
DOMAIN_IDS={item['id'] for item in DOMAIN_LESSONS}
