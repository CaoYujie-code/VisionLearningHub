"""Progressive OpenCV lessons for image statistics, segmentation and gradients."""
from .extra_lessons import _lesson

VISION_LESSONS=[
_lesson('V01','读懂灰度直方图','统计每个亮度值出现的次数，让图像分割有证据可看。',
    "image 是 uint8 灰度图。返回长度为 256 的整数数组：索引是亮度 0–255，对应值是该亮度的像素数。所有计数之和必须等于图像像素数。",
    '直方图保留了亮度出现频率，但丢失像素的位置。同一张直方图可能来自完全不同的空间布局。单峰集中可能表示对比度低，两个峰有时提示前景背景亮度分离。观察直方图有助于提出阈值范围，不能单独证明阈值能把目标完整分开。',
    ['把灰度数组展平后统计，每个像素只计入一个亮度区间。','np.bincount 可统计非负整数，指定 minlength=256 才能保留空的高亮度区间。','用 np.histogram(image,bins=256,range=(0,256)) 可交叉检查边界。'],
    '''
    import numpy as np
    def solve(image, params):
        return np.bincount(image.ravel(), minlength=256)
    ''',['展平二维图像','分别统计 0–255 的像素','返回固定 256 项计数数组'],('T03',)),
_lesson('V02','局部自适应阈值','在光照从一侧变亮时，用附近亮度代替全图同一个阈值。',
    "image 是 uint8 灰度图；params['block_size'] 是大于 1 的奇数窗口，params['c'] 是局部阈值校正值。返回同尺寸、只含 0 和 255 的 uint8 掩膜。",
    '全局阈值对全图使用同一亮度界线。自适应阈值先估计每个像素附近的局部亮度，再减去常数 C。窗口太小会跟着字纹理波动，太大会退化成近似全局判断。OpenCV 使用默认边界填充。暗字还是亮目标取决于二值方向；本练习约定亮于局部阈值输出白色。',
    ['检查窗口是奇数且大于 1。','调用 cv2.adaptiveThreshold，方法用 ADAPTIVE_THRESH_GAUSSIAN_C。','使用 THRESH_BINARY，并传入 params 的窗口和 C。'],
    '''
    import cv2
    def solve(image, params):
        return cv2.adaptiveThreshold(
            image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, params["block_size"], params["c"])
    ''',['读取局部窗口和校正值','计算加权局部均值','返回二值掩膜'],('T03',)),
_lesson('V03','去掉椒盐噪声','识别孤立黑白噪点，再比较中值滤波对细节的影响。',
    "image 是 uint8 单通道图，含少量 0 / 255 脉冲噪声；params['kernel'] 是奇数核尺寸。返回同尺寸 uint8 图像。",
    '中值滤波用邻域中间值替换中心像素，对孤立的椒盐点常比线性平滑更有效。OpenCV 的 medianBlur 使用边界复制。核尺寸太大会抹掉小孔、细线和角点。高斯滤波最小化加权平方差，解决的噪声假设与中值滤波不同。',
    ['调用 cv2.medianBlur(image, kernel)。','在实验室观察：去掉脉冲噪点后，尺寸很小的真实细节会怎样？'],
    '''
    import cv2
    def solve(image, params):
        return cv2.medianBlur(image, params["kernel"])
    ''',['读取奇数窗口','对每个像素取窗口中位数','保留 uint8 图像并返回'],('A01',)),
_lesson('V04','Sobel 与梯度方向','同时保留亮度变化方向与强度，再组合成边缘响应。',
    "image 是 uint8 灰度图；params['ksize'] 为 3 或 5。返回字典 gx、gy、magnitude，均为同尺寸浮点数组；magnitude=sqrt(gx²+gy²)。",
    'Sobel 通过平滑并求导估算亮度梯度。gx 为水平方向导数，gy 为垂直方向导数；正负号表示亮度变化方向。梯度幅值描述变化强弱，sqrt(gx²+gy²) 结合两个方向。导数结果可能小于 0 或大于 255，直接转 uint8 会截断信息。可视化前通常取绝对值并归一化，但判题接口保留浮点原值。边缘响应高不代表它一定属于需要的目标。',
    ['使用 cv2.Sobel(image, cv2.CV_32F, 1, 0, ksize=k) 得到 gx。','计算 gy 时把导数方向改为 (0,1)。','使用 cv2.magnitude 合并两个方向，返回三个数组。'],
    '''
    import cv2
    def solve(image, params):
        k = params["ksize"]
        gx = cv2.Sobel(image, cv2.CV_32F, 1, 0, ksize=k)
        gy = cv2.Sobel(image, cv2.CV_32F, 0, 1, ksize=k)
        magnitude = cv2.magnitude(gx, gy)
        return {"gx": gx, "gy": gy, "magnitude": magnitude}
    ''',['对 x、y 两个方向分别求导','保留有正负的浮点梯度','计算梯度幅值'],('T03','A01')),
_lesson('V05','积分图与矩形求和','先建一次前缀和，再用四个角快速回答多个区域统计问题。',
    "image 是 uint8 灰度图；params['roi']=(x,y,width,height)。返回字典 total、mean、count，依次为 ROI 像素和、平均值和像素数。",
    '积分图 integral[y,x] 累计左上方区域，并在最上方、最左侧额外填一行一列 0。半开区间矩形 [x,x+w)×[y,y+h) 的区域和为 I[y+h,x+w]-I[y,x+w]-I[y+h,x]+I[y,x]。坐标顺序仍是数组先行后列。整数求和避免 uint8 累加溢出；合法 ROI 保证非空。',
    ['cv2.integral 会返回高、宽都多 1 的数组。','解包 x、y、w、h，按四个角使用容斥计算 total。','count=w*h，mean=total/count。'],
    '''
    import cv2
    def solve(image, params):
        x, y, w, h = params["roi"]
        integral = cv2.integral(image, sdepth=cv2.CV_64F)
        total = integral[y+h,x+w] - integral[y,x+w] - integral[y+h,x] + integral[y,x]
        count = w*h
        return {"total": int(round(total)), "mean": float(total/count), "count": count}
    ''',['计算积分图','对四个边界角应用容斥','返回和、均值及面积'],('T02',)),
_lesson('V06','Otsu 自动选阈值','观察亮度分布中的双峰，用类间差异自动提出一个阈值。',
    "image 是 uint8 灰度图，亮目标位于暗背景上。返回字典 threshold 和 mask；mask 是 uint8 的 0/255 二值图。",
    'Otsu 遍历灰度阈值，把直方图分成两类并选择类间方差最大的界线。它是直方图方法：只看全局亮度频数，不考虑像素位置。前景面积占比很小、阴影或反光都会让它选错；两个主要亮度群比较分离时才更有参考意义。分割规则仍是原像素值大于阈值才输出白色。',
    ['调用 cv2.threshold(image, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)。','函数返回阈值和二值图，按题目字段组织结果。','将固定阈值与自动阈值放在相同输入上对比。'],
    '''
    import cv2
    def solve(image, params):
        threshold, mask = cv2.threshold(
            image, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
        return {"threshold": threshold, "mask": mask}
    ''',['使用灰度直方图自动选择一个阈值','用相同阈值规则生成掩膜','同时返回阈值和掩膜'],('T03','V01')),
]

VISION_IDS={item['id'] for item in VISION_LESSONS}
