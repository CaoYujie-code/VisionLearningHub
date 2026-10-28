"""离线课程。参考实现仅在用户主动查看或自检时使用，验收运行学生代码。"""
from textwrap import dedent


def lesson(key, title, goal, contract, knowledge, hints, reference, todos, prerequisites=()):
    return dict(id=key, title=title, goal=goal, contract=contract,
                knowledge=knowledge, hints=hints, reference=dedent(reference).strip()+"\n",
                starter="import cv2\nimport numpy as np\n\n\ndef solve(image, params):\n"
                + "".join("    # TODO: "+s+"\n" for s in todos)
                + "    raise NotImplementedError('请完成本关核心代码')\n",
                prerequisites=list(prerequisites))


LESSONS = [
lesson("T01", "读图与像素", "读入照片，理解图像的宽、高、通道与像素坐标。",
       "输入：BGR 图像 image；params['image_path'] 为图片路径。返回字典：width、height、channels、pixel（左上角的 BGR 列表）。",
       "图像是 NumPy 数组，shape 的顺序是高、宽、通道。image[y, x] 先写行再写列。read_image(path) 是平台提供的中文路径读图函数，内部用 np.fromfile 和 cv2.imdecode。正常图片为 uint8，每个通道通常在 0～255。读图失败应抛出明确错误。",
       ["用 image = read_image(params['image_path']) 读图。", "h, w, c = image.shape；像素用 image[0, 0].tolist()。"],
       """
       import cv2
       import numpy as np

       def solve(image, params):
           image = read_image(params["image_path"])
           h, w, c = image.shape
           return {"width": w, "height": h, "channels": c,
                   "pixel": image[0, 0].tolist()}
       """, ["读取 params 中的图片路径", "获取宽、高、通道及左上角像素", "返回约定的字典"]),
lesson("T02", "ROI 与坐标", "裁出指定工作区，理解 x、y 与数组切片的关系。",
       "params['roi'] 为 (x, y, width, height)。返回裁剪后的图像数组。",
       "ROI 是感兴趣区域。切片 image[y:y+h, x:x+w] 包含起点、不包含终点。裁剪图中的点 (u,v) 回到原图要加 (x,y)。用 copy() 创建独立数组，避免修改裁剪图时影响原图。平台验收会改变 ROI，不能写死位置。",
       ["先解包 x, y, w, h。", "切片的第一维是 y，第二维是 x。"],
       """
       def solve(image, params):
           x, y, w, h = params["roi"]
           return image[y:y+h, x:x+w].copy()
       """, ["取出 ROI 参数", "按行列顺序裁剪并返回"]),
lesson("T03", "灰度与阈值", "将彩色图转换为灰度，观察亮度分割的能力与局限。",
       "params['threshold'] 为阈值。返回 uint8 单通道图，亮于阈值为 255，其余为 0。",
       "cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) 将三通道转成亮度。cv2.threshold 返回阈值和输出图两个结果。THRESH_BINARY 在像素值大于阈值时输出 255。黑色印刷可能在白纸内部变成孔洞，下一关使用背景颜色改善这一问题。",
       ["先生成 gray。", "_, mask = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY)。"],
       """
       import cv2
       def solve(image, params):
           gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
           _, mask = cv2.threshold(gray, params["threshold"], 255, cv2.THRESH_BINARY)
           return mask
       """, ["转换为灰度", "应用指定阈值", "只返回二值图"]),
lesson("T04", "分离绿色背景", "从绿色工作台上提取完整的纸片区域。",
       "输入为 BGR 图。params['lower']、['upper'] 是 HSV 背景阈值。返回前景 255、背景 0 的 uint8 掩膜。",
       "标准 8 位 HSV 的 H 范围为 0～179，S/V 为 0～255。inRange 选出的是背景，取反后才是碎片。必须分清 BGR 与 RGB。检查掩膜时关注纸片内的黑字和红色图案是否仍属于前景。本关先用颜色明确的工作台。",
       ["使用 COLOR_BGR2HSV。", "用 inRange 选出绿色，再用 bitwise_not 取反。"],
       """
       import cv2
       import numpy as np
       def solve(image, params):
           hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
           background = cv2.inRange(hsv, np.array(params["lower"], np.uint8),
                                   np.array(params["upper"], np.uint8))
           return cv2.bitwise_not(background)
       """, ["BGR 转 HSV", "选出绿色背景", "取反得到完整碎片"]),
lesson("T05", "清理二值掩膜", "去掉孤立噪点，修补小孔，同时保留真实边界。",
       "本关 image 已是单通道含噪掩膜。params['kernel'] 为奇数核尺寸。返回清理后的 uint8 二值图。",
       "白色区域是前景。开运算先腐蚀后膨胀，常用于去掉小白点；闭运算先膨胀后腐蚀，常用于修补小黑孔。核过大可能吃掉短边或合并相邻碎片。对比处理前后，不要只追求画面光滑。",
       ["np.ones((k,k), np.uint8) 可以创建核。", "先 MORPH_OPEN，再 MORPH_CLOSE。"],
       """
       import cv2
       import numpy as np
       def solve(image, params):
           k = params["kernel"]
           kernel = np.ones((k, k), np.uint8)
           opened = cv2.morphologyEx(image, cv2.MORPH_OPEN, kernel)
           return cv2.morphologyEx(opened, cv2.MORPH_CLOSE, kernel)
       """, ["构建形态学核", "去掉孤立白点", "修补小孔并返回"]),
lesson("T06", "找到每块碎片", "将掩膜变成独立轮廓，过滤面积太小的区域。",
       "输入为单通道掩膜。返回轮廓列表，每条轮廓是 N×1×2 或 N×2 数组。过滤面积小于 params['min_area'] 的区域。",
       "findContours 返回轮廓列表和层级。RETR_EXTERNAL 只取外轮廓，避免把片内孔洞当成新碎片。contourArea 计算几何面积。轮廓返回顺序没有身份含义；验收会按位置匹配，而不是逐个比较列表下标。",
       ["findContours(image, RETR_EXTERNAL, CHAIN_APPROX_SIMPLE)。", "筛选 contourArea(c) >= params['min_area']。"],
       """
       import cv2
       def solve(image, params):
           contours, _ = cv2.findContours(image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
           return [c for c in contours if cv2.contourArea(c) >= params["min_area"]]
       """, ["提取外轮廓", "过滤小面积", "返回轮廓列表"]),
lesson("T07", "中心与角点", "用图像矩和多边形近似描述每块碎片。",
       "params['contours'] 提供轮廓。返回列表，每项为 {'center':(x,y), 'points':N×2顶点, 'area':面积}。",
       "质心为 (m10/m00, m01/m00)，需要先检查 m00。approxPolyDP 的 epsilon 通常取周长的一小部分。过大丢失短边，过小保留毛刺。顶点起点和顺逆时针都可能不同，平台检查几何误差并容许点序差异。",
       ["cv2.moments(c) 得到矩。", "epsilon = 0.018 * cv2.arcLength(c, True)，近似后 reshape(-1,2)。"],
       """
       import cv2
       def solve(image, params):
           pieces = []
           for c in params["contours"]:
               m = cv2.moments(c)
               if m["m00"] == 0:
                   continue
               points = cv2.approxPolyDP(c, 0.018 * cv2.arcLength(c, True), True)
               pieces.append({"center": (m["m10"]/m["m00"], m["m01"]/m["m00"]),
                              "points": points.reshape(-1, 2), "area": cv2.contourArea(c)})
           return pieces
       """, ["遍历轮廓并计算矩", "得到质心和近似顶点", "返回每片几何描述"]),
lesson("T08", "旋转与平移", "用二维矩阵移动多边形，理解图像坐标中的旋转。",
       "params 包含 points(N×2)、angle(度)、translation(dx,dy)。绕原点旋转后平移，返回 N×2 浮点数组。",
       "旋转矩阵 R=[[cos,-sin],[sin,cos]]；列向量写作 R@p+t，点按行存储时写 points@R.T+t。np.sin 接受弧度。图像的 y 向下，因此正角在画面上表现为顺时针。必须先说明坐标系，不能把角度直接发送给机械平台。",
       ["先 np.deg2rad(angle)。", "用 @ 做矩阵乘法，保持浮点精度。"],
       """
       import numpy as np
       def solve(image, params):
           points = np.asarray(params["points"], dtype=float)
           theta = np.deg2rad(params["angle"])
           c, s = np.cos(theta), np.sin(theta)
           rotation = np.array([[c, -s], [s, c]])
           return points @ rotation.T + np.asarray(params["translation"])
       """, ["角度转弧度", "创建旋转矩阵", "旋转后平移"]),
lesson("T09", "检验拼图布局", "分别测量覆盖和重叠，为搜索提供评价函数。",
       "params['layout'] 是多边形列表，params['target']=(x,y,w,h)。返回 {'coverage':0~1, 'overlap':0~1}。按本关栅格规则计数。",
       "每片画入独立 0/1 掩膜，然后相加得到每个像素被覆盖的次数。目标内 count>0 的像素数除以目标面积为 coverage；全画布 count>1 的像素数除以目标面积为 overlap。矩形目标用 NumPy 切片定义，右下边界不包含。共同边缘也计重叠；本关容差会考虑这一像素边界。",
       ["用 int32 累计图，避免 uint8 多片相加溢出。", "fillPoly 画每片；目标区域用切片统计。"],
       """
       import cv2
       import numpy as np
       def solve(image, params):
           counts = np.zeros(image.shape[:2], np.int32)
           for points in params["layout"]:
               mask = np.zeros(image.shape[:2], np.uint8)
               cv2.fillPoly(mask, [np.rint(points).astype(np.int32)], 1)
               counts += mask
           x, y, w, h = params["target"]
           coverage = np.count_nonzero(counts[y:y+h, x:x+w]) / (w*h)
           overlap = np.count_nonzero(counts > 1) / (w*h)
           return {"coverage": coverage, "overlap": overlap}
       """, ["把每片栅格化并累计", "计算目标内覆盖率", "计算重叠率"]),
lesson("T10", "选择合法候选", "调用自己写的评价函数，从多个布局中找出合法解。",
       "params['candidates'] 提供布局列表。调用 student('T09', image, child_params)，返回合法候选的索引；没有合法解则返回 -1。",
       "求解可以分为生成候选和评价候选。本关先给出候选，让你专注约束筛选。coverage≥0.98 且 overlap≤0.02 才接受。本关阈值是教学条件，不是比赛标准。候选顺序会变化，可能包含多个合法解；任何满足约束的解均可通过。后续可自行加入边对齐和回溯来产生候选。",
       ["复制 params 后把 layout 换成当前候选。", "student 调用你已保存的 T09 代码，不会自动使用参考实现。"],
       """
       def solve(image, params):
           for index, layout in enumerate(params["candidates"]):
               child = dict(params)
               child["layout"] = layout
               metrics = student("T09", image, child)
               if metrics["coverage"] >= 0.98 and metrics["overlap"] <= 0.02:
                   return index
           return -1
       """, ["遍历候选布局", "调用自己的 T09", "返回合法索引或 -1"], ("T09",)),
lesson("T11", "图案与身份", "从外形相同的图像块中识别每块的模板身份。",
       "params['templates'] 是参考灰度图列表，params['patches'] 是打乱并旋转后的图块。返回各图块对应的模板索引列表。",
       "相同轮廓不能确定身份。本关素材已统一尺寸，仅有 0/90/180/270 度旋转。可以对每个模板尝试四种朝向，比较归一化像素误差。np.rot90 返回视图，转 float 后求差可以避免 uint8 下溢。真实扑克还需要处理遮挡、尺度与拼缝连续性，本关是图案匹配的基础。",
       ["每片与所有模板的四种旋转分别比较。", "误差用 np.mean((a.astype(float)-b.astype(float))**2)。"],
       """
       import numpy as np
       def solve(image, params):
           identities = []
           for patch in params["patches"]:
               scores = []
               for template in params["templates"]:
                   score = min(np.mean((patch.astype(float) -
                               np.rot90(template, k).astype(float))**2) for k in range(4))
                   scores.append(score)
               identities.append(int(np.argmin(scores)))
           return identities
       """, ["遍历图块与模板", "尝试四种旋转并计算误差", "返回匹配身份"]),
lesson("T12", "多帧稳定", "从静止碎片的抖动序列中恢复稳定中心。",
       "params['frames'] 为多帧中心点列表，各帧顺序可能不同。返回按 x 从小到大排列的稳定中心。",
       "本关明确假设目标静止、x 方向相互分离且每帧没有漏片。可先按 x 排序建立对应，再对时间维求中值，抑制个别偏差。这个策略不能直接用于目标交叉、运动或漏检的场景；这些场景需要身份匹配和状态处理。",
       ["每帧先按 x 排序，不能直接对原始列表求平均。", "np.median(aligned, axis=0)。"],
       """
       import numpy as np
       def solve(image, params):
           aligned = [sorted(frame, key=lambda p: p[0]) for frame in params["frames"]]
           return np.median(np.asarray(aligned), axis=0)
       """, ["统一各帧中心的对应顺序", "沿时间维求中值", "返回稳定中心"]),
lesson("T13", "像素到平台", "用对应点拟合二维仿射映射，并验证未参与拟合的位置。",
       "params 包含 visual、platform、checks，均为 N×2 点数组。拟合 visual→platform，并返回 checks 映射后的坐标。",
       "仿射映射 X=a*u+b*v+c、Y=d*u+e*v+f。把视觉点扩成 [u,v,1]，用 np.linalg.lstsq 拟合。至少需要三组不共线点；原项目使用六点。验收使用独立检查点，同时会给出共线样本，必须用 ValueError 拒绝退化标定。",
       ["design = np.column_stack([visual, np.ones(len(visual))])。", "检查 matrix_rank(design) 是否为 3，然后求最小二乘。"],
       """
       import numpy as np
       def solve(image, params):
           visual = np.asarray(params["visual"], float)
           design = np.column_stack([visual, np.ones(len(visual))])
           if np.linalg.matrix_rank(design) < 3:
               raise ValueError("标定点共线，无法确定二维映射")
           affine = np.linalg.lstsq(design, params["platform"], rcond=None)[0]
           checks = np.asarray(params["checks"], float)
           return np.column_stack([checks, np.ones(len(checks))]) @ affine
       """, ["构造仿射设计矩阵", "拒绝共线点", "拟合后预测检查点"]),
lesson("T14", "我的碎片检测器", "组合之前亲手写的函数，完成图片到几何数据的全过程。",
       "输入 BGR 图片。调用自己保存的 T04、T05、T06、T07。返回 {'mask':二值图, 'pieces':几何描述列表}。",
       "把复杂任务拆成接口稳定的小函数，能定位错误发生在哪一步。student(id,image,params) 只运行你保存的实现；依赖尚未完成会明确报错。验收会改变碎片的形状、位置、数量及轻微噪点，空场景应返回空列表。此综合关验收视觉检测，完整机械闭环仍需要真实设备测量。",
       ["分割 → 清理 → 轮廓 → 几何描述。", "将轮廓放入 child['contours']，再调用 T07。"],
       """
       def solve(image, params):
           mask = student("T04", image, params)
           mask = student("T05", mask, params)
           contours = student("T06", mask, params)
           child = dict(params)
           child["contours"] = contours
           pieces = student("T07", image, child)
           return {"mask": mask, "pieces": pieces}
       """, ["调用自己的颜色分割和清理函数", "调用轮廓提取", "把轮廓交给几何描述函数", "返回掩膜与碎片"], ("T04","T05","T06","T07")),
]
from .extra_lessons import EXTRA_LESSONS
LESSONS.extend(EXTRA_LESSONS)
from .domain_lessons import DOMAIN_LESSONS
LESSONS.extend(DOMAIN_LESSONS)
from .vision_lessons import VISION_LESSONS
LESSONS.extend(VISION_LESSONS)
from .advanced_lessons import ADVANCED_LESSONS
LESSONS.extend(ADVANCED_LESSONS)
from .project_catalog import PROJECT_LESSONS
LESSONS.extend(PROJECT_LESSONS)
from .function_handbook import guide as function_guide
for item in LESSONS:
    if not item['id'].startswith('E'):
        item['function_guide'] = function_guide(item['id'])
BY_ID = {item["id"]: item for item in LESSONS}
COURSE_VERSION = 2
