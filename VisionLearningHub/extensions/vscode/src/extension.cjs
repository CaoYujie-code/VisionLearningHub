'use strict';
const vscode = require('vscode');
const fs = require('node:fs/promises');
const path = require('node:path');
const crypto = require('node:crypto');
const net = require('node:net');
const {spawn} = require('node:child_process');
const {probePython,describeReport}=require('./environment.cjs');
const {Updater}=require('./updater.cjs');
const {lessonKey, inside, apiPath, navigationState} = require('./core.cjs');
let instance;
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
async function exists(file) {try {await fs.access(file);return true;} catch {return false;}}
async function freePort() {return new Promise((resolve,reject)=>{const s=net.createServer();s.on('error',reject);s.listen(0,'127.0.0.1',()=>{const port=s.address().port;s.close(()=>resolve(port));});});}

class Hub {
  constructor(context) {
    this.context=context;this.output=vscode.window.createOutputChannel('Vision Learning Hub');
    this.events=new vscode.EventEmitter();this.onDidChangeTreeData=this.events.event;
    this.test=vscode.tests.createTestController('visionLearning.tests','视觉练习验收');
    this.test.createRunProfile('多样例验收',vscode.TestRunProfileKind.Run,(request,token)=>this.testRun(request,token),true);
    this.runtime=path.join(context.extensionPath,'runtime');
    this.known=[];this.stopping=false;this.tasks=new Set();this.debugSessions=new Set();
    context.subscriptions.push(vscode.debug.onDidStartDebugSession(session=>{if(session.configuration.visionLearning)this.debugSessions.add(session);}),vscode.debug.onDidTerminateDebugSession(session=>this.debugSessions.delete(session)));
    this.status=vscode.window.createStatusBarItem('visionLearning.progress',vscode.StatusBarAlignment.Left,30);
    this.status.name='视觉学习进度';this.status.command='visionLearning.continue';this.status.text='$(book) 视觉学习';this.status.show();
    this.updater=new Updater(context,this.output);
    context.subscriptions.push(this.output,this.events,this.test,this.status,this.updater);
    context.subscriptions.push(vscode.workspace.onDidChangeConfiguration(e=>{if(e.affectsConfiguration('visionLearning.pythonPath')&&this.service)this.output.appendLine('解释器设置已改变，请执行 Vision: 重启学习服务 使其生效。');}));
  }
  async runtimePath() {
    if(!await exists(path.join(this.runtime,'app_server.py')))this.runtime=path.resolve(this.context.extensionPath,'../..');
    return this.runtime;
  }
  async folder() {
    if(!vscode.workspace.isTrusted)throw new Error('请先在 VS Code 中信任此学习工程，之后才能运行 Python。');
    if(this.project)return this.project;
    const folders=vscode.workspace.workspaceFolders||[];
    if(!folders.length)throw new Error('请先在 VS Code 中打开一个本地学习文件夹。');
    const selected=folders.length===1?folders[0]:await vscode.window.showWorkspaceFolderPick({placeHolder:'选择学习记录所属的工程'});
    if(!selected)throw new Error('未选择学习工程');
    if(selected.uri.scheme!=='file')throw new Error('此版本需要本机或远程文件系统中的实际目录。');
    this.project=selected.uri.fsPath;this.root=path.join(this.project,'.vision-learning');this.data=path.join(this.root,'data');
    return this.project;
  }
  async python() {
    await this.folder();await this.runtimePath();
    const config=vscode.workspace.getConfiguration('visionLearning',vscode.Uri.file(this.project)).get('pythonPath');
    if(config)return config;
    const suffix=process.platform==='win32'?'Scripts/python.exe':'bin/python';
    for(const dir of [this.project,path.join(this.project,'VisionLearningHub'),this.runtime]){
      const file=path.join(dir,'.venv',suffix);if(await exists(file))return file;
    }
    const py=vscode.extensions.getExtension('ms-python.python');
    if(py){const api=await py.activate();const environment=api.environments?.getActiveEnvironmentPath(vscode.Uri.file(this.project));if(environment?.path){const resolved=await api.environments.resolveEnvironment(environment);if(resolved?.executable?.uri)return resolved.executable.uri.fsPath;}}
    return process.platform==='win32'?'python':'python3';
  }
  async ensure() {
    if(this.service)return this.service;
    if(this.starting)return this.starting;
    this.starting=this.start().finally(()=>{this.starting=null;});return this.starting;
  }
  async start() {
    await this.folder();await this.runtimePath();this.pythonExe=await this.python();
    const report=await probePython(this.pythonExe);this.output.appendLine(describeReport(report));
    if(!report.ok)throw new Error('学习环境尚未就绪。请执行“Vision: Python 环境设置与检查”，查看缺失依赖与解释器。');
    this.failure=null;
    await fs.mkdir(this.data,{recursive:true});
    if(!inside(await fs.realpath(this.project),await fs.realpath(this.root)))throw new Error('学习目录不能链接到工程之外。');
    this.lock=path.join(this.data,'extension.lock');
    if(this.child&&(this.child.exitCode!==null||this.child.signalCode)){
      try{if((await fs.readFile(this.lock,'utf8')).trim()===String(process.pid))await fs.unlink(this.lock);}catch{}
      this.child=null;
    }
    try {const lock=await fs.open(this.lock,'wx');await lock.writeFile(String(process.pid));await lock.close();}
    catch(error){
      if(error.code!=='EEXIST')throw error;
      const owner=Number(await fs.readFile(this.lock,'utf8'));let alive=true;
      try {process.kill(owner,0);}catch(e){if(e.code==='ESRCH')alive=false;}
      if(alive)throw new Error('此学习空间已在另一个 VS Code 窗口运行，请先停止那个窗口的学习服务。');
      await fs.unlink(this.lock);const lock=await fs.open(this.lock,'wx');await lock.writeFile(String(process.pid));await lock.close();
    }
    const port=await freePort(),control=crypto.randomBytes(32).toString('hex'),id=crypto.randomBytes(16).toString('hex');
    const child=spawn(this.pythonExe,[path.join(this.runtime,'app_server.py'),'--port',String(port),'--managed'],{
      cwd:this.runtime,windowsHide:true,stdio:['pipe','pipe','pipe'],
      env:{...process.env,PYTHONUTF8:'1',VLH_DATA_ROOT:this.data,VLH_WORKSPACE:this.root,VLH_CONTROL:control,VLH_INSTANCE:id}
    });
    let spawnError;child.on('error',e=>{spawnError=e;});
    child.stdout.on('data',s=>this.output.append(s.toString()));child.stderr.on('data',s=>this.output.append(s.toString()));
    child.once('exit',(code,signal)=>{
      if(this.child===child&&!this.stopping){
        this.service=null;this.failure='学习服务已退出（'+(signal||code)+'），请点击重启后重新运行练习。';
        this.output.appendLine(this.failure);this.status.text='$(warning) 视觉学习服务已停止';this.status.command='visionLearning.restart';
        this.panel?.webview.postMessage({type:'vlh-offline',message:this.failure});
      }
    });
    this.child=child;const url='http://127.0.0.1:'+port;
    try {
      for(let i=0;i<100;i++){
        if(spawnError)throw spawnError;if(child.exitCode!==null)throw new Error('Python 服务已退出，请查看 Vision 输出日志。');
        try {const h=await (await fetch(url+'/api/health',{signal:AbortSignal.timeout(700)})).json();if(h.instance===id){
          const html=await (await fetch(url)).text();const match=html.match(/name="vlh-token" content="([^"]+)"/);if(!match)throw new Error('学习前端资源缺失');
          this.service={url,control,token:match[1],id};break;
        }}catch{} await delay(150);
      }
      if(!this.service)throw new Error('学习服务启动超时，请检查依赖与输出日志。');
      const boot=await this.request('/bootstrap');this.known=boot.lessons.map(l=>l.id);this.boot=boot;
      for(const lesson of boot.lessons){const item=this.test.createTestItem(lesson.id,lesson.id+' '+lesson.title,vscode.Uri.file(this.file(lesson.id)));this.test.items.add(item);}
      if(!this.watcher){
        this.watcher=vscode.workspace.createFileSystemWatcher(new vscode.RelativePattern(this.root,'exercises/*.py'));
        const changed=()=>{this.test.invalidateTestResults();clearTimeout(this.refreshTimer);this.refreshTimer=setTimeout(()=>this.refresh().catch(e=>this.output.appendLine(e.message)),350);};
        this.watcher.onDidChange(changed);this.watcher.onDidCreate(changed);this.watcher.onDidDelete(changed);this.context.subscriptions.push(this.watcher);
      }
      const readme=path.join(this.root,'README.md');if(!await exists(readme))await fs.writeFile(readme,'# 我的视觉练习\n\nexercises/ 是你的真实 Python 代码；使用 cv2、numpy 和普通模块导入。\n通过 Vision 命令运行、调试和验收。data/ 是私有学习记录，请勿提交。\n清除记录不会删除代码；重置单题的旧代码存于 .vision-backups/。\n');
      this.updateStatus();this.events.fire();return this.service;
    }catch(error){await this.stop();throw error;}
  }
  file(key) {key=lessonKey(key,this.known);return key.startsWith('E')?path.join(this.root,'projects',key,'main.py'):path.join(this.root,'exercises',key+'.py');}
  async saveFiles() {
    for(const doc of vscode.workspace.textDocuments){if(doc.isDirty&&doc.uri.scheme==='file'&&(inside(path.join(this.root,'exercises'),doc.uri.fsPath)||inside(path.join(this.root,'projects'),doc.uri.fsPath))){if(!await doc.save())throw new Error('代码未保存，已取消运行。');}}
  }
  async request(route,method='GET',body) {
    apiPath(route);if(!this.service){if(this.failure)throw new Error(this.failure);await this.ensure();}
    const headers={'X-VLH-Token':this.service.token};
    if(body!==undefined&&!(body instanceof FormData))headers['Content-Type']='application/json';
    const response=await fetch(this.service.url+'/api'+route,{method,headers,body:body===undefined?undefined:body instanceof FormData?body:typeof body==='string'?body:JSON.stringify(body),signal:AbortSignal.timeout(60000)});
    if(!response.ok){const error=await response.json().catch(()=>({detail:'服务请求失败'}));throw new Error(typeof error.detail==='string'?error.detail:JSON.stringify(error.detail));}
    if(response.headers.get('content-type')?.includes('application/json'))return response.json();
    return Buffer.from(await response.arrayBuffer());
  }
  async refresh(){if(!this.service)return;this.boot=await this.request('/bootstrap');this.updateStatus();this.events.fire();this.panel?.webview.postMessage({type:'vlh-refresh'});}
  async getChildren(item) {
    try {await this.ensure();if(item?.course)return this.boot.lessons.filter(l=>l.course===item.course).map(l=>({lesson:l.id,label:l.id+' '+l.title}));if(item)return [];return [{page:'continue',label:'继续上次练习'},{page:'home',label:'学习总览'},{page:'projects',label:'工程项目实训'},...this.boot.courses.map(c=>({course:c.id,label:c.id+' '+c.title})),{page:'lab',label:'图像实验室'},{page:'resources',label:'学习资料库'},{page:'records',label:'记录、备份与清除'}];}
    catch(error){this.output.appendLine(error.message);return [{page:'setup',label:'配置环境 / 打开学习工程'}];}
  }
  getTreeItem(item) {
    const tree=new vscode.TreeItem(item.label,item.course?vscode.TreeItemCollapsibleState.Collapsed:vscode.TreeItemCollapsibleState.None);
    if(item.lesson){tree.description=this.boot?.passed[item.lesson]?'已验收':'待练习';tree.command={command:'visionLearning.exercise',title:'练习',arguments:[item.lesson]};}
    else if(item.course){const keys=this.boot.courses.find(c=>c.id===item.course)?.lessons||[];tree.description=keys.filter(k=>this.boot.passed[k]).length+' / '+keys.length;tree.tooltip='本章正式验收进度';}
    else if(item.page)tree.command={command:item.page==='setup'?'visionLearning.environment':item.page==='continue'?'visionLearning.continue':'visionLearning.open',title:'打开',arguments:[item.page]};
    return tree;
  }
  async show(page,lesson) {
    await this.ensure();await this.viewSave;
    const saved=this.context.workspaceState.get(this.stateKey(),{});
    const state=navigationState(lesson?{...saved,page:'practice',lesson}:page?{...saved,page,lesson:page==='practice'?(saved.lastBasic||'P01'):saved.lesson}:saved,this.known,this.boot.courses.map(c=>c.id));
    this.navigation={type:'vlh-navigate',...state};this.restoreTarget=state;this.viewState=null;this.navVersion=(this.navVersion||0)+1;
    if(!this.panel){
      this.panel=vscode.window.createWebviewPanel('visionLearning.hub','Vision · 视觉学习',vscode.ViewColumn.Beside,{enableScripts:true,retainContextWhenHidden:true,localResourceRoots:[vscode.Uri.file(path.join(this.runtime,'dist')),vscode.Uri.file(this.data)]});
      const panel=this.panel;const web=panel.webview;const resource=name=>web.asWebviewUri(vscode.Uri.file(path.join(this.runtime,'dist',name))).toString();
      web.html=`<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src ${web.cspSource} data: blob:; style-src ${web.cspSource} 'unsafe-inline'; script-src ${web.cspSource}; font-src ${web.cspSource};"><link rel="stylesheet" href="${resource('app.css')}"></head><body><div id="root"></div><script type="module" src="${resource('app.js')}"></script></body></html>`;
      web.onDidReceiveMessage(async m=>{if(this.panel!==panel||m?.type!=='vlh-request')return;try{const value=await this.message(m.action,m.args||{});await web.postMessage({type:'vlh-response',id:m.id,value});}catch(e){await web.postMessage({type:'vlh-response',id:m.id,error:e.message});}});
      this.panel.onDidDispose(()=>{this.panel=null;});
    }else this.panel.reveal(vscode.ViewColumn.Beside,true);
    await this.panel.webview.postMessage(this.navigation);
  }
  async images(value) {
    if(Array.isArray(value))return Promise.all(value.map(v=>this.images(v)));
    if(value&&typeof value==='object'){const result={};for(const [k,v]of Object.entries(value))result[k]=await this.images(v);return result;}
    if(typeof value==='string'&&value.startsWith('/api/assets/')){
      const file=path.resolve(this.data,value.slice('/api/assets/'.length));
      if(!inside(this.data,file)||path.extname(file)!=='.png')throw new Error('图片路径无效');
      const real=await fs.realpath(file);if(!inside(await fs.realpath(this.data),real))throw new Error('图片超出学习空间');
      return this.panel?.webview.asWebviewUri(vscode.Uri.file(real)).toString()+'?v='+(await fs.stat(real)).mtimeMs;
    }return value;
  }
  rememberState(patch) {
    this.viewSave=(this.viewSave||Promise.resolve()).catch(()=>{}).then(async()=>{
      const saved=this.context.workspaceState.get(this.stateKey(),{});
      const value=navigationState({...saved,...patch},this.known,this.boot.courses.map(c=>c.id));
      await this.context.workspaceState.update(this.stateKey(),value);
    });return this.viewSave;
  }
  async message(action,args) {
    if(action==='rememberView'){
      await this.rememberState({memory:args.memory});return true;
    }
    if(action==='viewReady'){
      if(this.restoreTarget&&(args.page!==this.restoreTarget.page||(['practice','project'].includes(args.page)&&args.lesson!==this.restoreTarget.lesson)||(args.page==='route'&&args.course!==this.restoreTarget.course)))return true;
      this.restoreTarget=null;
      await this.rememberState(args);this.viewState=args;return true;
    }
    if(action==='api'){
      apiPath(args.path);let body=args.body;
      if(args.path==='/clear')this.ensureIdle();
      if(args.method==='POST'&&args.path==='/jobs')await this.saveFiles();
      if(body?.file){if(!['/upload','/restore'].includes(args.path)&&!/^\/lesson\/[A-Z]\d{2}\/walkthrough\/import$/.test(args.path))throw new Error('不支持的上传');const bytes=Buffer.from(body.file.data,'base64');if(bytes.length>(args.path==='/restore'?128:12)*1024*1024)throw new Error('上传文件过大');const form=new FormData();form.append('file',new Blob([bytes],{type:body.file.type}),path.basename(body.file.name));body=form;}
      const result=await this.request(args.path,args.method,body);
      if(args.path==='/clear'&&(typeof body==='string'?JSON.parse(body):body)?.scope==='all')await this.context.workspaceState.update(this.stateKey(),undefined);
      if(args.path==='/bootstrap'&&this.navigation){const nav=this.navigation,panel=this.panel,version=this.navVersion;this.navigation=null;setTimeout(()=>{if(this.panel===panel&&this.navVersion===version)void panel?.webview.postMessage(nav);},150);}
      if(args.path==='/clear'||args.path==='/restore'||(/^\/jobs\/[a-f0-9]+$/.test(args.path)&&['done','error','timeout','cancelled'].includes(result.status)))await this.refresh();
      return Buffer.isBuffer(result)?{status:200,base64:result.toString('base64')}:{status:200,json:await this.images(result)};
    }
    if(action==='download'){
      if(!['/backup','/export-code'].includes(args.path)&&!/^\/projects\/E\d{2}\/export$/.test(args.path)&&!/^\/lesson\/[A-Z]\d{2}\/examples$/.test(args.path)&&!/^\/lesson\/[A-Z]\d{2}\/walkthrough\/export\/\d{1,4}$/.test(args.path))throw new Error('不支持的导出');await this.saveFiles();
      const destination=await vscode.window.showSaveDialog({defaultUri:vscode.Uri.file(path.join(this.project,path.basename(args.name))),filters:{ZIP:['zip']}});
      if(!destination)throw new Error('已取消导出');const bytes=await this.request(args.path);await vscode.workspace.fs.writeFile(destination,bytes);return true;
    }
    if(['openWalkthrough','runWalkthrough','readWalkthrough'].includes(action)){
      await this.ensure();const key=lessonKey(args.key,this.known);
      if(!Number.isInteger(args.parameter)||args.parameter<0||args.parameter>9999)throw new Error('实验参数无效');
      const route='/lesson/'+key+'/walkthrough';const pack=await this.request(route+'/files/'+args.parameter);
      if(!/^[a-f0-9]{16}$/.test(pack.revision))throw new Error('课程版本无效');
      const parent=path.join(this.root,'walkthrough-experiments');
      const directory=path.join(parent,key+'-'+pack.revision+'-'+args.parameter);const rootReal=await fs.realpath(this.root);
      for(const part of [parent,directory]){
        try{if(!inside(rootReal,await fs.realpath(part)))throw new Error('实验目录超出学习工程');}
        catch(error){if(error.code!=='ENOENT')throw error;await fs.mkdir(part);}
      }
      const names=['practice.py','reference.py','input.npy','input.png','params.json','context.json','README.md'];
      for(const item of pack.files){
        if(!names.includes(item.name))throw new Error('未知实验文件');
        const file=path.join(directory,item.name);
        try{await fs.writeFile(file,Buffer.from(item.base64,'base64'),{flag:'wx'});}catch(error){if(error.code!=='EEXIST')throw error;}
        if(!inside(await fs.realpath(directory),await fs.realpath(file)))throw new Error('实验文件超出目录');
      }
      const file=path.join(directory,'practice.py');
      if(action==='openWalkthrough'){
        const document=await vscode.workspace.openTextDocument(vscode.Uri.file(file));await vscode.window.showTextDocument(document,{viewColumn:vscode.ViewColumn.One});return true;
      }
      if(['runWalkthrough','readWalkthrough'].includes(action)&&this.tasks.size)throw new Error('请等待终端任务结束，再运行或读取步骤结果。');
      if(action==='readWalkthrough'){
        const result=path.join(directory,'results.zip');let real;
        try{real=await fs.realpath(result);}catch(error){if(error.code==='ENOENT')throw new Error('尚未生成 results.zip，请先运行分步代码，等待终端结束。');throw error;}
        if(!inside(await fs.realpath(directory),real))throw new Error('结果文件超出实验目录');
        if((await fs.stat(real)).size>12*1024*1024)throw new Error('结果包不能超过 12 MB');
        const form=new FormData();form.append('file',new Blob([await fs.readFile(real)],{type:'application/zip'}),'results.zip');
        return this.images(await this.request(route+'/import','POST',form));
      }
      await this.saveFiles();
      // Keep the previous generated result separately: an early crash must not import it as this run.
      const previous=path.join(directory,'results.zip');
      try{const real=await fs.realpath(previous);if(!inside(await fs.realpath(directory),real))throw new Error('结果文件超出实验目录');await fs.rename(previous,path.join(directory,'results.previous-'+Date.now()+'.zip'));}
      catch(error){if(error.code!=='ENOENT')throw error;}
      const execution=new vscode.ProcessExecution(this.pythonExe,[file],{cwd:directory,env:{PYTHONUTF8:'1'}});
      const task=new vscode.Task({type:'visionLearning',lesson:key},vscode.TaskScope.Workspace,'Vision steps '+key,'Vision',execution,[]);
      const running=await vscode.tasks.executeTask(task);this.tasks.add(running);const ended=vscode.tasks.onDidEndTask(e=>{if(e.execution===running){this.tasks.delete(running);ended.dispose();}});return true;
    }
    if(action==='openFunctionExample'){
      await this.ensure();const key=lessonKey(args.key,this.known);
      const boot=await this.request('/bootstrap');const card=boot.lessons.find(l=>l.id===key)?.function_guide?.cards.find(c=>c.id===args.id);
      if(!card||!/^[a-z_]+$/.test(card.id))throw new Error('未知函数示例');
      const directory=path.join(this.root,'function-examples',key);const rootReal=await fs.realpath(this.root);
      // Check each ancestor before mkdir, and each existing file before opening.
      for(const part of [path.join(this.root,'function-examples'),directory]){
        try{if(!inside(rootReal,await fs.realpath(part)))throw new Error('示例目录超出学习工程');}
        catch(error){if(error.code!=='ENOENT')throw error;await fs.mkdir(part);}
      }
      const file=path.join(directory,card.id+'.py');
      try{await fs.writeFile(file,card.example,{encoding:'utf8',flag:'wx'});}catch(error){if(error.code!=='EEXIST')throw error;}
      if(!inside(await fs.realpath(directory),await fs.realpath(file)))throw new Error('示例文件超出目录');
      const document=await vscode.workspace.openTextDocument(vscode.Uri.file(file));await vscode.window.showTextDocument(document,{viewColumn:vscode.ViewColumn.One});return true;
    }
    if(action==='confirm')return (await vscode.window.showWarningMessage(String(args.message),{modal:true},'继续'))==='继续';
    if(action==='external'){const uri=vscode.Uri.parse(args.url);if(!['https','http'].includes(uri.scheme))throw new Error('仅支持文档网页链接');return vscode.env.openExternal(uri);}
    if(action==='openProjectFile'||action==='openProjectFolder'){
      await this.ensure();const key=lessonKey(args.key,this.known);if(!key.startsWith('E'))throw new Error('工程不存在');
      const root=path.join(this.root,'projects',key);const name=action==='openProjectFolder'?'README.md':args.name;
      if(typeof name!=='string'||!(/^[a-z][a-z0-9_]{0,47}\.py$/.test(name)||['config.json','README.md'].includes(name)))throw new Error('工程文件名无效');
      const file=path.join(root,name);const real=await fs.realpath(file);if(!inside(await fs.realpath(root),real))throw new Error('工程文件超出目录');
      if(action==='openProjectFolder')return vscode.commands.executeCommand('revealInExplorer',vscode.Uri.file(root));
      const document=await vscode.workspace.openTextDocument(vscode.Uri.file(file));await vscode.window.showTextDocument(document,{viewColumn:vscode.ViewColumn.One});return true;
    }
    if(action==='openExercise')return this.openExercise(args.key,args.line);
    if(action==='runNative')return this.native(args.key,false);
    if(action==='debug')return this.native(args.key,true);
    if(action==='resetExercise')return this.reset(args.key);
    if(action==='environment')return this.environment();
    if(action==='restart')return this.restart();
    if(action==='checkUpdate')return this.updater.check(true);
    throw new Error('未知扩展操作');
  }
  async openExercise(key,line=1) {
    await this.ensure();const file=this.file(key);const document=await vscode.workspace.openTextDocument(vscode.Uri.file(file));
    const editor=await vscode.window.showTextDocument(document,{viewColumn:vscode.ViewColumn.One,preserveFocus:false});
    const position=new vscode.Position(Math.max(0,Math.min(Number(line)||1,document.lineCount)-1),0);editor.selection=new vscode.Selection(position,position);editor.revealRange(new vscode.Range(position,position));return true;
  }
  currentKey(arg) {if(typeof arg==='string'&&this.known.includes(arg))return arg;const active=vscode.window.activeTextEditor?.document.uri.fsPath;if(active&&inside(path.join(this.root,'projects'),active))return lessonKey(path.relative(path.join(this.root,'projects'),active).split(path.sep)[0],this.known);if(active&&inside(path.join(this.root,'exercises'),active))return lessonKey(path.basename(active,'.py'),this.known);throw new Error('请先打开一份 exercises 中的练习代码。');}
  async native(key,debug) {
    await this.ensure();key=this.currentKey(key);await this.saveFiles();
    const args=['--workspace',this.root,'--lesson',key,'--output',path.join(this.data,'debug',key)];
    if(debug){if(!vscode.extensions.getExtension('ms-python.debugpy'))throw new Error('请自行安装 Microsoft Python Debugger 扩展后再调试。');return vscode.debug.startDebugging(vscode.workspace.getWorkspaceFolder(vscode.Uri.file(this.project)),{name:'Vision '+key,type:'debugpy',request:'launch',module:'learning.debug_runner',python:this.pythonExe,args,cwd:this.runtime,console:'integratedTerminal',justMyCode:false,visionLearning:true,env:{PYTHONUTF8:'1',PYTHONPATH:this.runtime}});}
    const execution=new vscode.ProcessExecution(this.pythonExe,['-m','learning.debug_runner',...args],{cwd:this.runtime,env:{PYTHONUTF8:'1',PYTHONPATH:this.runtime}});
    const task=new vscode.Task({type:'visionLearning',lesson:key},vscode.TaskScope.Workspace,'Vision '+key,'Vision',execution,[]);const taskRun=await vscode.tasks.executeTask(task);this.tasks.add(taskRun);const ended=vscode.tasks.onDidEndTask(e=>{if(e.execution===taskRun){this.tasks.delete(taskRun);ended.dispose();}});return true;
  }
  async run(key,verify=true,token,onStart) {
    await this.ensure();key=this.currentKey(key);await this.saveFiles();const draft=await this.request('/lesson/'+key);
    const job=await this.request('/jobs','POST',{lesson:key,code:draft.code,note:draft.note,verify});if(onStart)onStart(job.id);
    const cancel=token?.onCancellationRequested(()=>this.request('/jobs/'+job.id+'/stop','POST',{}).catch(()=>{}));
    try {for(;;){if(token?.isCancellationRequested)await this.request('/jobs/'+job.id+'/stop','POST',{});const status=await this.request('/jobs/'+job.id);if(!['queued','running','stopping'].includes(status.status)){await this.refresh();return status;}await delay(250);}}
    finally{cancel?.dispose();}
  }
  async testRun(request,token) {
    await this.ensure();const run=this.test.createTestRun(request);const items=request.include||[...this.known].map(k=>this.test.items.get(k));
    try {for(const item of items){if(request.exclude?.some(x=>x.id===item.id))continue;if(token.isCancellationRequested){run.skipped(item);continue;}run.started(item);try{const result=await this.run(item.id,true,token);if(result.result?.passed&&!result.stale)run.passed(item);else run.failed(item,new vscode.TestMessage(result.error||JSON.stringify(result.result?.reports?.filter(r=>!r.passed)||result.status,null,2)));}catch(e){run.errored(item,new vscode.TestMessage(e.message));}}}finally{run.end();}
  }
  async clear(scope) {
    await this.ensure();
    if(!scope){const pick=await vscode.window.showQuickPick([{label:'清除实验缓存',scope:'cache',description:'保留代码、笔记、历史与通关'},{label:'清除验收历史',scope:'history',description:'通关归零，保留代码、笔记和收藏'},{label:'清除全部学习记录',scope:'all',description:'删除笔记、收藏、历史、图片和空间内备份；保留代码'}]);scope=pick?.scope;}
    if(!scope)return false;
    const value=await vscode.window.showInputBox({title:'确认清除当前学习空间',prompt:'范围：'+scope+'。位置：'+this.data+'。保留源码。输入 CLEAR，取消则不修改。',validateInput:v=>v==='CLEAR'?null:'请输入 CLEAR'});
    if(value!=='CLEAR')return false;this.ensureIdle();await this.request('/clear','POST',{scope,confirmation:value});if(scope==='all')await this.context.workspaceState.update(this.stateKey(),undefined);await this.refresh();return true;
  }
  async reset(key) {
    await this.ensure();key=this.currentKey(key);this.ensureIdle();
    if(await vscode.window.showWarningMessage('重置 '+key+' 到空白练习？当前代码会先备份到 .vision-backups。',{modal:true},'备份并重置')!=='备份并重置')return false;
    await this.saveFiles();const result=await this.request('/workspace/reset/'+key,'POST',{scope:'exercise',confirmation:'CLEAR'});await this.refresh();await vscode.window.showInformationMessage('原代码备份：'+result.backup);return true;
  }
  async environment() {
    await this.folder();await this.runtimePath();const choice=await vscode.window.showQuickPick(['检查当前环境','选择 Python 可执行文件','在终端安装项目依赖','查看扩展依赖说明']);if(!choice)return;
    if(choice==='选择 Python 可执行文件'){const selected=await vscode.window.showOpenDialog({canSelectMany:false,canSelectFiles:true,canSelectFolders:false,title:'选择学习环境中的 python.exe / python'});if(selected?.[0]){await this.stop();await vscode.workspace.getConfiguration('visionLearning',vscode.Uri.file(this.project)).update('pythonPath',selected[0].fsPath,vscode.ConfigurationTarget.WorkspaceFolder);this.events.fire();}return;}
    if(choice==='在终端安装项目依赖'){
      const python=await this.python();if(await vscode.window.showWarningMessage('将通过 pip 安装到以下解释器：'+python+'。建议先使用独立虚拟环境。',{modal:true},'安装依赖')!=='安装依赖')return;
      const task=new vscode.Task({type:'visionLearning.install'},vscode.TaskScope.Workspace,'Vision 安装依赖','Vision',new vscode.ProcessExecution(python,['-m','pip','install','-r',path.join(this.runtime,'requirements.lock.txt')],{cwd:this.runtime}),[]);await vscode.tasks.executeTask(task);return;
    }
    if(choice==='查看扩展依赖说明'){return vscode.env.openExternal(vscode.Uri.parse('https://code.visualstudio.com/docs/python/environments'));}
    const report=await probePython(await this.python());this.output.appendLine(describeReport(report));this.output.show();if(report.ok)await vscode.window.showInformationMessage('环境检查通过：Python '+report.python+'。');return report;
  }
  stateKey(){return 'view.'+crypto.createHash('sha256').update(this.project||'').digest('hex').slice(0,16);}
  updateStatus(){
    if(!this.boot)return;
    const passed=Object.values(this.boot.passed).filter(Boolean).length;
    this.status.text='$(book) 视觉学习 '+passed+'/'+this.known.length;this.status.command='visionLearning.continue';
    this.status.tooltip='点击继续上次练习。解释器：'+this.pythonExe;
    this.status.accessibilityInformation={label:'视觉学习，已通过 '+passed+' 道，共 '+this.known.length+' 道'};
  }
  ensureIdle(){if(this.tasks.size||this.debugSessions.size)throw new Error('请先结束终端运行或调试，再清除数据或重置练习。');}
  async resume(){
    await this.ensure();const state=this.context.workspaceState.get(this.stateKey());
    const key=this.known.includes(state?.lastLearning)?state.lastLearning:this.known.includes(state?.lesson)?state.lesson:this.boot.courses.flatMap(c=>c.lessons).find(k=>!this.boot.passed[k])||this.known[0];
    await this.show('practice',key);await this.openExercise(key);
  }
  async restart(){
    await this.stop();this.failure=null;await this.ensure();await this.refresh();return true;
  }
  async stop() {
    if(this.stopping)return;this.stopping=true;clearTimeout(this.refreshTimer);
    try {for(const task of this.tasks)task.terminate();this.tasks.clear();for(const session of this.debugSessions)await vscode.debug.stopDebugging(session);this.debugSessions.clear();if(this.service){try{await fetch(this.service.url+'/api/shutdown',{method:'POST',headers:{'X-VLH-Control':this.service.control},signal:AbortSignal.timeout(2000)});}catch{}}
      this.child?.stdin.end();if(this.child&&this.child.exitCode===null){await Promise.race([new Promise(r=>this.child.once('exit',r)),delay(3500)]);if(this.child.exitCode===null)this.child.kill();}
      this.service=null;this.child=null;this.status.text='$(book) 视觉学习已暂停';this.status.command='visionLearning.open';if(this.lock){try{if((await fs.readFile(this.lock,'utf8')).trim()===String(process.pid))await fs.unlink(this.lock);}catch{}}
    }finally{this.stopping=false;}
  }
}

function activate(context) {
  const hub=instance=new Hub(context);context.subscriptions.push(vscode.window.registerTreeDataProvider('visionLearning.courses',hub));
  const register=(id,fn)=>context.subscriptions.push(vscode.commands.registerCommand('visionLearning.'+id,async(...args)=>{try{return await fn(...args);}catch(e){hub.output.appendLine(e.stack||e.message);await vscode.window.showErrorMessage(e.message);}}));
  register('open',page=>hub.show(page));
  register('continue',()=>hub.resume());register('restart',()=>hub.restart());register('checkUpdate',()=>hub.updater.check(true));
  hub.updater.schedule();
  register('exercise',async key=>{await hub.ensure();if(!key){const pick=await vscode.window.showQuickPick(hub.boot.lessons.map(l=>({label:l.id+' '+l.title,key:l.id})));key=pick?.key;}if(key){await hub.show('practice',key);return hub.openExercise(key);}});
  for(const [command,verify]of [['run',false],['verify',true]])register(command,async key=>{await hub.ensure();key=hub.currentKey(key);const result=await vscode.window.withProgress({location:vscode.ProgressLocation.Notification,title:'Vision '+key,cancellable:true},(_,token)=>hub.run(key,verify,token));await hub.show('practice',key);await vscode.window.showInformationMessage(result.result?.passed?'检查通过；结果已保存，可在历史中查看。':result.error||'检查未通过，请查看练习历史。');return result;});
  register('debug',key=>hub.native(key,true));register('environment',()=>hub.environment());register('clear',()=>hub.clear());register('reset',key=>hub.reset(key));register('stop',()=>{hub.panel?.dispose();return hub.stop();});
  return hub;
}
async function deactivate(){if(instance)await instance.stop();}
module.exports={activate,deactivate};
