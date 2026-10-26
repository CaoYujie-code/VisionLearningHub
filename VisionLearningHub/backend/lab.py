import uuid
import cv2
import numpy as np
from learning.engine import scene, read_image, write_image


def experiment(root, options):
    source = options.get('source', 'standard')
    if source.startswith('upload:'):
        key = source.split(':', 1)[1]
        if len(key) != 32 or any(c not in '0123456789abcdef' for c in key):
            raise ValueError('图片标识无效')
        image = read_image(root / 'uploads' / (key + '.png'))
    else:
        image, _, _ = scene(21)
        if source == 'dim':
            gradient = np.linspace(.18, .9, image.shape[1])[None, :, None]
            image = np.clip(image * gradient, 0, 255).astype(np.uint8)
        elif source == 'noise':
            noise = np.random.default_rng(17).normal(0, 20, image.shape)
            image = np.clip(image.astype(float) + noise, 0, 255).astype(np.uint8)
        elif source == 'same_color':
            cv2.rectangle(image, (65, 65), (190, 170), (50, 130, 45), -1)
        elif source != 'standard':
            raise ValueError('未知样例')
    method = options.get('method', 'hsv')
    threshold = int(options.get('threshold', 130))
    kernel = int(options.get('kernel', 3))
    low = int(options.get('low', 50)); high = int(options.get('high', 150))
    hue_low = int(options.get('hue_low', 30)); hue_high = int(options.get('hue_high', 95))
    block_size=int(options.get('block_size',15));c_value=int(options.get('c',4))
    if not (0 <= threshold <= 255 and kernel in range(1, 16, 2) and 0 <= low <= high <= 255 and 0 <= hue_low <= hue_high <= 179 and block_size in range(3,52,2) and 0<=c_value<=20):
        raise ValueError('参数超出范围，或下限高于上限')
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    if method=='adaptive' and block_size>min(gray.shape):
        raise ValueError('局部窗口不能超过图像的短边；请降低窗口尺寸或选择更大的图片')
    if method == 'gray':
        middle = gray; result = gray
        code = 'result = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)'
        meaning = '灰度表达亮度；颜色差异可能因此消失。适合亮度统计和后续边缘处理。'
    elif method == 'threshold':
        middle = gray
        _, result = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY)
        code = f'gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)\n_, result = cv2.threshold(gray, {threshold}, 255, cv2.THRESH_BINARY)'
        meaning = '白色表示亮度大于阈值。尝试阴影样例，观察同一物体是否被分成两部分。'
    elif method == 'adaptive':
        middle = gray
        result = cv2.adaptiveThreshold(gray,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY,block_size,c_value)
        code = f'result = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, {block_size}, {c_value})'
        meaning = '每个像素参考附近的加权亮度。窗口决定局部背景范围，C 调整界线；它不能区分亮度接近且颜色不同的物体。'
    elif method == 'otsu':
        middle = gray
        value,result = cv2.threshold(gray,0,255,cv2.THRESH_BINARY|cv2.THRESH_OTSU)
        code = f'threshold, result = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)\n# 本次自动阈值：{value:g}'
        meaning = f'Otsu 根据整张图的灰度直方图选界线；本次阈值为 {value:g}。它不使用空间位置，阴影或很小的目标可能导致分割失败。'
    elif method == 'histogram':
        middle = gray
        hist = cv2.calcHist([gray],[0],None,[256],[0,256]).ravel()
        canvas = np.full((300,512,3),(246,247,249),np.uint8)
        peak = max(float(hist.max()),1.0)
        cv2.line(canvas,(0,274),(511,274),(150,160,173),1)
        for i,value in enumerate(hist):
            x=round(i*511/255);y=274-round(float(value)*245/peak)
            cv2.line(canvas,(x,274),(x,y),(77,132,188),1)
        result = canvas
        code = 'hist = cv2.calcHist([gray], [0], None, [256], [0, 256]).ravel()\ncanvas = np.full((300, 512, 3), 246, np.uint8)\npeak = max(float(hist.max()), 1.0)\nfor i, value in enumerate(hist):\n    x = round(i * 511 / 255)\n    y = 274 - round(float(value) * 245 / peak)\n    cv2.line(canvas, (x, 274), (x, y), (77, 132, 188), 1)\nresult = canvas'
        meaning = '横轴是灰度值，纵轴是像素数量；直方图没有保存空间位置。两个峰可提示亮度群体，最终阈值仍需查看分割图。'
    elif method == 'equalize':
        middle = gray; result = cv2.equalizeHist(gray)
        code = 'gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)\nresult = cv2.equalizeHist(gray)'
        meaning = '直方图均衡拉开灰度分布以改善部分低对比度图像；它会改变亮度，也可能放大噪声，并不总能改善检测。'
    elif method == 'blur':
        middle = gray; result = cv2.GaussianBlur(gray, (kernel, kernel), 0)
        code = f'gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)\nresult = cv2.GaussianBlur(gray, ({kernel}, {kernel}), 0)'
        meaning = '平滑可以压低高频噪声，同时也会损失小纹理。核为 1 时不产生平滑效果。'
    elif method == 'median':
        middle = gray; result = cv2.medianBlur(gray,kernel)
        code = f'gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)\nresult = cv2.medianBlur(gray, {kernel})'
        meaning = '中值滤波常用于孤立的椒盐噪声。过大的窗口会擦掉细线和小孔；它和高斯加权平均对应不同的噪声特征。'
    elif method == 'bilateral':
        middle = gray; result = cv2.bilateralFilter(gray,kernel,60,60)
        code = f'gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)\nresult = cv2.bilateralFilter(gray, {kernel}, 60, 60)'
        meaning = '双边滤波同时考虑像素距离和亮度差，能保留部分边缘；计算较慢，参数不合适时也会丢失小结构。'
    elif method == 'sobel':
        gx = cv2.Sobel(gray,cv2.CV_32F,1,0,ksize=kernel)
        gy = cv2.Sobel(gray,cv2.CV_32F,0,1,ksize=kernel)
        magnitude = cv2.magnitude(gx,gy)
        scale = 255/max(float(np.percentile(magnitude,99.5)),1.)
        middle = np.clip(np.abs(gx)*scale,0,255).astype(np.uint8)
        result = np.clip(magnitude*scale,0,255).astype(np.uint8)
        code = f'gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize={kernel})\ngy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize={kernel})\nmagnitude = cv2.magnitude(gx, gy)\nscale = 255 / max(float(np.percentile(magnitude, 99.5)), 1)\nresult = np.clip(magnitude * scale, 0, 255).astype(np.uint8)'
        meaning = '中间图显示横向梯度绝对值，输出图显示梯度幅值。亮边不等于目标区域；转换为 uint8 时需要考虑缩放与信息截断。'
    elif method == 'canny':
        middle = cv2.GaussianBlur(gray, (kernel, kernel), 0)
        result = cv2.Canny(middle, low, high)
        code = f'gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)\nblur = cv2.GaussianBlur(gray, ({kernel}, {kernel}), 0)\nresult = cv2.Canny(blur, {low}, {high})'
        meaning = '白色表示边缘响应，不能直接当作物体填充区域。对比噪声与平滑核的影响。'
    elif method == 'hsv':
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        middle = cv2.bitwise_not(cv2.inRange(hsv, np.array([hue_low,35,15], np.uint8), np.array([hue_high,255,255], np.uint8)))
        k = np.ones((kernel,kernel), np.uint8)
        result = cv2.morphologyEx(cv2.morphologyEx(middle, cv2.MORPH_OPEN, k), cv2.MORPH_CLOSE, k)
        code = f'hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)\nbg = cv2.inRange(hsv, np.array([{hue_low},35,15], np.uint8), np.array([{hue_high},255,255], np.uint8))\nmask = cv2.bitwise_not(bg)\nk = np.ones(({kernel},{kernel}), np.uint8)\nopened = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k)\nresult = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, k)'
        meaning = '先排除绿色背景，再清理掩膜。绿色目标也会被排除；形态学无法恢复颜色分割已丢失的信息。'
    else:
        raise ValueError('未知处理方法')
    if method in ('adaptive','otsu','histogram','sobel'):
        code='gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)\n'+code
    if method=='histogram':
        code=code.replace('np.full((300, 512, 3), 246, np.uint8)',
                          'np.full((300, 512, 3), (246, 247, 249), np.uint8)')
        code=code.replace('peak = max(float(hist.max()), 1.0)',
                          'peak = max(float(hist.max()), 1.0)\ncv2.line(canvas, (0, 274), (511, 274), (150, 160, 173), 1)')
    folder = root / 'lab' / uuid.uuid4().hex; folder.mkdir(parents=True)
    paths = {}
    for name, array in [('input', image), ('middle', middle), ('output', result)]:
        path = folder / (name + '.png'); write_image(path, array); paths[name] = str(path)
    paths.update(method=method, code=code, meaning=meaning, width=image.shape[1], height=image.shape[0],
                 mean=round(float(result.mean()), 2), nonzero=round(float(np.count_nonzero(result) / result.size * 100), 2))
    return paths
