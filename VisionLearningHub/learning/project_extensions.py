"""Additional scenarios: explicit generated objects on attributed photographic surfaces."""
import cv2
import numpy as np

COLORS = '''def process_image(image, input_dir, output_dir, stem, config):
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    objects = []
    overlay = image.copy()
    for name, bands in config['bands'].items():
        mask = np.zeros(image.shape[:2], np.uint8)
        for low, high in bands:
            mask |= cv2.inRange(hsv, np.array(low), np.array(high))
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            if cv2.contourArea(contour) < config['min_area']: continue
            m = cv2.moments(contour)
            center = [m['m10']/m['m00'], m['m01']/m['m00']]
            objects.append({'color':name, 'center':center})
            cv2.drawContours(overlay, [contour], -1, (255,255,255), 2)
    return {'objects':objects}, overlay
'''

MEASURE = '''def process_image(image, input_dir, output_dir, stem, config):
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    ruler = cv2.inRange(hsv, np.array([100,120,80]), np.array([130,255,255]))
    contours, _ = cv2.findContours(ruler, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    overlay = image.copy()
    if not contours:
        return {'status':'no_reference','sizes_mm':[]}, overlay
    x,y,w,h = cv2.boundingRect(max(contours,key=cv2.contourArea))
    pixels_per_mm = w/config['reference_mm']
    mask = cv2.inRange(image, np.array([180,180,180]), np.array([255,255,255]))
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    sizes = []
    for contour in contours:
        if cv2.contourArea(contour)<200: continue
        rect = cv2.minAreaRect(contour)
        sizes.append(sorted([v/pixels_per_mm for v in rect[1]],reverse=True))
        cv2.drawContours(overlay,[np.int32(cv2.boxPoints(rect))],-1,(0,0,255),2)
    return {'status':'ok','sizes_mm':sizes}, overlay
'''

LABEL = '''def process_image(image, input_dir, output_dir, stem, config):
    template = read_image(input_dir/'_template.png')
    orb = cv2.ORB_create(nfeatures=1800, edgeThreshold=8, fastThreshold=8)
    ka, da = orb.detectAndCompute(cv2.cvtColor(template,cv2.COLOR_BGR2GRAY),None)
    kb, db = orb.detectAndCompute(cv2.cvtColor(image,cv2.COLOR_BGR2GRAY),None)
    corners = []; overlay = image.copy()
    if da is not None and db is not None and len(db)>=2:
        pairs = cv2.BFMatcher(cv2.NORM_HAMMING).knnMatch(da,db,k=2)
        good = [pair[0] for pair in pairs if len(pair)==2 and pair[0].distance<config['ratio']*pair[1].distance]
        if len(good)>=8:
            a = np.float32([ka[m.queryIdx].pt for m in good])
            b = np.float32([kb[m.trainIdx].pt for m in good])
            matrix, inliers = cv2.findHomography(a,b,cv2.RANSAC,3)
            if matrix is not None and int(inliers.sum())>=8:
                h,w = template.shape[:2]
                polygon = cv2.perspectiveTransform(np.float32([[[0,0],[w-1,0],[w-1,h-1],[0,h-1]]]),matrix)[0]
                if np.isfinite(polygon).all() and cv2.isContourConvex(polygon) and abs(cv2.contourArea(polygon))>1000:
                    corners = polygon.tolist()
                    cv2.polylines(overlay,[np.int32(polygon)],True,(0,255,255),2)
    return {'corners':corners,'decision':'present' if corners else 'missing'}, overlay
'''

PUZZLE = '''def process_image(image, input_dir, output_dir, stem, config):
    board = read_image(input_dir/'_board.png')
    size = config['tile_size']; assignments = []; overlay = image.copy()
    targets = [board[(i//3)*size:(i//3+1)*size,(i%3)*size:(i%3+1)*size] for i in range(9)]
    for slot in range(9):
        y,x = (slot//3)*size,(slot%3)*size
        tile = image[y:y+size,x:x+size]
        if float(tile.std())<2: continue
        candidates = []
        for target,base in enumerate(targets):
            for turns in range(4):
                aligned = np.rot90(tile,-turns).astype(np.float32)
                difference = aligned-base.astype(np.float32)
                score = float(np.mean(np.abs(difference-np.median(difference))))
                candidates.append((score,target,turns*90))
        score,target,rotation = min(candidates)
        if score>config['max_error']: continue
        assignments.append({'slot':slot,'target':target,'rotation':rotation})
        cv2.putText(overlay,str(target),(x+8,y+22),0,.6,(0,0,255),2)
    valid = len(assignments)==9 and len({a['target'] for a in assignments})==9
    return {'assignments':assignments,'valid':valid}, overlay
'''

EXTRA_PROJECTS = [
    dict(id='E05',title='颜色零件分拣与批量统计',scenario='为分拣工位识别红、绿、蓝零件，输出类别和中心。比较曝光变化、小噪点与空工位下的表现。',
         output='records 每项含 file、objects=[{color:red/green/blue,center:[x,y]}]；中心误差≤4px，类别与数量准确；坏图记录decode_failed；每张有效图保存overlays/同名.png。',
         stages=['确定颜色类别和BGR/HSV约定。','读取图片并检查坏文件。','分割颜色、过滤小区域并计算中心。','绘制类别与位置，保存结构化结果。','检查曝光、噪点和空场景，分析真实反光的影响。'],
         limits='公开砖墙纹理上的人工彩色零件，不是实拍产线；不覆盖严重反光、重叠和跨相机色彩差异。',prerequisites=['V13','V10','T07'],assets=['brick.png'],
         config=dict(min_area=150,bands={'red':[[[0,100,60],[10,255,255]],[[170,100,60],[179,255,255]]],'green':[[[40,100,60],[85,255,255]]],'blue':[[[100,100,60],[130,255,255]]]}),algorithm=COLORS),
    dict(id='E06',title='平面零件尺寸测量与标尺检查',scenario='在正视、同一平面的图像中利用已知长度蓝色标尺测量白色矩形零件，标尺缺失时拒绝输出物理尺寸。',
         output='records 每项含 file、status=ok/no_reference、sizes_mm=[[长,宽],...]，长度降序，单位mm，允许1mm误差；无标尺返回空列表；保存overlay并记录坏图。',
         stages=['明确同平面正视条件与标尺实际长度。','读取图像并定位蓝色标尺。','根据标尺像素宽度建立比例，测量旋转矩形。','输出毫米尺寸与定位图，不把像素当毫米。','验证不同尺寸、旋转、空场景和缺失标尺。'],
         limits='教学合成平面零件，自动验收只含正视同平面场景；倾斜视角需先标定/校正，不能承诺现场计量精度。',prerequisites=['T07','A03'],assets=['gravel.png'],config=dict(reference_mm=50),algorithm=MEASURE),
    dict(id='E07',title='纹理标签定位与漏贴检查',scenario='根据模板定位具有纹理的标签，在旋转、缩放和位置变化下输出四角；未贴标签时返回缺失。',
         output='读取_template.png；records 每项含 file、corners（模板左上/右上/右下/左下在场景中的位置）、decision=present/missing；四角最大误差≤10px，缺失返回[]；保存overlay和坏图记录。',
         stages=['区分模板坐标和场景坐标。','读取模板与待检图。','提取特征、筛选匹配并用RANSAC估计几何关系。','检查内点和四边形，将模板四角映射到场景。','验证旋转、缩放和漏贴；解释低纹理标签的局限。'],
         limits='真实硬币纹理制作的教学标签，场景由程序投影生成；不覆盖低纹理、重复标签或严重遮挡。',prerequisites=['V12','A03'],assets=['coins.png'],config=dict(ratio=.72),algorithm=LABEL),
    dict(id='E08',title='九宫格拼图身份与方向恢复',scenario='读取标准图和打乱的九宫格图，为每个槽位识别原图块及恢复方向，检测缺块或重复块并拒绝有效排列。',
         output='读取_board.png；records 每项含 file、assignments=[{slot,target,rotation}]和valid。slot/target为行优先0..8；rotation为恢复原方向所需顺时针0/90/180/270度；缺失槽不输出；重复/缺块时valid=false。保存overlay和坏图记录。',
         stages=['约定九宫格槽位、图块ID和旋转方向。','按固定网格切分标准图与待测图。','比较四种旋转，补偿整体亮度差。','输出匹配与方向，检查身份唯一性。','处理完整、缺块、重复块；说明自由散落拼图还需哪些模块。'],
         limits='公开硬币照片切成固定网格后生成；不含自由散落块检测、机械执行或特定电赛规则。重复块不强行分配成完整排列。',prerequisites=['T11','A04'],assets=['coins.png'],config=dict(tile_size=96,max_error=8),algorithm=PUZZLE),
]

def prepare_extra(key,seed,folder,add,read,write):
    rng=np.random.default_rng(seed)
    if key=='E05':
        for i in range(4):
            image=(cv2.resize(read('brick.png'),(360,260))*.22).astype(np.uint8);objects=[]
            for j in range(0 if i==3 else 2+i):
                x,y=55+75*(j%4)+seed%9,60+110*(j//4)+i*10
                name=['red','green','blue'][(j+i+seed)%3];color={'red':(0,0,220),'green':(0,210,0),'blue':(210,0,0)}[name]
                cv2.circle(image,(x,y),18+i,color,-1);objects.append(dict(color=name,center=[x,y]))
            for _ in range(12):
                x,y=rng.integers([0,0],[360,260]);cv2.circle(image,(int(x),int(y)),1,(0,0,200),-1)
            image=np.clip(image.astype(float)*(.7+.1*(seed%3)),0,255).astype(np.uint8)
            add(i,image,dict(objects=objects),'人工彩色零件/小噪点/曝光变化，背景为公开纹理')
    elif key=='E06':
        for i in range(4):
            image=(cv2.resize(read('gravel.png'),(360,260))*.2).astype(np.uint8);sizes=[]
            if i!=2:cv2.rectangle(image,(20,20),(119,31),(220,0,0),-1)
            if i!=3:
                long,short=80+seed%11+12*i,40+seed%7
                box=cv2.boxPoints(((190,150),(long,short),float(10+i*13+seed%9)))
                cv2.fillConvexPoly(image,np.int32(box),(230,230,230))
                if i!=2:sizes=[[long/2,short/2]]
            add(i,image,dict(status='no_reference' if i==2 else 'ok',sizes_mm=sizes),'合成同平面矩形/旋转/空工位/缺失蓝色标尺')
    elif key=='E07':
        template=cv2.resize(read('coins.png'),(200,160));write(folder/'_template.png',template)
        for i in range(4):
            image=np.full((420,520,3),32+seed%15,np.uint8);corners=[]
            if i!=3:
                angle=(-18,8,23)[i]+seed%5;scale=(.85,1,1.12)[i]
                matrix=cv2.getRotationMatrix2D((100,80),angle,scale);matrix[:,2]+=np.array([145+seed%20,105+i*10])
                image=cv2.warpAffine(template,matrix,(520,420),dst=image,borderMode=cv2.BORDER_TRANSPARENT)
                corners=cv2.transform(np.float32([[[0,0],[199,0],[199,159],[0,159]]]),matrix)[0].tolist()
            add(i,image,dict(corners=corners,decision='present' if corners else 'missing'),'实拍硬币纹理标签的旋转缩放合成场景/漏贴')
    elif key=='E08':
        board=cv2.resize(read('coins.png'),(288,288));write(folder/'_board.png',board)
        for i in range(4):
            image=np.full_like(board,20);order=rng.permutation(9).tolist();assignments=[]
            if i==2:order[1]=order[0]
            for slot,target in enumerate(order):
                if i==3 and slot==4:continue
                turns=int(rng.integers(0,4));tile=board[(target//3)*96:(target//3+1)*96,(target%3)*96:(target%3+1)*96]
                tile=np.clip(np.rot90(tile,turns).astype(float)+(seed%9)-4,0,255).astype(np.uint8)
                image[(slot//3)*96:(slot//3+1)*96,(slot%3)*96:(slot%3+1)*96]=tile
                assignments.append(dict(slot=slot,target=target,rotation=turns*90))
            add(i,image,dict(assignments=assignments,valid=i<2),'固定网格的照片裁片：乱序、90度旋转、亮度、重复或缺块')

def assess_extra(key,record,target):
    if key=='E05':
        objects=record.get('objects');expected=target['objects']
        if not isinstance(objects,list) or len(objects)!=len(expected):return False
        used=set()
        for obj in expected:
            match=None
            for j,other in enumerate(objects):
                if j in used or not isinstance(other,dict) or other.get('color')!=obj['color']:continue
                center=np.asarray(other.get('center'),dtype=float)
                if center.shape==(2,) and np.isfinite(center).all() and np.linalg.norm(center-obj['center'])<=4:match=j;break
            if match is None:return False
            used.add(match)
        return True
    if key=='E06':
        sizes=np.asarray(record.get('sizes_mm'),dtype=float);expected=np.asarray(target['sizes_mm'],dtype=float)
        return record.get('status')==target['status'] and sizes.shape==expected.shape and np.isfinite(sizes).all() and (sizes.size==0 or np.max(np.abs(sizes-expected))<=1)
    if key=='E07':
        corners=np.asarray(record.get('corners'),dtype=float);expected=np.asarray(target['corners'],dtype=float)
        return record.get('decision')==target['decision'] and corners.shape==expected.shape and np.isfinite(corners).all() and (corners.size==0 or np.max(np.linalg.norm(corners-expected,axis=1))<=10)
    if key=='E08':
        assignments=record.get('assignments')
        if not isinstance(assignments,list) or not all(isinstance(a,dict) and all(type(a.get(k)) is int for k in ('slot','target','rotation')) for a in assignments):return False
        normalize=lambda values:sorted((v['slot'],v['target'],v['rotation']) for v in values)
        return type(record.get('valid')) is bool and record['valid']==target['valid'] and normalize(assignments)==normalize(target['assignments'])
    raise ValueError(key)
