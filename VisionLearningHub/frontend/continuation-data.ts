export const nextRound = [
 {id:'T07',title:'把轮廓变成几何信息',outcome:'能从轮廓得到中心、顶点和面积。',input:'params.contours 中已有的轮廓；不是一张需要重新分割的照片。',output:'几何描述列表；每项含 center、points、area，points 是 N×2 数组。',first:'先只看一条轮廓的 m00；非零时求中心，确认它位于预期位置后再近似顶点。',check:'m00 为零时跳过；质心不是所有边界点坐标的简单平均。',terms:['centroid','contour','shape']},
 {id:'T08',title:'用一个点理解变换',outcome:'能解释先旋转再平移为何不同于反过来。',input:'N×2 点坐标、角度（度）、平移量 (dx,dy)。',output:'同样 N×2 的浮点坐标；绕原点旋转后平移。',first:'用 (1,0) 和 90 度手算：旋转后为 (0,1)，再加平移量；随后与程序比较。',check:'sin/cos 使用弧度；点按行保存时乘旋转矩阵的转置，不能用逐元素乘法代替。',terms:['radian','shape','affine']},
 {id:'T09',title:'区分覆盖和重叠',outcome:'能用累计次数解释两个指标。',input:'多边形布局、目标矩形 (x,y,w,h)；image 提供画布尺寸。',output:'含 coverage、overlap 的字典；分母都是目标面积。',first:'先画一片，再画两片相同的片，分别观察累计图中的 0、1、2。',check:'覆盖只统计目标内，重叠统计整个画布；累计图使用 int32，不能把 255 当覆盖次数。',terms:['mask','dtype','roi']},
 {id:'T10',title:'复用自己的评价函数',outcome:'能遍历候选并按两个约束选择布局。',input:'候选布局列表，以及你保存的 T09 实现。',output:'任一合法候选的原始下标；全不合法时返回 -1。',first:'先让 T09 通过，再单独打印一个候选的 coverage 和 overlap，确认取到的是当前候选。',check:'coverage≥0.98 且 overlap≤0.02 才接受；student 是平台调用已保存练习的适配接口，不是 OpenCV 函数。',terms:['dependency','index','threshold']},
 {id:'T11',title:'用图案辨认身份',outcome:'能比较每个模板的四种朝向并选最小误差。',input:'等尺寸灰度模板与打乱、旋转后的图块；仅含四种直角旋转。',output:'每个图块对应的模板下标列表，顺序与输入图块一致。',first:'先只选一片和一个模板，比较旋转 0、90、180、270 度后的四个均方误差。',check:'相减前转 float，避免 uint8 下溢；当前方法不处理任意旋转、遮挡和不同尺寸。',terms:['matching','dtype','index']},
 {id:'T12',title:'先对应，再平滑',outcome:'能说明多帧统计前为什么先统一目标顺序。',input:'多帧中心坐标；目标静止、沿 x 分离，每帧都能看到全部目标。',output:'按 x 升序排列的稳定中心坐标数组。',first:'拿两帧交换过目标顺序的坐标，先按 x 排序，检查同一列是否仍对应同一个目标。',check:'沿时间维求中值；目标交叉、漏检或移动时不能直接套用本题的排序策略。',terms:['matching','axis','shape']},
 {id:'T13',title:'用已知点建立坐标映射',outcome:'能分清拟合点与独立检查点。',input:'成对的视觉/平台坐标，以及未参与拟合的 checks 点。',output:'checks 映射到平台后的 N×2 坐标；共线标定点应抛出 ValueError。',first:'先在纸上给视觉点加一列 1，检查点是否共线，再求映射；最后用另一个已知点验证。',check:'至少三组不共线对应点；拟合方向为视觉到平台，训练点拟合得好不等于新位置准确。',terms:['affine','rank','shape']},
 {id:'T14',title:'把四步接成检测器',outcome:'能定位颜色、清理、轮廓、几何描述中的首个错误。',input:'BGR 图和本次参数；复用已保存的 T04、T05、T06、T07。',output:'含 mask（二值图）和 pieces（几何描述列表）的字典。',first:'先核对四道前置题，再只接通 T04→T05；看清理后的掩膜后再接 T06 和 T07。',check:'T07 的 contours 放进子参数；空场景返回空列表。student 是平台适配接口，独立工程中改为普通模块函数调用。',terms:['dependency','mask','contour']},
] as const;

export const extensionTerms = [
 {id:'centroid',name:'centroid / moments · 质心与图像矩',meaning:'图像矩把形状的空间分布汇总为数值；m00 非零时，m10/m00 与 m01/m00 给出质心坐标。',example:'均匀矩形从 (0,0) 到 (10,4)，中心为 (5,2)。',pitfall:'顶点平均不总等于面积质心；除法前检查 m00。'},
 {id:'radian',name:'radian · 弧度',meaning:'与度数不同的角度单位；NumPy 的 sin/cos 使用弧度。',example:'np.deg2rad(90) 约为 1.5708；先转换再计算三角函数。',pitfall:'本题图像 y 轴向下，正角在画面上表现为顺时针。'},
 {id:'affine',name:'affine · 仿射映射',meaning:'用线性变换加平移映射二维坐标，能描述旋转、缩放、剪切和平移。',example:'X=2*u+10，Y=3*v-5，把 (1,2) 映射成 (12,1)。',pitfall:'先标明输入输出坐标系；一般透视变形不能只用仿射模型描述。'},
 {id:'rank',name:'rank · 矩阵的秩',meaning:'反映矩阵里有多少独立信息。T13 的 [u,v,1] 设计矩阵需要三列独立才能确定二维仿射映射。',example:'三个标定点都在一条直线上，无法唯一确定整个平面的映射。',pitfall:'点数足够仍可能共线；还要用独立点检查映射误差。'},
 {id:'matching',name:'matching · 建立对应关系',meaning:'先确认两个集合中的哪些元素代表同一对象，再比较或统计。',example:'两帧各有两片纸，但列表顺序交换；直接逐项平均会混合两片纸的坐标。',pitfall:'排序只在本题约定的条件下能建立对应，不等于通用跟踪。'},
 {id:'dependency',name:'dependency / student · 前置题与复用',meaning:'组合题运行你保存的前置题实现。student 是平台适配接口，不是 Python、NumPy 或 OpenCV 原生函数。',example:'T14 把 T06 返回的轮廓放入子参数，再交给 T07；前置代码不完整会导致组合失败。',pitfall:'普通工程应导入自己的模块并调用函数；不要把 student 当成可直接复制到任意 Python 文件的库函数。'},
] as const;

export const learningPaths = [
 {id:'detector',title:'做出第一个碎片检测器',goal:'把前景掩膜接成轮廓与几何信息，最终交付 mask 和 pieces。',prepare:['T04','T05','T06'],boundary:'本路线验收视觉检测，不代表完成机械抓取或真实设备闭环。',steps:[
  {id:'T04',why:'找到前景，先明确掩膜含义。'},{id:'T05',why:'清理噪点，避免干扰变成假目标。'},{id:'T06',why:'把区域变成独立轮廓。'},{id:'T07',why:'把轮廓变成中心、顶点与面积。'},{id:'T14',why:'复用自己的四道实现，完成组合验收。'}]},
 {id:'geometry',title:'理解拼图几何与定位',goal:'学习位置变换、布局评价、身份与多帧对应，最后建立坐标映射。',prepare:['P02','T06'],boundary:'这些是拼图求解与定位的组成部分，尚不等于任意拼图求解器或实机标定完成。',steps:[
  {id:'T07',why:'取得可计算的几何描述。'},{id:'T08',why:'预测旋转和平移后的点。'},{id:'T09',why:'区分覆盖不足与互相重叠。'},{id:'T10',why:'复用评价函数筛选合法布局。'},{id:'T11',why:'外形相同时用图案区分身份。'},{id:'T12',why:'建立帧间对应后再稳定坐标。'},{id:'T13',why:'把视觉坐标映射到平台坐标并独立检查。'}]},
 {id:'detection',title:'准备 YOLO 数据与后处理',goal:'读懂标签、框坐标、去重与评价，知道每个数字从哪里来。',prepare:['P01','P02'],boundary:'离线使用已给定数据，不启动模型训练，不把这些指标当作完整 mAP。',steps:[
  {id:'Y01',why:'先找出非法标签。'},{id:'Y04',why:'检查数据划分是否泄漏。'},{id:'Y02',why:'把补边缩放后的框还原到原图。'},{id:'A04',why:'用 IoU 衡量两个框的重合。'},{id:'A05',why:'理解 NMS 如何删除重复预测。'},{id:'Y03',why:'先在二分类样本上理解误报与漏报。'},{id:'Y05',why:'把类别、IoU 与一对一匹配连接起来。'}]},
 {id:'embedded',title:'准备嵌入式视觉数据',goal:'从离线日志、图像行缓冲区与耗时记录练习设备排查的基础。',prepare:['P01','P02'],boundary:'可在 Windows 练习；Linux 命令、相机采集与开发板联调仍需在真实环境另行完成。',steps:[
  {id:'L01',why:'从级别字段定位日志异常。'},{id:'L02',why:'区分行步幅与有效像素，正确还原图像。'},{id:'L03',why:'按帧汇总耗时，观察延迟和吞吐差别。'}]},
] as const;
