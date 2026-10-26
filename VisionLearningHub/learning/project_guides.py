"""Optional ordinary Python checkpoints; final grading always runs the learner's main.py."""

BLOCK_IDS=('io','detect','render','batch','accept')
GUIDE_VERSION=1
CLI='''
if __name__ == '__main__':
    import argparse
    import json
    from pathlib import Path
    parser = argparse.ArgumentParser()
    parser.add_argument('--block',choices=['io','detect','render'],required=True)
    parser.add_argument('--input',default='data/sample')
    parser.add_argument('--output',default='checkpoint-output')
    parser.add_argument('--config',default='config.json')
    args = parser.parse_args()
    output = Path(args.output); output.mkdir(parents=True,exist_ok=True)
    run_checkpoint(args.block,Path(args.input),output,json.loads(Path(args.config).read_text(encoding='utf-8')))
'''

STARTER='''"""可选的分块检查入口。内部函数和模块由你设计；不导入平台库。
io: 写results.json，records每项含file、shape、dtype；保存roundtrip/同名.png。
detect: 写与工程相同的records结果；此块不要求叠加图或完整跟踪事件。
render: 读取输入目录_detections.json，在原图上绘制，保存overlays/同名.png。
所有块都要为损坏图写error=decode_failed。输入中_开头的文件为辅助文件。
只实现当前块即可；在对应分支内导入模块，不要提前执行未完成的流水线。
"""

def run_checkpoint(block,input_dir,output_dir,config):
    # 可以将下面每个分支改为调用你自己设计的函数。
    if block == 'io':
        raise NotImplementedError('遍历图片，调用自己的读写函数，记录shape/dtype并保存无损回读图片')
    if block == 'detect':
        raise NotImplementedError('只运行自己的检测/测量/匹配算法，写入results.json')
    if block == 'render':
        raise NotImplementedError('读取_detections.json，绘制结果并保存overlays和results.json')
'''+CLI

REFERENCE='''"""仅使用标准Python、NumPy和OpenCV；分块入口可在平台外运行。"""
import json
import cv2
import numpy as np

def run_checkpoint(block,input_dir,output_dir,config):
    from imaging import read_image, write_image
    records=[]
    if block == 'render':
        payload=json.loads((input_dir/'_detections.json').read_text(encoding='utf-8'))
        for record in payload['records']:
            if 'error' in record: continue
            image=read_image(input_dir/record['file'])
            for center in record.get('centers',[]):
                cv2.circle(image,tuple(round(v) for v in center),8,(0,0,255),2)
            for obj in record.get('objects',[]):
                cv2.circle(image,tuple(round(v) for v in obj['center']),12,(0,0,255),2)
            for x,y,w,h in record.get('boxes',[]):
                cv2.rectangle(image,(x,y),(x+w-1,y+h-1),(0,0,255),2)
            if record.get('corners'):
                cv2.polylines(image,[np.int32(record['corners'])],True,(0,0,255),2)
            for item in record.get('assignments',[]):
                y,x=divmod(item['slot'],3);size=config['tile_size']
                cv2.putText(image,str(item['target']),(x*size+8,y*size+22),0,.6,(0,0,255),2)
            # 标明本图已经处理；无目标图也有可检查的可视化交付。
            cv2.putText(image,'CHECKED',(5,16),0,.45,(0,255,255),1)
            write_image(output_dir/'overlays'/record['file'],image)
        records=payload['records']
    else:
        if block=='detect':
            import pipeline
        for path in sorted(input_dir.glob('*.png')):
            if path.name.startswith('_'): continue
            try: image=read_image(path)
            except ValueError:
                records.append({'file':path.name,'error':'decode_failed'});continue
            if block=='io':
                result={'shape':list(image.shape),'dtype':str(image.dtype)}
                write_image(output_dir/'roundtrip'/path.name,image)
            elif PROJECT_ID=='E04':
                result={'objects':[{'id':i,'center':p} for i,p in enumerate(pipeline.detect_centers(image,config))]}
            else:
                result,_=pipeline.process_image(image,input_dir,output_dir,path.stem,config)
            records.append({'file':path.name,**result})
    (output_dir/'results.json').write_text(json.dumps({'records':records},ensure_ascii=False,indent=2),encoding='utf-8')
'''+CLI

def checkpoint_source(key,reference=False):
    return ("PROJECT_ID = "+repr(key)+"\n"+REFERENCE) if reference else STARTER

CONCEPTS={
 'E01':('边缘、轮廓与图像矩','先观察边缘闭合程度；用面积过滤，再用矩计算中心。','T06','https://docs.opencv.org/4.x/dd/d49/tutorial_py_contour_features.html'),
 'E02':('有符号差值与局部异常','转float后做差；减去全图中位差，再提取强局部变化。','V14','https://docs.opencv.org/4.x/d9/d61/tutorial_py_morphological_ops.html'),
 'E03':('角点顺序与透视映射','筛选四边形并约定角点顺序；检测块只输出四角，完整工程再交付校正图。','A03','https://docs.opencv.org/4.x/da/d6e/tutorial_py_geometric_transformations.html'),
 'E04':('检测与时间状态分离','先逐帧提取中心；检测块不要求稳定ID，批处理块才检查关联和过线事件。','V14','https://docs.opencv.org/4.x/d3/dc0/group__imgproc__shape.html'),
 'E05':('HSV范围与连通区域','红色可能跨越Hue端点；分别分割每类，过滤噪点并保留类别。','V13','https://docs.opencv.org/4.x/df/d9d/tutorial_py_colorspaces.html'),
 'E06':('标尺比例与旋转矩形','先检查蓝色标尺，再计算像素/mm；minAreaRect的边长需统一长短顺序。','A03','https://docs.opencv.org/4.x/dd/d49/tutorial_py_contour_features.html'),
 'E07':('特征匹配与几何一致性','ORB匹配使用Hamming距离；筛选匹配后用RANSAC验证，不凭一个匹配就判定存在。','V12','https://docs.opencv.org/4.x/d1/de0/tutorial_py_feature_homography.html'),
 'E08':('旋转枚举与身份唯一性','比较每块的四种旋转，补偿亮度；完成匹配后检查缺块和重复ID。','T11','https://docs.opencv.org/4.x/da/d6e/tutorial_py_geometric_transformations.html'),
}

def guide(key):
    concept,hint,lesson,url=CONCEPTS[key]
    rows=[
      ('io','读写与输入检查','只实现读写即可，不导入未完成的pipeline。','checkpoint.py --block io','输出每图shape、dtype与roundtrip无损回读图；坏图写decode_failed。',['遍历非下划线开头的PNG；用ValueError表达坏图。','读取 → 判断解码 → 记录shape/dtype → 保存PNG → 写JSON。']),
      ('detect','算法结果与位置','把核心算法与批处理、绘图分开。'+concept,'checkpoint.py --block detect','输出工程规定的records；不要求overlay、校正图和完整跟踪事件。',[hint,'先处理一张图并保存调试结果，再遍历小批次；空目标与坏图是不同情况。']),
      ('render','可视化与模块衔接','先用标准检测结果学习绘图，再接自己的算法输出。','checkpoint.py --block render','读取_detections.json，保留records并保存同尺寸overlays；无目标也标明已处理。',['标准输入只用于练习，不代表自己的检测已通过。','逐条读结果 → 回读原图 → 绘制对应几何信息/状态 → 保存叠加图。']),
      ('batch','完整批处理与异常','将自己的模块连成main.py，检查完整开发批次。','main.py','使用自己全部源码交付results.json与所有必需图片。',['先看最早失败的输入或输出检查项，再定位到模块。','E03还要写rectified；E04需按时间顺序保留ID并输出events。']),
      ('accept','多场景完整验收','运行五个不同条件的批次；通过后才计入工程通关。','main.py','完整工程正式验收，不使用标准中间数据。',['开发批次通过不代表所有变化条件都通过。','比较失败样例的光照、数量、角度或时间状态，修改后重新验收。']),
    ]
    return dict(version=GUIDE_VERSION,starter=STARTER,blocks=[dict(id=i,title=t,purpose=p,command=c,contract=out,hints=h,lesson=lesson,resource=url) for i,t,p,c,out,h in rows])

def guide_readme(key):
    data=guide(key)
    return '# 分块学习（可选）\n\n独立模式直接运行main.py；切换模式不会改写源码。分块入口checkpoint.py由你实现，可以调用任何普通Python模块。\n\n'+ '\n\n'.join('## '+b['title']+'\n\n'+b['purpose']+'\n\n'+b['contract']+'\n\n`python '+b['command']+' --input data/sample --output step-output --config config.json`\n\n[官方资料]('+b['resource']+')' for b in data['blocks'])+'\n\nrender需要输入目录中的_detections.json。可从自己detect输出复制results.json，也可使用data/standard/_detections.json中的教学结果；标准数据不会计入算法或工程通关。平台中每次检查都保存源码快照；修改源码后旧检查显示需要重验。\n'
