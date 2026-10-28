"""E09: rendered pinhole-camera targets with private ground truth, not real camera photos."""
import cv2
import numpy as np

PIPELINE = '''import json
import cv2
import numpy as np
from imaging import read_image,write_image

def process_image(image,input_dir,output_dir,stem,config):
    gray=cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)
    found,corners=cv2.findChessboardCorners(gray,tuple(config['pattern']),cv2.CALIB_CB_ADAPTIVE_THRESH|cv2.CALIB_CB_NORMALIZE_IMAGE|cv2.CALIB_CB_FAST_CHECK)
    overlay=image.copy()
    if found:
        corners=cv2.cornerSubPix(gray,corners,(5,5),(-1,-1),(cv2.TERM_CRITERIA_EPS|cv2.TERM_CRITERIA_MAX_ITER,40,.001))
        cv2.drawChessboardCorners(overlay,tuple(config['pattern']),corners,True)
    return {'status':'ok' if found else 'not_found','corners':corners.reshape(-1,2).tolist() if found else []},overlay

def run_batch(input_dir,output_dir,config):
    output_dir.mkdir(parents=True,exist_ok=True)
    objects=np.zeros((np.prod(config['pattern']),3),np.float32)
    objects[:,:2]=np.mgrid[0:config['pattern'][0],0:config['pattern'][1]].T.reshape(-1,2)*config['square_mm']
    records=[];points=[];images=[];names=[];shape=None
    for path in sorted(input_dir.glob('*.png')):
        if path.name.startswith('_'):continue
        try:image=read_image(path)
        except ValueError:
            records.append({'file':path.name,'error':'decode_failed'});continue
        if shape is None:shape=image.shape[:2]
        if shape!=image.shape[:2]:raise ValueError('标定图分辨率不一致')
        result,overlay=process_image(image,input_dir,output_dir,path.stem,config)
        records.append({'file':path.name,**result})
        write_image(output_dir/'overlays'/path.name,overlay)
        images.append((path.name,image))
        if result['status']=='ok':
            names.append(path.name);points.append(np.asarray(result['corners'],np.float32).reshape(-1,1,2))
    if len(points)<10:raise ValueError('至少需要10张有效的不同姿态棋盘图')
    rms,matrix,dist,rotations,translations=cv2.calibrateCamera([objects]*len(points),points,shape[::-1],None,None,flags=cv2.CALIB_FIX_K3)
    errors={}
    for name,observed,rotation,translation in zip(names,points,rotations,translations):
        projected,_=cv2.projectPoints(objects,rotation,translation,matrix,dist)
        errors[name]=float(np.sqrt(np.mean(np.sum((projected-observed)**2,axis=2))))
    for name,image in images:write_image(output_dir/'undistorted'/name,cv2.undistort(image,matrix,dist,None,matrix))
    payload={'records':records,'calibration':{'matrix':matrix.tolist(),'distortion':dist.ravel().tolist(),'rms':rms,'view_errors':errors,'image_size':list(shape[::-1])}}
    (output_dir/'results.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
'''

PROJECT=dict(id='E09',title='相机标定与畸变校正',scenario='为固定分辨率相机建立内参与畸变模型：从多姿态棋盘图片提取角点，估计参数，逐图解释重投影误差并交付校正图。',
 output='records每图含file、status=ok/not_found、corners（54个有序内角点或[]），坏图error=decode_failed；保存同尺寸overlays与undistorted。calibration含matrix（3×3）、distortion（5项）、image_size=[640,480]、rms及view_errors（有效文件名到RMSE）。角点误差≤2px（允许整体反序）；焦距相对误差≤4%、主点误差≤12px、网格畸变误差≤2px；rms≤0.8，逐图误差由验收器重新计算。校正统一使用原matrix作newCameraMatrix，不裁剪。',
 stages=['统计内角点数与棋盘格数，确定毫米单位、分辨率和姿态覆盖。','灰度读图，检测54个内角点并亚像素细化；坏图与无棋盘分别处理。','生成物平面点，配对每张图的角点；至少10张不同倾角再拟合。','调用calibrateCamera，使用projectPoints重新计算每图RMSE，定位异常图。','统一新内参，输出undistort校正图；保留参数及采集设置，解释真实镜头迁移边界。'],
 limits='全部棋盘图由已知针孔模型与畸变参数渲染，包含不同姿态、亮度、空场景及坏图；不是实拍标定，不代表镜头现场精度。真实数据需重新采集与验证。',
 prerequisites=['A03','T13'],assets=[],config={'pattern':[9,6],'square_mm':25},algorithm='')

def prepare_calibration(seed,folder,add):
    rng=np.random.default_rng(seed)
    matrix=np.array([[680+seed%41,0,318+seed%5],[0,700+seed%31,238+seed%5],[0,0,1]],float)
    dist=np.array([-.16-(seed%5)*.006,.04,.001,-.001,0.])
    objects=np.zeros((54,3),np.float32);objects[:,:2]=np.mgrid[0:9,0:6].T.reshape(-1,2)*25
    for i in range(12):
        rotation=np.array([(-.48 if i%2 else .42)+rng.uniform(-.12,.12),(-.4 if i%3 else .45)+rng.uniform(-.12,.12),rng.uniform(-.18,.18)])
        translation=np.array([-100+(i%3-1)*50.,-62.5+(i//3%3-1)*35.,580+(i%4)*30.])
        image=np.full((960,1280,3),155,np.uint8)
        for y in range(-1,6):
            for x in range(-1,9):
                square=np.array([[x,y,0],[x+1,y,0],[x+1,y+1,0],[x,y+1,0]],np.float32)*25
                pixels,_=cv2.projectPoints(square,rotation,translation,matrix,dist)
                shade=(235 if (x+y)%2 else 20)+seed%9
                cv2.fillConvexPoly(image,np.round(pixels.reshape(-1,2)*2).astype(np.int32),(shade,shade,shade),cv2.LINE_AA)
        image=cv2.resize(image,(640,480),interpolation=cv2.INTER_AREA)
        corners,_=cv2.projectPoints(objects,rotation,translation,matrix,dist)
        add(i,image,dict(status='ok',corners=corners.reshape(-1,2).tolist()),'程序渲染：针孔投影、径向/切向畸变、多姿态棋盘')
    add(12,np.full((480,640,3),155,np.uint8),dict(status='not_found',corners=[]),'程序生成：无棋盘场景')
    return dict(matrix=matrix,distortion=dist,objects=objects)

def assess_corners(record,target):
    try:
        points=np.asarray(record.get('corners'),float);expected=np.asarray(target['corners'],float)
        if target['status']=='not_found':return record.get('status')=='not_found' and points.shape==(0,)
        return record.get('status')=='ok' and points.shape==(54,2) and np.isfinite(points).all() and min(np.max(np.linalg.norm(points-expected,axis=1)),np.max(np.linalg.norm(points[::-1]-expected,axis=1)))<=2
    except (ValueError,TypeError):return False

def assess_calibration(payload,truth,input_dir,output_dir,add,image_output):
    try:
        data=payload['calibration'];matrix=np.asarray(data['matrix'],float);dist=np.asarray(data['distortion'],float)
        target=truth['_calibration'];expected=target['matrix'];objects=target['objects']
        valid=matrix.shape==(3,3) and dist.shape==(5,) and np.isfinite(matrix).all() and np.isfinite(dist).all() and np.allclose(matrix[2],[0,0,1]) and matrix[0,1]==0 and matrix[1,0]==0
        add('标定参数协议',valid and data['image_size']==[640,480],'有限3×3内参、5项畸变与原图分辨率')
        if not valid:return
        add('焦距与主点',np.max(abs(matrix.diagonal()[:2]/expected.diagonal()[:2]-1))<=.04 and np.max(abs(matrix[:2,2]-expected[:2,2]))<=12,'对比生成器私有真值：焦距4%，主点12px')
        grid=np.array([[x,y,1] for y in np.linspace(-.24,.24,7) for x in np.linspace(-.36,.36,9)],float)
        a,_=cv2.projectPoints(grid,np.zeros(3),np.zeros(3),matrix,dist)
        b,_=cv2.projectPoints(grid,np.zeros(3),np.zeros(3),matrix,target['distortion'])
        add('独立网格畸变',np.sqrt(np.mean(np.sum((a-b)**2,axis=2)))<=2,'比较未参与拟合的网格点畸变位移，RMSE≤2px')
        squared=[];reported=data['view_errors'];valid_errors=True;expected_names=set()
        for record in payload['records']:
            if record.get('status')!='ok':continue
            name=record['file'];expected_names.add(name);points=np.asarray(record['corners'],np.float32)
            ok,rotation,translation=cv2.solvePnP(objects,points,matrix,dist)
            projected,_=cv2.projectPoints(objects,rotation,translation,matrix,dist)
            error=float(np.sqrt(np.mean(np.sum((points-projected.reshape(-1,2))**2,axis=1))))
            squared.append(error**2);value=reported.get(name)
            valid_errors=valid_errors and ok and isinstance(value,(int,float)) and np.isfinite(value) and abs(value-error)<=.03 and error<=.8
        rms=data['rms']
        add('逐图重投影误差与整体RMSE',valid_errors and set(reported)==expected_names and len(squared)>=10 and isinstance(rms,(int,float)) and np.isfinite(rms) and abs(rms-np.sqrt(np.mean(squared)))<=.03,'验收器用提交角点和参数重新求姿态与误差；不能只填一个很小的数字')
        for name,target_record in truth.items():
            if name.startswith('_') or 'error' in target_record:continue
            source=image_output(input_dir,name);actual=image_output(output_dir,'undistorted/'+name)
            expected_image=cv2.undistort(source,matrix,dist,None,matrix)
            add(name+' 畸变校正图',actual is not None and actual.shape==source.shape and np.mean(abs(actual.astype(float)-expected_image))<1,'检查确实使用提交参数去畸变，不裁剪且保持640×480')
    except (KeyError,TypeError,ValueError,cv2.error) as error:add('标定交付',False,str(error))
