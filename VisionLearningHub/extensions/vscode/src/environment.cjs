'use strict';
const {execFile}=require('node:child_process');
const {promisify}=require('node:util');
const execute=promisify(execFile);
const probe=`import importlib, importlib.metadata, json, sys
packages = {'cv2': 'OpenCV', 'numpy': 'NumPy', 'fastapi': 'FastAPI', 'uvicorn': 'Uvicorn', 'multipart': 'python-multipart', 'httpx': 'httpx'}
checks = []
for module, label in packages.items():
    try:
        value = importlib.import_module(module)
        checks.append({'module': module, 'label': label, 'ok': True, 'version': getattr(value, '__version__', 'available')})
    except Exception as error:
        checks.append({'module': module, 'label': label, 'ok': False, 'error': type(error).__name__ + ': ' + str(error)})
opencv_packages = []
for name in ('opencv-python', 'opencv-python-headless', 'opencv-contrib-python', 'opencv-contrib-python-headless'):
    try: opencv_packages.append({'name': name, 'version': importlib.metadata.version(name)})
    except importlib.metadata.PackageNotFoundError: pass
print(json.dumps({'executable': sys.executable, 'python': sys.version.split()[0], 'checks': checks, 'opencvPackages': opencv_packages}))`;
async function probePython(python){
  try {
    const {stdout}=await execute(python,['-c',probe],{windowsHide:true,timeout:20000,maxBuffer:1024*1024,env:{...process.env,PYTHONUTF8:'1'}});
    const report=JSON.parse(stdout.trim());
    report.ok=report.checks.every(check=>check.ok)&&report.opencvPackages.length<=1;
    return report;
  }catch(error){return {ok:false,executable:python,checks:[],error:(error.stderr||error.message).trim()};}
}
function describeReport(report){
  return [`Python: ${report.python||'无法启动'}`,`解释器: ${report.executable}`,
    ...report.checks.map(c=>`${c.ok?'✓':'×'} ${c.label}: ${c.ok?c.version:c.error}`),
    ...(report.opencvPackages?.length>1?['× 同一环境安装了多个 OpenCV 包，请保留一种。']:[]),
    ...(report.error?[report.error]:[]),
    report.ok?'环境检查通过。':'请先选择或配置独立 Python 环境，再从环境菜单安装项目依赖。'].join('\n');
}
module.exports={probePython,describeReport};
