"""Engineering briefs and plain Python source bundles (no platform imports in student code)."""
import json
from textwrap import dedent

MAIN = '''"""普通命令行程序；可直接在 VS Code / PyCharm 运行。"""
import argparse
import json
from pathlib import Path
from pipeline import run_batch

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', default='data/sample')
    parser.add_argument('--output', default='output')
    parser.add_argument('--config', default='config.json')
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text(encoding='utf-8'))
    run_batch(Path(args.input), Path(args.output), config)

if __name__ == '__main__':
    main()
'''

IMAGING = '''from pathlib import Path
import cv2
import numpy as np

def read_image(path):
    image = cv2.imdecode(np.fromfile(str(path), np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError('无法解码图片：' + Path(path).name)
    return image

def write_image(path, image):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    ok, data = cv2.imencode('.png', image)
    if not ok:
        raise ValueError('图片编码失败')
    data.tofile(str(path))
'''

BATCH = '''import json
import cv2
import numpy as np
from imaging import read_image, write_image

{algorithm}

def run_batch(input_dir, output_dir, config):
    output_dir.mkdir(parents=True, exist_ok=True)
    records = []
    for path in sorted(input_dir.glob('*.png')):
        if path.name.startswith('_'):
            continue
        try:
            image = read_image(path)
        except ValueError:
            records.append({{'file':path.name, 'error':'decode_failed'}})
            continue
        result, overlay = process_image(image, input_dir, output_dir, path.stem, config)
        records.append({{'file':path.name, **result}})
        write_image(output_dir / 'overlays' / (path.stem+'.png'), overlay)
    (output_dir / 'results.json').write_text(json.dumps({{'records':records}},ensure_ascii=False,indent=2),encoding='utf-8')
'''

COINS = '''def detect_centers(image, config):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    smooth = cv2.GaussianBlur(gray, (3,3), 0)
    edges = cv2.Canny(smooth, config['edge_low'], config['edge_high'])
    mask = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, np.ones((3,3),np.uint8))
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    centers = []
    for contour in contours:
        if config['min_area'] <= cv2.contourArea(contour) <= config['max_area']:
            moment = cv2.moments(contour)
            if moment['m00']:
                centers.append([moment['m10']/moment['m00'], moment['m01']/moment['m00']])
    return sorted(centers, key=lambda p:(p[1],p[0]))

def process_image(image, input_dir, output_dir, stem, config):
    centers = detect_centers(image, config)
    overlay = image.copy()
    for x,y in centers:
        cv2.circle(overlay, (round(x),round(y)), 8, (0,0,255),2)
    return {'centers':centers,'count':len(centers)}, overlay
'''

DEFECTS = '''def find_defects(image, reference, config):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY).astype(np.float32)
    base = cv2.cvtColor(reference, cv2.COLOR_BGR2GRAY).astype(np.float32)
    if gray.shape != base.shape:
        raise ValueError('模板和待检图尺寸不一致')
    difference = gray-base
    difference -= np.median(difference)
    mask = (np.abs(difference) > config['difference_threshold']).astype(np.uint8)*255
    mask = cv2.morphologyEx(mask,cv2.MORPH_CLOSE,np.ones((3,3),np.uint8))
    contours,_ = cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    return [list(cv2.boundingRect(c)) for c in contours if cv2.contourArea(c)>=config['min_area']]

def process_image(image, input_dir, output_dir, stem, config):
    reference = read_image(input_dir / '_reference.png')
    boxes = find_defects(image,reference,config)
    overlay = image.copy()
    for x,y,w,h in boxes:
        cv2.rectangle(overlay,(x,y),(x+w-1,y+h-1),(0,0,255),2)
    return {'boxes':boxes,'decision':'reject' if boxes else 'accept'},overlay
'''

DOCUMENTS = '''def locate_page(image, config):
    gray = cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)
    mask = cv2.threshold(gray,config['paper_threshold'],255,cv2.THRESH_BINARY)[1]
    contours,_ = cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    for contour in sorted(contours,key=cv2.contourArea,reverse=True):
        if cv2.contourArea(contour)<config['min_area']:
            continue
        polygon = cv2.approxPolyDP(contour,.02*cv2.arcLength(contour,True),True)
        if len(polygon)==4:
            points = polygon.reshape(4,2).astype(np.float32)
            # 本项目视角适中，可按左右两组再按y排序；极端旋转需重新设计点序。
            left = sorted(points[np.argsort(points[:,0])[:2]],key=lambda p:p[1])
            right = sorted(points[np.argsort(points[:,0])[2:]],key=lambda p:p[1])
            return np.array([left[0],right[0],right[1],left[1]],np.float32)
    return None

def process_image(image, input_dir, output_dir, stem, config):
    corners = locate_page(image,config)
    overlay = image.copy()
    if corners is None:
        return {'corners':[]},overlay
    w,h = config['width'],config['height']
    target = np.float32([[0,0],[w-1,0],[w-1,h-1],[0,h-1]])
    matrix = cv2.getPerspectiveTransform(corners,target)
    rectified = cv2.warpPerspective(image,matrix,(w,h))
    write_image(output_dir/'rectified'/(stem+'.png'),rectified)
    cv2.polylines(overlay,[np.rint(corners).astype(np.int32)],True,(0,0,255),2)
    return {'corners':corners.tolist()},overlay
'''

TRACKING = '''import json
import cv2
import numpy as np
from imaging import read_image, write_image

def detect_centers(image, config):
    gray = cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)
    mask = cv2.threshold(gray,config['threshold'],255,cv2.THRESH_BINARY)[1]
    mask = cv2.morphologyEx(mask,cv2.MORPH_CLOSE,np.ones((3,3),np.uint8))
    contours,_ = cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    centers = []
    for contour in contours:
        if cv2.contourArea(contour)>config['min_area']:
            m = cv2.moments(contour)
            centers.append([m['m10']/m['m00'],m['m01']/m['m00']])
    return centers

def run_batch(input_dir, output_dir, config):
    output_dir.mkdir(parents=True,exist_ok=True)
    meta = json.loads((input_dir/'_sequence.json').read_text(encoding='utf-8'))
    tracks = {}; next_id = 1; records = []; events = []
    for frame_index, frame in enumerate(meta['frames']):
        image = read_image(input_dir/frame['file'])
        centers = detect_centers(image,config)
        candidates = []
        for identity,track in tracks.items():
            if frame_index-track['frame']<=config['max_gap']:
                for j,point in enumerate(centers):
                    distance = float(np.linalg.norm(np.array(point)-track['center']))
                    if distance<config['max_distance']:
                        candidates.append((distance,identity,j))
        assigned = {}; used = set()
        for _,identity,j in sorted(candidates):
            if identity not in used and j not in assigned:
                assigned[j] = identity; used.add(identity)
        objects = []
        for j,point in enumerate(centers):
            identity = assigned.get(j)
            if identity is None:
                identity = next_id; next_id += 1
            previous = tracks.get(identity)
            if previous:
                old_side = previous['center'][0] > meta['line_x']
                new_side = point[0] > meta['line_x']
                if old_side!=new_side:
                    events.append({'file':frame['file'],'id':identity,'direction':'right' if new_side else 'left'})
            tracks[identity] = {'center':point,'frame':frame_index}
            objects.append({'id':identity,'center':point})
            cv2.circle(image,tuple(round(v) for v in point),23,(0,0,255),2)
            cv2.putText(image,str(identity),tuple(round(v) for v in point),0,.5,(0,0,255),1)
        records.append({'file':frame['file'],'objects':objects})
        cv2.line(image,(meta['line_x'],0),(meta['line_x'],image.shape[0]-1),(0,180,255),1)
        write_image(output_dir/'overlays'/frame['file'],image)
    (output_dir/'results.json').write_text(json.dumps({'records':records,'events':events},indent=2),encoding='utf-8')
'''

PROJECTS = [
    dict(id='E01',title='批量硬币计数与定位',scenario='你要为盘点工位处理一个图片目录：逐张识别硬币、输出数量和中心坐标，遇到损坏文件也能继续处理。',
         output='results.json 的 records 每项含 file、count、centers（像素x,y）。损坏文件返回 error="decode_failed"；每张有效图保存 overlays/同名.png。中心允许8px误差，数量必须准确。',
         stages=['设计 read_image、detect_centers、draw_overlay 等职责，给每个函数写输入输出说明。','遍历图片目录，处理中文路径与解码失败；不把 _ 开头的辅助文件当待检图。','比较阈值、边缘与形态学，先在公开样例定位，再检查不同数量与光照。','输出 JSON 和定位叠加图，保证每个输入恰好有一条记录。','批量验收后总结误检、漏检与边缘残缺；换自己的工位照片做探索。'],
         limits='真实古钱币照片，非现代硬币面值识别；变体来自同一原图，不能证明跨相机泛化。',
         prerequisites=['T06','T07','V10'],assets=['coins.png'],config=dict(edge_low=40,edge_high=100,min_area=600,max_area=4500),algorithm=COINS),
    dict(id='E02',title='纹理表面缺陷与放行判断',scenario='你接到一组已对齐的基准图和待检表面图。需要区分曝光变化与局部异常，给出缺陷框和放行/拒收结果。',
         output='records 每项含 file、boxes（x,y,w,h列表）、decision=accept/reject。损坏文件给 decode_failed。缺陷框一对一匹配IoU>=0.5，不漏报、不多报；保存 overlays/同名.png。',
         stages=['定义模板读取、尺寸检查、亮度补偿、缺陷分割和输出五个模块。','读取 _reference.png，检查图像尺寸和dtype，使用有符号或浮点差值。','用中位差补偿整体曝光；对局部强变化分割、清理并提取区域。','把几何结果转换成 accept/reject，输出每个缺陷位置和叠加图。','验证无缺陷、多缺陷、曝光变化和坏文件；用真实配准误差解释方法的边界。'],
         limits='底图是真实CC0砖墙/碎石纹理，缺陷为人工注入，非真实工业缺陷数据；自动验收只覆盖已对齐图像。',
         prerequisites=['V10','V14'],assets=['brick.png','gravel.png'],config=dict(difference_threshold=40,min_area=40),algorithm=DEFECTS),
    dict(id='E03',title='单据定位与透视校正',scenario='将倾斜单据从桌面背景中提取并拉正，为后续OCR准备统一尺寸图片；空桌面不能伪造单据。',
         output='records 每项含 file、corners（左上/右上/右下/左下）；无单据为[]，损坏文件给decode_failed。保存叠加图和 rectified/同名.png；四角误差<=7px，校正图240×320、平均像素误差<24。',
         stages=['写出角点顺序和目标尺寸约定，避免把高宽反过来。','从背景中检测纸张候选，过滤面积并近似四边形；为空图设计返回。','独立编写点序函数，检查交叉点序和退化情况。','计算透视矩阵，保存定位叠加图与拉正图片，形成批处理CLI。','验证多个透视、亮度和无单据输入；分析反光、遮挡与弯曲纸张为什么会失败。'],
         limits='单据文本和透视为程序生成，桌面使用公开纹理。这里只验收定位校正，不包含文字识别或真实票据提取。',
         prerequisites=['A03','T06'],assets=['brick.png'],config=dict(paper_threshold=170,min_area=10000,width=240,height=320),algorithm=DOCUMENTS),
    dict(id='E04',title='传送带跟踪与双向过线计数',scenario='读取带时间戳的图像序列，为物体维持ID，记录穿过计数线的事件；短时漏检不能重复分配身份。',
         output='按 _sequence.json 顺序处理。records 每项含 file、objects（id、center）；events 含 file、id、direction=right/left。位置误差<=6px，同物体ID连续，跨线不重复，事件时间允许1帧偏差；每帧保存overlay。',
         stages=['读取序列清单、时间戳和line_x，区分文件字典序与采集顺序。','将检测与跟踪拆成不同函数，保持上一帧状态和最后出现时间。','按距离做一对一关联，设计最大位移和丢失保留窗口。','检测左右状态翻转并记录事件，输出带ID和计数线的图片。','验证双向运动、短时缺失和静止干扰，解释遮挡交叉时最近邻的局限。'],
         limits='从真实硬币图片裁取精灵后生成序列，非真实相机视频；不包含外观重识别，复杂遮挡需更强关联。',
         prerequisites=['T12','V14','L03'],assets=['coins.png'],config=dict(threshold=45,min_area=600,max_distance=85,max_gap=3),algorithm=None),
]

from .project_extensions import EXTRA_PROJECTS
from .project_guides import checkpoint_source
PROJECTS.extend(EXTRA_PROJECTS)
from .project_calibration import PROJECT as CALIBRATION_PROJECT, PIPELINE as CALIBRATION_PIPELINE
PROJECTS.append(CALIBRATION_PROJECT)

PROJECT_BY_ID={p['id']:p for p in PROJECTS}
PROJECT_IDS=set(PROJECT_BY_ID)

def source_bundle(key, reference=False):
    project=PROJECT_BY_ID[key]
    if reference:
        pipeline=CALIBRATION_PIPELINE if key=='E09' else TRACKING if key=='E04' else BATCH.format(algorithm=project['algorithm'])
        imaging=IMAGING
    else:
        imaging='''import cv2
import numpy as np

def read_image(path):
    # TODO: 用OpenCV/NumPy读文件；无法解码时抛出ValueError
    raise NotImplementedError('请实现读图')

def write_image(path, image):
    # TODO: 创建父目录，编码PNG并保存；支持中文路径
    raise NotImplementedError('请实现保存图像')
'''
        pipeline='''"""你可以自行增加函数或同目录.py模块；验收读取结果文件，不检查函数命名。"""
import json
import cv2
import numpy as np
from imaging import read_image, write_image

def run_batch(input_dir, output_dir, config):
    # TODO: 拆分读取、处理、可视化、结果序列化
    # TODO: 使用真实文件路径，保存 output_dir/results.json 与 overlays/*.png
    # TODO: 根据任务说明处理坏文件/空目标/时序状态
    raise NotImplementedError('请实现工程流水线')
'''
    return {'checkpoint.py':checkpoint_source(key,reference),'main.py':MAIN,'imaging.py':imaging,'pipeline.py':pipeline,'config.json':json.dumps(project['config'],ensure_ascii=False,indent=2)+'\n'}

PROJECT_LESSONS=[]
for p in PROJECTS:
    PROJECT_LESSONS.append(dict(id=p['id'],title=p['title'],goal=p['scenario'],contract=p['output'],knowledge=p['limits'],hints=p['stages'],prerequisites=p['prerequisites'],kind='project',starter=json.dumps(source_bundle(p['id']),ensure_ascii=False,sort_keys=True),reference=json.dumps(source_bundle(p['id'],True),ensure_ascii=False,sort_keys=True)))
