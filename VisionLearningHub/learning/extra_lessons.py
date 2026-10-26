"""Python、OpenCV 和搜索算法的可手敲基础课程。"""
from textwrap import dedent


def _lesson(key, title, goal, contract, knowledge, hints, reference, todos, prerequisites=()):
    return dict(id=key, title=title, goal=goal, contract=contract,
                knowledge=knowledge, hints=hints, reference=dedent(reference).strip()+"\n",
                starter="import cv2\nimport numpy as np\n\n\ndef solve(image, params):\n"
                + "".join("    # TODO: "+s+"\n" for s in todos)
                + "    raise NotImplementedError('请完成本关核心代码')\n",
                prerequisites=list(prerequisites))


EXTRA_LESSONS = [
_lesson("P01", "Python：循环与筛选", "用列表、循环和条件判断筛选候选区域，为轮廓过滤打基础。",
        "params['areas'] 是非负面积列表，params['min_area'] 是最小面积。返回所有面积 >= min_area 的原始下标列表，按原顺序排列。空输入返回 []。image 仅辅助展示。",
        "列表下标从 0 开始。enumerate(areas) 同时提供下标和数值；if 判断是否保留；append 将下标加入结果。函数应 return 结果，print 只产生日志。>= 包含边界，> 不包含边界。不要在遍历时删除原列表，否则可能跳过元素。你可以先写普通 for 循环，再改写为列表推导式，比较可读性。这个逻辑会在 T06 轮廓面积过滤、A05 候选过滤中重复使用。",
        ["先创建 kept = []，遍历 enumerate(params['areas'])。", "判断 area >= params['min_area'] 时追加 index，最后 return kept。"],
        '''
        def solve(image, params):
            kept = []
            for index, area in enumerate(params["areas"]):
                if area >= params["min_area"]:
                    kept.append(index)
            return kept
        ''', ["读取面积列表和最小面积", "遍历并保留满足条件的原始下标", "返回下标列表；处理空列表"]),
_lesson("P02", "NumPy：切片与统计", "掌握数组的行列顺序、切片、布尔比较与聚合计算。",
        "image 是 uint8 灰度图；params['roi']=(x,y,w,h)，params['threshold'] 是亮度阈值。返回 {'mean':ROI平均亮度, 'bright_count':ROI内严格大于阈值的像素数, 'shape':[h,w]}。",
        "二维数组 shape=(高,宽)，数组索引 image[y,x]。ROI 切片写作 image[y:y+h,x:x+w]，右端不包含。np.mean 自动进行数值聚合，不能只统计第一行。roi > threshold 产生布尔数组，np.count_nonzero 统计 True 的数量。Python 的 and/or 不用于逐像素逻辑，多条件使用 & 或 | 并给每个条件加括号。uint8 的减法可能下溢，图像相减前先转 float32 或 int16。",
        ["先解包 x,y,w,h，再按 y、x 的顺序切片。", "mean 用 float(np.mean(roi))，bright_count 用 int(np.count_nonzero(roi > threshold))。"],
        '''
        import numpy as np
        def solve(image, params):
            x, y, w, h = params["roi"]
            roi = image[y:y+h, x:x+w]
            return {"mean": float(np.mean(roi)),
                    "bright_count": int(np.count_nonzero(roi > params["threshold"])),
                    "shape": list(roi.shape)}
        ''', ["按约定裁剪灰度 ROI", "计算平均亮度、亮像素数量和形状", "返回字典"], ("P01",)),
_lesson("A01", "高斯滤波与噪声", "观察平滑怎样抑制噪声，以及核尺寸和 sigma 的作用。",
        "image 是含噪 uint8 灰度图。params['kernel'] 为奇数核尺寸，params['sigma'] 为标准差。使用 BORDER_REFLECT_101 边界，返回同尺寸 uint8 高斯滤波结果。",
        "滤波通过邻域加权平均计算输出。高斯核离中心越近权重越大，sigma 决定扩散范围；核越大不等于细节越好。GaussianBlur(image,(k,k),sigma,borderType=cv2.BORDER_REFLECT_101) 指定尺寸、标准差和边界。边缘处邻域越界时也需要明确规则。高斯适合平滑随机噪声；中值滤波更适合孤立的椒盐噪声；双边滤波可在平滑时保留部分边缘。这三者作用不同，本关只验收指定高斯规则。",
        ["k 必须为正奇数；使用参数，不要写死为 3。", "显式指定 borderType，避免边界像素与约定不一致。"],
        '''
        import cv2
        def solve(image, params):
            k = params["kernel"]
            return cv2.GaussianBlur(image, (k, k), params["sigma"],
                                    borderType=cv2.BORDER_REFLECT_101)
        ''', ["读取核尺寸和 sigma", "应用高斯滤波并返回图像"], ("P02",)),
_lesson("A02", "Canny 边缘检测", "理解梯度、双阈值与边缘连接，区分轮廓线和区域掩膜。",
        "输入 BGR 图。先转灰度，再 GaussianBlur((3,3),sigmaX=1,BORDER_REFLECT_101)，然后 Canny(low,high,apertureSize=3,L2gradient=True)。low/high 来自 params。返回 uint8 单通道 0/255 边缘图。",
        "Canny 的主要步骤为平滑、计算梯度、非极大值抑制和双阈值连接。高阈值选出强边缘，低阈值允许与强边缘连接的弱边缘保留；只把灰度二值化无法替代它。L2gradient=True 使用欧氏梯度幅值。边缘通常只有细线，颜色分割得到的是整块区域；找实心纸片时两者不能直接互换。拍摄模糊、背景纹理和纸片印刷都会影响边缘，本关使用可控的合成场景练习 API。",
        ["先 cvtColor(..., COLOR_BGR2GRAY)，再固定 3×3 平滑。", "Canny 使用 params['low'] 和 params['high']，显式 L2gradient=True。"],
        '''
        import cv2
        def solve(image, params):
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            smooth = cv2.GaussianBlur(gray, (3, 3), 1,
                                      borderType=cv2.BORDER_REFLECT_101)
            return cv2.Canny(smooth, params["low"], params["high"],
                             apertureSize=3, L2gradient=True)
        ''', ["BGR 转灰度并平滑", "设置双阈值和梯度选项", "返回边缘图"], ("A01", "T03")),
_lesson("A03", "透视矫正", "将倾斜拍摄的工作区拉正，理解四点对应和输出坐标。",
        "params['corners'] 按左上、右上、右下、左下提供 4×2 浮点点坐标；params['size']=(width,height)。映射到 (0,0),(w-1,0),(w-1,h-1),(0,h-1)，INTER_LINEAR 和 BORDER_CONSTANT=0。返回 h×w×3 uint8 矫正图。",
        "透视变换用 3×3 单应矩阵描述平面上的对应关系，适合平面纸片和工作台。getPerspectiveTransform 要求两组四点一一对应且为 float32。点顺序错误会造成折叠、镜像或严重扭曲。warpPerspective 的 dsize 顺序为宽、高，与数组 shape 的高、宽相反。透视矫正不能消除镜头畸变，也不能把非共面的物体统一矫正；实际相机先考虑畸变标定。",
        ["src=np.asarray(corners,np.float32)；创建约定顺序的 dst。", "先求矩阵，再 warpPerspective(image,matrix,(w,h))。"],
        '''
        import cv2
        import numpy as np
        def solve(image, params):
            w, h = params["size"]
            source = np.asarray(params["corners"], np.float32)
            target = np.array([[0,0],[w-1,0],[w-1,h-1],[0,h-1]], np.float32)
            matrix = cv2.getPerspectiveTransform(source, target)
            return cv2.warpPerspective(image, matrix, (w,h),
                flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        ''', ["按约定点序创建目标角点", "计算透视矩阵", "以指定宽高和插值方法变换图像"], ("T08", "P02")),
_lesson("A04", "矩形 IoU 评价", "实现交并比，建立检测结果评价与去重的基础。",
        "params['box_a']、['box_b'] 均为 [x1,y1,x2,y2]，连续坐标且 x2>=x1、y2>=y1。返回交集面积/并集面积浮点数。零面积框及零并集返回 0。面积不加 1。",
        "IoU 是 intersection over union。交集左上角取两个左上角的最大值，右下角取最小值；宽高分别 max(0,右-左)，不相交时面积自然为 0。并集=面积A+面积B-交集。IoU 为 1 表示完全相同，0 表示无面积重叠。它与 T09 的目标覆盖率不同：IoU 同时考虑漏检和多检。本关采用连续坐标，切勿混入像素端点包含规则的 +1。",
        ["先分别计算面积与相交宽高。", "判断 union > 0 再做除法，避免空框除零。"],
        '''
        def solve(image, params):
            a, b = params["box_a"], params["box_b"]
            width = max(0, min(a[2], b[2]) - max(a[0], b[0]))
            height = max(0, min(a[3], b[3]) - max(a[1], b[1]))
            intersection = width * height
            area_a = (a[2]-a[0]) * (a[3]-a[1])
            area_b = (b[2]-b[0]) * (b[3]-b[1])
            union = area_a + area_b - intersection
            return intersection / union if union > 0 else 0.0
        ''', ["计算交集并截断负宽高", "计算并集", "处理零面积并返回浮点 IoU"], ("P01",)),
_lesson("A05", "NMS 候选框去重", "实现按分数贪心保留框，并理解阈值与排序边界。",
        "params['boxes'] 为 Nx4 连续坐标框，['scores'] 为分数，['iou_threshold'] 为阈值。按分数降序、同分按原下标升序；保留当前最高分框，删除与其 IoU 严格大于阈值的框。返回保留的原下标列表，空输入返回 []。调用自己 A04 的代码。",
        "非极大值抑制 NMS 常用于删除同一目标的重复检测。它是贪心算法，按当前最高分作局部选择；并不保证任意业务目标的全局最优。本关单类别，真实多类别检测通常分别去重。阈值低更容易删除邻近目标，阈值高会保留更多重复框。IoU 恰好等于阈值时应保留。排序需要稳定约定，才能复现结果。最简单实现复杂度约 O(N²)，先理解再考虑向量化。",
        ["order=sorted(range(len(boxes)),key=lambda i:(-scores[i],i))。", "反复取 order[0]，保留剩余 IoU <= threshold 的下标。", "student('A04', image, {'box_a':..., 'box_b':...}) 调用你自己的上一关。"],
        '''
        def solve(image, params):
            boxes, scores = params["boxes"], params["scores"]
            order = sorted(range(len(boxes)), key=lambda i: (-scores[i], i))
            kept = []
            while order:
                best = order.pop(0)
                kept.append(best)
                remaining = []
                for index in order:
                    iou = student("A04", image, {"box_a": boxes[best], "box_b": boxes[index]})
                    if iou <= params["iou_threshold"]:
                        remaining.append(index)
                order = remaining
            return kept
        ''', ["按分数和下标确定排序", "保留最高分框", "调用自己的 IoU，过滤高重叠候选", "循环到候选为空"], ("A04",)),
_lesson("A06", "DFS 与回溯拼图", "亲手实现试放、递归和撤销，解决一个小型离散覆盖问题。",
        "params['board'] 是二维 0/1 列表：1 为目标格、0 为禁放格。params['pieces'] 为块列表，每块由若干 [row,col] 相对坐标组成。允许 90° 旋转和平移，禁止镜像；每块恰好使用一次。返回 [{'piece':原下标,'cells':[[行,列],...]}]，覆盖全部目标且不重叠；无解返回 None。",
        "DFS 深度优先搜索每次作一个选择并递归，走不通就撤销。状态包含剩余格子、已用块和当前路径。选最靠前的空格作为锚点，只尝试覆盖它的放置，可减少重复搜索。每块的旋转先减去最小行列完成归一化，并去重；每次试放前检查是否越界、落到禁放格或重叠。剩余格为空时还要确认所有块用完。仅面积相等不足以保证有解。本关是离散格子算法教学，不是原题连续多边形配准、机械执行或完整赛事求解器；学会后再迁移候选生成与几何约束。",
        ["把 board 中所有 1 的 (row,col) 放入 set，构建各块去重后的旋转形状。", "DFS 选择 min(remaining)，将旋转形状的每个格分别对齐这个锚点。", "cells <= remaining 才能试放；递归失败后撤销 path 和 used。", "返回成功路径的副本，搜索穷尽返回 None，不能把无解写成 []。"],
        '''
        def solve(image, params):
            remaining = {(r,c) for r,row in enumerate(params["board"])
                         for c,value in enumerate(row) if value == 1}
            variants = []
            for piece in params["pieces"]:
                points = [tuple(p) for p in piece]
                rotations = set()
                for _ in range(4):
                    min_r = min(r for r,c in points)
                    min_c = min(c for r,c in points)
                    rotations.add(tuple(sorted((r-min_r,c-min_c) for r,c in points)))
                    points = [(c,-r) for r,c in points]
                variants.append(sorted(rotations))
            used, path = set(), []

            def search(empty):
                if not empty:
                    return list(path) if len(used) == len(variants) else None
                anchor_r, anchor_c = min(empty)
                for index, rotations in enumerate(variants):
                    if index in used:
                        continue
                    for shape in rotations:
                        for local_r, local_c in shape:
                            cells = {(r+anchor_r-local_r,c+anchor_c-local_c) for r,c in shape}
                            if not cells <= empty:
                                continue
                            used.add(index)
                            path.append({"piece":index,"cells":[list(p) for p in sorted(cells)]})
                            answer = search(empty-cells)
                            if answer is not None:
                                return answer
                            path.pop()
                            used.remove(index)
                return None

            if sum(len(p) for p in params["pieces"]) != len(remaining):
                return None
            return search(remaining)
        ''', ["生成各块的旋转并去重", "建立剩余目标格、已用块和路径", "选锚点，枚举合法试放", "递归失败时撤销，成功返回路径，无解返回 None"], ("P01", "T10")),
]

EXTRA_IDS = {item["id"] for item in EXTRA_LESSONS}
