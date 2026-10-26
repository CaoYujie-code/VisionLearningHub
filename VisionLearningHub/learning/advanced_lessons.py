"""进阶图像处理、检测评估和部署数据契约；只使用标准库、OpenCV、NumPy。"""
from .extra_lessons import _lesson

ADVANCED_LESSONS = [
_lesson('V07', '缩放图像与插值选择', '缩放输入并保持宽高约定，比较图像和标签的插值需求。',
    "image 为 uint8 BGR 图；params['size']=[width,height]；params['mode'] 为 area 或 nearest。返回按对应 INTER_AREA/INTER_NEAREST 缩放的 uint8 BGR 图。",
    'resize 的 dsize 是宽、高，数组 shape 是高、宽、通道。缩小照片通常可尝试 INTER_AREA；离散类别掩膜用最近邻可避免生成新类别。缩放不是裁剪，非等比缩放会改变形状；需要保留长宽比时另加 letterbox。先打印输入输出 shape，再检查输出像素，不要仅看窗口大小。',
    ['把 size 转为 tuple。', '根据 mode 选择插值常量，不要写死输出尺寸。'],
    '''
    import cv2
    def solve(image, params):
        mode = cv2.INTER_AREA if params['mode'] == 'area' else cv2.INTER_NEAREST
        return cv2.resize(image, tuple(params['size']), interpolation=mode)
    ''', ['读取尺寸和插值模式', '调用 resize 并返回结果'], ('P02',)),
_lesson('V08', 'Gamma 与查找表', '用明确的公式调整亮度，而不是依赖模糊的调亮参数。',
    "image 为 uint8 灰度图，gamma>0。返回 floor(255*(image/255)**gamma) 的 uint8 图；运算先用 float64。本题采用 gamma 指数而非 1/gamma。",
    '在本题公式下，gamma<1 提亮中间灰度，gamma>1 压暗；0 和 255 保持端点不变。LUT 把 256 种输入预先映射到输出，适合重复处理 uint8 图。它不恢复已经过曝或欠曝丢失的细节，也不会消除空间上不均匀的光照。手算 0、64、128、255，再与代码比对。',
    ['np.arange(256, dtype=np.float64)/255 得到归一化灰度。', '乘 255、floor、转 uint8 后交给 cv2.LUT。'],
    '''
    import cv2
    import numpy as np
    def solve(image, params):
        table = np.floor(255 * (np.arange(256, dtype=np.float64) / 255) ** params['gamma']).astype(np.uint8)
        return cv2.LUT(image, table)
    ''', ['构造 256 项映射表', '按契约取整并使用 LUT'], ('P02',)),
_lesson('V09', 'CLAHE 局部对比度', '在局部亮度不均的图片中控制对比度增强。',
    "image 为 uint8 灰度图；params['clip_limit'] 为正数，params['grid']=[列网格数,行网格数]。返回 createCLAHE(clipLimit=...,tileGridSize=...).apply(image) 的结果。",
    '全局均衡化使用整幅图的分布；CLAHE 分块统计并限制局部直方图的过度集中，再融合块间结果。tileGridSize 是网格数量，不是每块的像素宽高。增强可能同时突出噪声，不能将对比度变强直接当成分割准确率提高。彩色图不要未经比较就分别均衡三个 BGR 通道；可在明确颜色空间后仅处理亮度通道。',
    ['先 createCLAHE，再调用 apply。', '观察 clipLimit 与 grid 分别改变什么。'],
    '''
    import cv2
    def solve(image, params):
        clahe = cv2.createCLAHE(clipLimit=params['clip_limit'], tileGridSize=tuple(params['grid']))
        return clahe.apply(image)
    ''', ['设置对比度限制和网格数', '增强灰度图并返回'], ('V01',)),
_lesson('V10', '连通域计数与像素面积', '将二值掩膜分成独立区域，区分像素面积与轮廓面积。',
    "image 为 uint8 0/255 掩膜；params['connectivity'] 为4或8；params['min_area'] 为像素面积下限。排除背景，返回面积>=下限的 [x,y,w,h,area] 列表，按 (y,x) 排序；空前景返回 []。",
    '4 连通只连接上下左右；8 连通还允许对角连接，两个角接触的块可能因此合并。connectedComponentsWithStats 的 0 号标签是背景；CC_STAT_AREA 统计实际前景像素数量。它不同于 contourArea 的几何面积，也不等于外接矩形面积。孔洞不算前景。区域编号不用于排序或跨帧身份，返回前按坐标排序。',
    ['显式传 connectivity=，从标签1开始遍历 stats。', 'stats 的前五列就是 LEFT、TOP、WIDTH、HEIGHT、AREA。'],
    '''
    import cv2
    def solve(image, params):
        count, labels, stats, centers = cv2.connectedComponentsWithStats(image, connectivity=params['connectivity'])
        rows = [row.tolist() for row in stats[1:] if row[cv2.CC_STAT_AREA] >= params['min_area']]
        return sorted(rows, key=lambda row: (row[1], row[0]))
    ''', ['计算连通域统计并排除背景', '按面积筛选', '按 y、x 排序'], ('T05',)),
_lesson('V11', '距离变换与目标内部', '计算前景像素到最近背景的距离，为分离粘连目标做准备。',
    "image 为含背景的 uint8 二值图；使用 DIST_L2、DIST_MASK_PRECISE，返回同尺寸 float32 距离图。背景为0，前景值为到最近零像素的欧氏距离。",
    'distanceTransform 的距离是到最近的零像素，不是到图像中心。物体内部通常有较大值，可用于生成分水岭种子；距离峰值并不总对应独立物体，细长目标、噪声和粘连会影响种子数量。计算结果保留浮点距离；仅在显示时归一化到 0–255，否则测量单位就丢失了。',
    ['明确 DIST_L2 与 DIST_MASK_PRECISE。', '不要把显示用归一化图作为返回值。'],
    '''
    import cv2
    def solve(image, params):
        return cv2.distanceTransform(image, cv2.DIST_L2, cv2.DIST_MASK_PRECISE)
    ''', ['调用精确欧氏距离变换', '返回原始浮点距离'], ('V10',)),
_lesson('V12', '模板定位与分数方向', '用模板在原图中定位一个外观固定的目标。',
    "image 与 params['template'] 为 uint8 灰度图，模板不大于输入；使用 TM_SQDIFF，返回 {'top_left':[x,y]} 的全局最小值位置；有多个同分位置时按 y、x 选最先者。",
    'matchTemplate 输出每个有效模板左上角位置的响应图，宽为 W-w+1，高为 H-h+1。TM_SQDIFF 越小越相似；相关性类方法通常取最大值，不能混用。此练习输入含一个精确模板；现场需要验证分数阈值、无目标情况及重复纹理。旋转、尺度和透视变化明显时，需要多尺度搜索或特征匹配等方法。',
    ['用 matchTemplate 生成差平方响应。', 'minMaxLoc 的第三个返回值是 minLoc。'],
    '''
    import cv2
    def solve(image, params):
        response = cv2.matchTemplate(image, params['template'], cv2.TM_SQDIFF)
        _, _, location, _ = cv2.minMaxLoc(response)
        return {'top_left': list(location)}
    ''', ['计算响应图', '取最小值对应的左上角坐标'], ('P02',)),
_lesson('V13', 'HSV 环绕色相分割', '正确处理跨越色相零点的红色范围。',
    "image 为 uint8 BGR 图。转为 OpenCV 标准 uint8 HSV；params 有 hue_low、hue_high、s_min、v_min。H 区间包含端点；low<=high 选中闭区间，否则选 H>=low 或 H<=high。同时 S>=s_min、V>=v_min，返回 uint8 0/255 掩膜。",
    'OpenCV 标准 uint8 HSV 的 H 通常取 0–179，红色跨越零点。不能把 [170,10] 当成普通上下界交给一次 inRange。先分成两段，再 bitwise_or；S/V 过滤低饱和灰色与暗区。HSV_FULL 与浮点 HSV 的范围不同，本题只使用 COLOR_BGR2HSV。固定阈值仍需要不同光照下的独立样本。',
    ['普通范围一次 inRange；环绕范围分别取 [low,179] 和 [0,high]。', '两个区间使用同一组 S/V 下限。'],
    '''
    import cv2
    def solve(image, params):
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        low, high = params['hue_low'], params['hue_high']
        s, v = params['s_min'], params['v_min']
        if low <= high:
            return cv2.inRange(hsv, (low,s,v), (high,255,255))
        a = cv2.inRange(hsv, (low,s,v), (179,255,255))
        b = cv2.inRange(hsv, (0,s,v), (high,255,255))
        return cv2.bitwise_or(a,b)
    ''', ['转换到标准 HSV', '判断是否跨越色相零点', '合并掩膜并保留 S/V 限制'], ('T04',)),
_lesson('V14', '帧差与运动区域', '找出两帧之间发生变化的像素，同时理解运动检测的局限。',
    "image 为当前 uint8 灰度帧，params['previous'] 为同尺寸前帧，threshold 为0–255整数。返回 abs(current-previous)>threshold 的 uint8 0/255 掩膜；相等时为0。",
    'uint8 直接相减可能回绕，cv2.absdiff 同时处理变亮和变暗。两帧差异会覆盖移动目标的新旧位置；光照突变、相机抖动也会触发响应。它不提供物体身份，也不能直接得到速度。进一步学习时先固定摄像头，再比较背景建模、稀疏光流和目标跟踪，并保存时间戳。',
    ['先 absdiff，后 THRESH_BINARY。', 'threshold 的判定是严格大于，不包含相等值。'],
    '''
    import cv2
    def solve(image, params):
        delta = cv2.absdiff(image, params['previous'])
        return cv2.threshold(delta, params['threshold'], 255, cv2.THRESH_BINARY)[1]
    ''', ['计算双向绝对差值', '按阈值返回变化掩膜'], ('T03',)),
_lesson('Y04', '检查数据划分泄漏', '发现同一采集场景同时出现在训练集和验证集的问题。',
    "params['samples'] 是含 group、split 的字典列表；group 为非空字符串，split 为 train/val/test。返回出现在多个 split 中的 group，去重并按字符串排序；空输入返回 []。",
    '同一段视频的邻近帧高度相似，逐张随机划分会夸大泛化表现。group 可采用采集会话、工件批次或现场编号。先按组划分，再做训练集增强；不要把同一原图的增强版分到验证集。本题审计分组交叉，不检测视觉近重复，也不保证类别平衡。审计通过后仍需看各组的类别和场景分布。',
    ['用字典记录每个 group 出现过的 split 集合。', '集合长度大于1的组就是交叉组。'],
    '''
    def solve(image, params):
        groups = {}
        for sample in params['samples']:
            groups.setdefault(sample['group'], set()).add(sample['split'])
        return sorted(key for key, splits in groups.items() if len(splits) > 1)
    ''', ['按 group 汇总 split', '筛选跨集合的组并排序'], ('P01',)),
_lesson('Y05', '检测框一对一匹配', '把重复框、错误类别和漏检转换为 TP、FP、FN。',
    "params['predictions'] 的行是 [x1,y1,x2,y2,score,class]，truth 的行是 [x1,y1,x2,y2,class]，均为正面积半开框。按分数降序（同分按原下标）处理预测；只匹配同类别且未匹配的真值，选 IoU 最大者（同 IoU 取真值原下标）；IoU>=iou_threshold 才匹配。返回整数 tp、fp、fn。空输入合法。",
    '一次真值只能贡献一个 TP；同一物体上的重复框仍是 FP。类别必须匹配，IoU 的面积按连续半开坐标计算，不加1。这里固定一张图、一个 IoU 阈值，用于理解贪心匹配；不是 COCO mAP 的完整复现。完整指标还涉及多个阈值、类别聚合、置信度排序以及 crowd/ignore 等数据集约定。',
    ['sorted 用 (-score,index) 保证确定顺序。', '每次只查尚未匹配且同类的真值，匹配成功后加入 used。'],
    '''
    def solve(image, params):
        predictions, truth = params['predictions'], params['truth']
        used = set()
        for index in sorted(range(len(predictions)), key=lambda i: (-predictions[i][4],i)):
            p = predictions[index]
            best, best_iou = None, -1.0
            for j, t in enumerate(truth):
                if j in used or p[5] != t[4]:
                    continue
                intersection = max(0,min(p[2],t[2])-max(p[0],t[0])) * max(0,min(p[3],t[3])-max(p[1],t[1]))
                union = (p[2]-p[0])*(p[3]-p[1]) + (t[2]-t[0])*(t[3]-t[1]) - intersection
                iou = intersection / union
                if iou > best_iou:
                    best, best_iou = j, iou
            if best is not None and best_iou >= params['iou_threshold']:
                used.add(best)
        tp = len(used)
        return {'tp':tp, 'fp':len(predictions)-tp, 'fn':len(truth)-tp}
    ''', ['按分数排序并保持同分顺序', '计算同类未匹配框的 IoU', '执行一对一匹配并统计'], ('A04','Y03')),
_lesson('L02', '读懂图像行步幅', '把带行填充的原始 BGR 缓冲区转换为正确的像素数组。',
    "params 包含 buffer（uint8一维数组）、width、height、stride；每行前 width*3 字节为紧密 BGR，剩余为 padding；stride>=width*3，缓冲区大小为 height*stride。返回独立、连续的 height×width×3 uint8 数组，不包含 padding。",
    '设备返回的一行字节数可能大于宽×通道数，直接 reshape(height,width,3) 会失败或错位。先按 stride 分行，截取有效像素，再调整通道并 copy。这是单平面 BGR8 的离线契约练习，不适用于 NV12/YUYV，也不模拟真实 V4L2 驱动。真实设备还需协商像素格式、bytesperline、sizeimage 和缓冲区生命周期。',
    ['buffer.reshape(height,stride) 先保留每行填充。', '每行取前 width*3 字节，再 reshape 并 copy。'],
    '''
    import numpy as np
    def solve(image, params):
        rows = np.asarray(params['buffer'], dtype=np.uint8).reshape(params['height'], params['stride'])
        return rows[:, :params['width']*3].reshape(params['height'], params['width'],3).copy()
    ''', ['按行步幅组织缓冲区', '去除每行填充', '返回独立连续的 BGR 数组'], ('P02',)),
_lesson('L03', '端到端延迟统计', '从逐帧记录中找出慢帧，而不是只报告模型前向时间。',
    "params['frames'] 每行是非负的 [采集,预处理,推理,后处理] 毫秒；至少1行且每帧总耗时>0。返回 mean_ms、p95_ms（np.percentile 默认 linear）、serial_fps=1000/mean_ms；计算应使用 float64。",
    '每帧先求和，得到端到端延迟；P95 描述延迟分布尾部，均值不能反映偶发卡顿。此题 serial_fps 只估算完全串行、无其他等待的处理能力；异步流水线的吞吐不能用它直接替代。实测时固定输入、预热、使用单调时钟，并正确同步异步设备。GPU 推理时间与采集到输出的墙钟时间分别记录。',
    ['沿 axis=1 求每帧总耗时。', '先取平均再求倒数，不要对每帧 FPS 求平均。'],
    '''
    import numpy as np
    def solve(image, params):
        totals = np.asarray(params['frames'], dtype=np.float64).sum(axis=1)
        mean = float(totals.mean())
        return {'mean_ms':mean, 'p95_ms':float(np.percentile(totals,95)), 'serial_fps':1000/mean}
    ''', ['计算各帧总耗时', '计算均值和 P95', '估算串行 FPS 并返回'], ('P02',)),
]
ADVANCED_IDS = {lesson['id'] for lesson in ADVANCED_LESSONS}
