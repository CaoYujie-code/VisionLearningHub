export const firstRound = [
 {id:'P01',title:'用循环筛选',outcome:'能分清索引与面积，并返回筛选结果。',input:'已经准备好的面积列表和最小面积；这题先不处理图像。',output:'满足条件的原始下标列表，按原顺序排列；没有目标时返回空列表。',first:'先用一个只有 3 项的列表，在纸上标出 0、1、2 三个下标，再逐项判断。',check:'恰好等于最小面积也要保留；返回下标，而不是面积。',terms:['index','return','params']},
 {id:'P02',title:'裁剪与统计数组',outcome:'能按行列裁剪，并统计局部亮度。',input:'一张灰度图，ROI 的 x/y/宽/高，以及亮度阈值。',output:'包含 mean、bright_count、shape 三个字段的字典；shape 为 [高,宽]。',first:'先只检查 ROI 的 shape；高、宽正确以后，再写平均值和亮像素计数。',check:'严格大于阈值才计数；白色掩膜的数值和不是像素个数。',terms:['shape','roi','axis']},
 {id:'T01',title:'认识图像和像素',outcome:'能说出宽高、通道，以及一个像素保存了什么。',input:'params 中的图片路径。使用 NumPy/OpenCV 原生读图，再查看数组。',output:'包含 width、height、channels、pixel 的字典；pixel 是左上角的 BGR 列表。',first:'先确认图像读成功，再看 image.shape；按高、宽、通道的顺序读它。',check:'数组的高在前、宽在后；pixel 需要列表，不是单个亮度值。',terms:['shape','dtype','bgr']},
 {id:'T02',title:'选出感兴趣区域',outcome:'能把 x/y 坐标转换成数组切片。',input:'原图与 ROI 参数 (x,y,width,height)。',output:'裁剪出的图像数组；颜色通道保持不变。',first:'先画出左上角 (x,y)，再标出向右 width、向下 height 的范围。',check:'数组先写 y 再写 x；切片包含起点、不包含终点。',terms:['roi','shape','copy']},
 {id:'T03',title:'用亮度分离区域',outcome:'能解释灰度图为什么变成黑白掩膜。',input:'彩色图和亮度阈值；先转换为灰度。',output:'单通道 uint8 掩膜；亮于阈值为 255，其余为 0。',first:'先观察灰度图，再预测提高阈值后白色区域会变大还是变小。',check:'cv2.threshold 返回两个值；这题需要返回其中的结果图。',terms:['threshold','mask','dtype']},
 {id:'T04',title:'用颜色分离背景',outcome:'能区分选中背景与得到前景这两步。',input:'BGR 图和 HSV 背景颜色范围 lower/upper。',output:'前景为 255、背景为 0 的单通道掩膜。',first:'先找到绿色背景的掩膜，再看取反后纸片和内部黑字是否保留下来。',check:'inRange 选出的是背景，需要取反；BGR 和 HSV 的数值含义不同。',terms:['hsv','bgr','mask']},
 {id:'T05',title:'清理噪点和小孔',outcome:'能说明开运算与闭运算分别改变了哪里。',input:'已经是黑白的含噪掩膜，以及奇数核尺寸。',output:'清理后的同尺寸 uint8 二值图。',first:'先圈出小白点和小黑孔；分别观察开、闭运算，不要一口气只看最终图。',check:'核太大可能删掉真实小目标或合并相邻块；干净不等于正确。',terms:['kernel','mask','parameter']},
 {id:'T06',title:'提取轮廓',outcome:'能从区域图得到独立边界，并排除小区域。',input:'单通道掩膜和最小轮廓面积。',output:'轮廓列表；每条轮廓是坐标点数组，不是画好边界的图片。',first:'先看 findContours 的轮廓数量，再逐条查看面积，最后做筛选。',check:'轮廓几何面积不一定等于白色像素数；返回顺序不代表物体身份。',terms:['contour','index','return']},
] as const;

export const terms = [
 {id:'image',name:'image · 图像数组',meaning:'图像在程序里是一组数值，变量名通常叫 image。灰度像素存一个值，彩色像素存多个通道值。',example:'image[2,5] 读取第 2 行、第 5 列（下标从 0 开始）的像素。',pitfall:'在数组里先写 y/行，再写 x/列。'},
 {id:'params',name:'params · 参数字典',meaning:'题目提供的配置，例如阈值、ROI 或图片路径。不同验收样例会改变它们。',example:'params["threshold"] 取出本次阈值。',pitfall:'按题目提供的键读取，不把演示中的数值写死。'},
 {id:'index',name:'index · 下标',meaning:'某个元素在列表或数组里的位置，从 0 开始。下标和元素的值是两件事。',example:'areas=[20,80,120]，areas[1] 的值是 80。',pitfall:'要求返回下标时，80 对应的答案是 1。'},
 {id:'shape',name:'shape · 数组形状',meaning:'每一维有多少个元素。图像通常按高、宽、通道排列。',example:'(120,200,3) 表示高 120、宽 200、3 个通道；灰度图通常是 (120,200)。',pitfall:'不要把 shape 的前两项当成宽、高。'},
 {id:'dtype',name:'dtype / uint8 · 数值类型',meaning:'dtype 说明一个数如何保存。uint8 是无符号 8 位整数，只能保存 0~255。',example:'黑白掩膜常用 uint8；带负数的梯度常用 float32。',pitfall:'uint8 相减可能回绕；需要有符号差值时先转换类型。'},
 {id:'roi',name:'ROI · 感兴趣区域',meaning:'当前只想处理的那块矩形区域，用 x、y、宽、高描述。',example:'(10,20,30,40) 对应 image[20:60,10:40]。',pitfall:'切片的右端不包含，ROI 自己的坐标回原图时还要加偏移。'},
 {id:'mask',name:'mask · 掩膜',meaning:'用一个单通道数组表示哪些像素被选中。课程中通常用 255 选中、0 不选中。',example:'白色区域可能表示纸片，也可能表示绿色背景，要看本步约定。',pitfall:'颜色为白不自动代表前景；先确认当前 mask 的含义。'},
 {id:'threshold',name:'threshold · 阈值',meaning:'划分两种情况的边界值，必须连同比较符号一起理解。',example:'亮度 100 与阈值 100：条件 >100 不保留，>=100 则保留。',pitfall:'不能把不同题里的 > 和 >= 混用。'},
 {id:'bgr',name:'BGR · 通道顺序',meaning:'OpenCV 常用彩色数组的三个通道依次为蓝、绿、红。',example:'uint8 BGR 的 [0,0,255] 表示红色。',pitfall:'交给需要 RGB 的显示库前，先明确是否需要转换。'},
 {id:'hsv',name:'HSV · 色相、饱和度、明度',meaning:'另一种描述颜色的方式。本平台标准 uint8 HSV 的 H 为 0~179，S/V 为 0~255。',example:'用色相范围选颜色，再用 S/V 排除灰色或过暗区域。',pitfall:'红色可能跨越 H 的零点，不能只用一个普通连续区间。'},
 {id:'return',name:'return / print · 返回与打印',meaning:'return 把结果交给调用函数的程序；print 把内容写进控制台，方便观察。',example:'print(result) 会显示 result；return result 才把它交给验收程序。',pitfall:'只打印而没有 return，函数通常返回 None。'},
 {id:'axis',name:'axis · 沿哪一维计算',meaning:'二维数组 axis=0 沿行方向聚合，保留各列；axis=1 沿列方向聚合，保留各行。',example:'每行是一帧的四阶段耗时，sum(axis=1) 得到每帧总耗时。',pitfall:'先写清每行每列代表什么，再选轴。'},
 {id:'copy',name:'copy · 独立副本',meaning:'把数据复制到独立存储中。切片经常与原数组共享数据。',example:'roi=image[y:y+h,x:x+w].copy() 后修改 roi，不会修改原图。',pitfall:'数组看起来相同，不代表它们的内存相互独立。'},
 {id:'kernel',name:'kernel · 邻域核',meaning:'算法处理一个位置时使用的邻域形状与大小。滤波核和形态学核的作用不同。',example:'3×3 核查看附近 9 个位置；更大的核会影响更大的范围。',pitfall:'核越大不一定越好，可能抹掉细节或合并物体。'},
 {id:'contour',name:'contour · 轮廓',meaning:'描述物体边界的一串坐标点。画出的线只是这些点的可视化。',example:'轮廓点常见形状为 N×1×2，最后两个数是 x 和 y。',pitfall:'轮廓列表与标注图片不是同一种返回值。'},
 {id:'parameter',name:'参数实验 · 只改一个量',meaning:'固定样例，改变一个明确的变量，观察结果怎么变化。',example:'只提高阈值，比较白色区域是否减少；先不同时改滤波核。',pitfall:'同时改多个参数后，很难判断变化是由哪一个引起的。'},
 {id:'seed',name:'seed · 样例编号与随机种子',meaning:'平台用固定种子生成可重复样例，方便每次对照相同输入。',example:'单次运行显示 seed 17；多样例验收使用其他输入检查泛化。',pitfall:'记住一张图的尺寸或答案，不能证明算法适用于其他图。'},
 {id:'verify',name:'自评、导入与验收',meaning:'自评记录你是否能解释；导入展示本地保存的中间结果；多样例验收检查原题代码。',example:'参考脚本也能生成 results.zip，所以导入成功不会自动授予通关。',pitfall:'教学图、自己的运行结果和正式验收成绩要分别阅读。'},
] as const;

export const troubleshooting = [
 {id:'start',name:'不知道从哪里写',steps:['先用一句话说出输入与最终返回值；暂时不写完整算法。','只实现第一个处理步骤，观察 shape、dtype 或一个小样本。','查看函数的最小示例，再回到本题接上自己的输入。'],tab:'函数与场景',action:'查看本题函数'},
 {id:'error',name:'运行报错或出现 None',steps:['先读错误类型与行号，定位第一次失败的调用。','NotImplementedError 通常表示模板还没完成；写好实现后再替换该占位语句。','如果代码只 print 了结果，检查是否按约定 return；读图失败则先检查路径和解码结果。'],tab:'知识与提示',action:'查看本题提示'},
 {id:'image',name:'图像全黑、错位或颜色不对',steps:['先看原始数值范围和非零数量，确认全黑是否为合法空结果。','检查行列顺序、BGR/HSV 转换和当前掩膜表示前景还是背景。','在最先不符合预期的步骤停下，每次只改一个参数。'],tab:'逐步图解',action:'观察中间结果'},
 {id:'verify',name:'运行成功但验收未通过',steps:['先读报告中第一条未通过项，核对返回类型、尺寸和字段名。','再检查边界等号、空输入，以及是否写死了样例参数。','修正后先运行当前样例，再做多样例验收；修改代码后需要重新验收。'],tab:'任务',action:'核对原题约定'},
] as const;
