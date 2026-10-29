'use strict';
const vscode=require('vscode');
const assert=require('node:assert/strict');
const fs=require('node:fs/promises');
const path=require('node:path');
exports.run=async()=>{
 let hub;const passed=[];
 try{
  const extension=vscode.extensions.all.find(e=>e.id.toLowerCase()==='caoyujie-code.vision-learning-hub');assert.ok(extension);
  hub=await extension.activate();await hub.ensure();passed.push('isolated VS Code extension starts packaged Python runtime');
  const boot=await hub.request('/bootstrap');assert.equal(boot.lessons.length,53);assert.equal(boot.courses.length,33);assert.equal(hub.test.items.size,53);passed.push('44 exercises + 9 native projects, 33 courses and Test Explorer items');
  for(const key of ['V13','Y05','L02']){
   const source=(await hub.request('/lesson/'+key+'/reference')).code;
   await fs.writeFile(hub.file(key),source,'utf8');
   const checked=await hub.run(key,true);assert.ok(checked.result?.passed,JSON.stringify(checked));
   assert.equal(checked.result.reports.length,5);passed.push(key+' new exercise verifies from packaged native source');
  }
  for(const key of ['E01','E02','E03','E04','E05','E06','E07','E08','E09']){
   const files=JSON.parse((await hub.request('/lesson/'+key+'/reference')).code);
   for(const [name,content]of Object.entries(files))await fs.writeFile(path.join(path.dirname(hub.file(key)),name),content,'utf8');
   const result=await hub.run(key,true);assert.ok(result.result?.passed,JSON.stringify(result));assert.equal(result.result.reports.length,5);
   passed.push(key+' multi-file project produces verified artifacts from packaged runtime');
  }
  await hub.message('openProjectFile',{key:'E05',name:'checkpoint.py'});
  const checkpointEditor=vscode.window.activeTextEditor;
  await checkpointEditor.edit(edit=>edit.insert(new vscode.Position(0,0),'# native checkpoint edit\n'));
  const checkpointStarted=await hub.message('api',{path:'/jobs',method:'POST',body:{lesson:'E05',code:'ignored IDE draft',note:'native guide',verify:false,project_block:'io',block_source:'own'}});
  let checkpointJob;
  for(let i=0;i<100;i++){checkpointJob=await hub.request('/jobs/'+checkpointStarted.json.id);if(!['queued','running'].includes(checkpointJob.status))break;await new Promise(r=>setTimeout(r,100));}
  assert.equal(checkpointJob.status,'done');assert.ok(checkpointJob.result.passed);assert.ok(!checkpointEditor.document.isDirty);
  assert.equal((await hub.request('/projects/E05')).block_progress['io:own'].state,'passed');
  assert.equal((await hub.request('/bootstrap')).passed.E05,false);
  passed.push('native checkpoint saves dirty source and never grants whole-project completion');
  const beforeGuide=await fs.readFile(hub.file('E01'),'utf8');
  await hub.message('api',{path:'/projects/E01/guide',method:'POST',body:{}});
  assert.equal(await fs.readFile(hub.file('E01'),'utf8'),beforeGuide);
  passed.push('guided initialization preserves existing native source');
  const projectEnded=new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(new Error('project terminal timeout')),20000);const disposable=vscode.tasks.onDidEndTaskProcess(e=>{if(e.execution.task.name==='Vision E01'){clearTimeout(timer);disposable.dispose();resolve(e.exitCode);}});});
  await hub.native('E01',false);assert.equal(await projectEnded,0);await fs.access(path.join(hub.data,'debug','E01','results.json'));passed.push('engineering CLI runs through native VS Code terminal and writes results.json');
  await hub.message('openProjectFile',{key:'E01',name:'imaging.py'});const projectEditor=vscode.window.activeTextEditor;
  assert.equal(path.basename(projectEditor.document.fileName),'imaging.py');await projectEditor.edit(edit=>edit.insert(new vscode.Position(0,0),'# learner module edit\n'));assert.ok(projectEditor.document.isDirty);
  assert.ok((await hub.run('E01',true)).result.passed);assert.ok(!projectEditor.document.isDirty);passed.push('project helper opens natively and is saved before verification');
  await assert.rejects(hub.message('openProjectFile',{key:'E01',name:'../escape.py'}));
  await hub.show('projects');for(let i=0;i<100&&hub.viewState?.page!=='projects';i++)await new Promise(r=>setTimeout(r,100));
  assert.equal(hub.viewState.page,'projects');passed.push('engineering project navigation renders in VS Code');
  const code=(await hub.request('/lesson/V01/reference')).code;
  await hub.openExercise('V01');const editor=vscode.window.activeTextEditor;assert.equal(path.basename(editor.document.fileName),'V01.py');
  await editor.edit(edit=>edit.replace(new vscode.Range(0,0,editor.document.lineCount,0),code));assert.ok(editor.document.isDirty);
  const job=await hub.run('V01',true);assert.ok(job.result?.passed,JSON.stringify(job));assert.equal(job.result.reports.length,5);assert.ok(!editor.document.isDirty);const savedCode=await fs.readFile(hub.file('V01'),'utf8');assert.equal(savedCode.replace(/\r\n/g,'\n'),code);passed.push('native dirty editor is saved and verified against five fixtures');
  const ended=new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(new Error('native task timeout')),20000);const disposable=vscode.tasks.onDidEndTaskProcess(e=>{if(e.execution.task.name==='Vision V01'){clearTimeout(timer);disposable.dispose();resolve(e.exitCode);}});});
  await hub.native('V01',false);assert.equal(await ended,0);passed.push('native Python terminal task executes real source');
  if(process.env.VLH_TEST_DEBUG==='1'){
   const breakpoint=new vscode.SourceBreakpoint(new vscode.Location(vscode.Uri.file(hub.file('V01')),new vscode.Position(2,0)));
   vscode.debug.addBreakpoints([breakpoint]);let debugSession;
   let resolveStopped;const stopped=new Promise(resolve=>{resolveStopped=resolve;});
   const tracker=vscode.debug.registerDebugAdapterTrackerFactory('debugpy',{createDebugAdapterTracker(session){debugSession=session;return {onDidSendMessage(message){if(message.type==='event'&&message.event==='stopped')resolveStopped({session,threadId:message.body.threadId});}};}});
   try{
    assert.ok(await hub.native('V01',true));
    let timer;const hit=await Promise.race([stopped,new Promise((_,reject)=>{timer=setTimeout(()=>reject(new Error('Python breakpoint was not hit')),35000);})]);clearTimeout(timer);
    const stack=await hit.session.customRequest('stackTrace',{threadId:hit.threadId,startFrame:0,levels:1});
    assert.equal(path.basename(stack.stackFrames[0].source.path),'V01.py');
    const scopes=await hit.session.customRequest('scopes',{frameId:stack.stackFrames[0].id});
    const variables=await hit.session.customRequest('variables',{variablesReference:scopes.scopes[0].variablesReference});
    assert.ok(variables.variables.some(v=>v.name==='image'));
    await hit.session.customRequest('continue',{threadId:hit.threadId});
    passed.push('Python Debugger hits real V01 breakpoint and exposes image variable');
   }finally{tracker.dispose();vscode.debug.removeBreakpoints([breakpoint]);if(debugSession)await vscode.debug.stopDebugging(debugSession);}
  }
  await hub.request('/lesson/V01','PUT',{code:'stale web code',note:'host note'});assert.equal(await fs.readFile(hub.file('V01'),'utf8'),savedCode);passed.push('stale panel draft cannot overwrite IDE code');
  await hub.request('/settings/bookmarks','PUT',{value:['R01']});
  await hub.show('practice','V01');assert.ok(hub.panel.webview.html.includes('Content-Security-Policy'));assert.ok(!hub.panel.webview.html.includes('<iframe'));
  for(let i=0;i<100&&!hub.viewState;i++)await new Promise(r=>setTimeout(r,100));
  assert.equal(hub.viewState?.lessons,53,'Webview must execute React and communicate through the bridge');passed.push('native learning webview created with local assets');
  const report=await require('../src/environment.cjs').probePython(hub.pythonExe);assert.ok(report.ok);assert.ok(report.checks.some(c=>c.module==='cv2'&&c.ok));passed.push('structured environment diagnosis identifies Python and required packages');
  await hub.message('viewReady',{page:'practice',course:null,lesson:'V01',lessons:53});
  assert.equal(hub.context.workspaceState.get(hub.stateKey()).lesson,'V01');
  hub.panel.dispose();await hub.show();
  for(let i=0;i<100&&(hub.viewState?.page!=='practice'||hub.viewState?.lesson!=='V01');i++)await new Promise(r=>setTimeout(r,100));
  assert.equal(hub.viewState.lesson,'V01');assert.equal(hub.viewState.page,'practice');passed.push('closed learning panel restores persistent page and exercise');
  await hub.message('viewReady',{page:'project',course:null,lesson:'E09',lastBasic:'V13',lastProject:'E09',lastLearning:'E09',memory:{'E09.tab':'代码与运行','E09.file':'imaging.py'},trail:[{page:'practice',lesson:'T13',course:null}],lessons:53});
  hub.panel.dispose();await hub.show();
  for(let i=0;i<100&&(hub.viewState?.page!=='project'||hub.viewState?.lesson!=='E09');i++)await new Promise(r=>setTimeout(r,100));
  assert.equal(hub.viewState.page,'project');assert.equal(hub.viewState.lesson,'E09');assert.equal(hub.viewState.memory['E09.file'],'imaging.py');assert.equal(hub.viewState.lastBasic,'V13',JSON.stringify(hub.viewState));passed.push('engineering page and source tab restore in packaged Webview');
  await hub.show('practice');
  for(let i=0;i<100&&(hub.viewState?.page!=='practice'||hub.viewState?.lesson!=='V13');i++)await new Promise(r=>setTimeout(r,100));
  assert.equal(hub.viewState.page,'practice');assert.equal(hub.viewState.lesson,'V13');passed.push('native basic entry leaves project and restores last basic lesson');

  const handbookBoot=await hub.request('/bootstrap');assert.equal(handbookBoot.lessons.filter(l=>l.function_guide).length,44);
  const beforeExample=await fs.readFile(hub.file('T03'),'utf8');
  await hub.message('openFunctionExample',{key:'T03',id:'threshold'});
  const exampleDocument=vscode.window.activeTextEditor.document;assert.equal(path.basename(exampleDocument.fileName),'threshold.py');assert.ok(exampleDocument.getText().includes('cv2.threshold'));
  await fs.appendFile(exampleDocument.fileName,'\n# keep learner experiment\n');
  await hub.message('openFunctionExample',{key:'T03',id:'threshold'});
  assert.ok((await fs.readFile(exampleDocument.fileName,'utf8')).includes('keep learner experiment'));
  assert.equal(await fs.readFile(hub.file('T03'),'utf8'),beforeExample);
  await assert.rejects(hub.message('openFunctionExample',{key:'T03',id:'../outside'}),/未知函数示例/);
  passed.push('native function example opens independently and preserves edits and exercise source');
  const exampleZip=await hub.request('/lesson/T03/examples');assert.ok(Buffer.isBuffer(exampleZip)&&exampleZip.length>1000);
  passed.push('function handbook and standalone ZIP are available in packaged extension');
  const quiz=handbookBoot.lessons.find(l=>l.id==='T03').function_guide.cards.find(c=>c.id==='threshold').quiz;
  const gradesBeforeQuiz=(await hub.request('/bootstrap')).passed;
  const answered=await hub.message('api',{path:'/function-review',method:'POST',body:{card:'threshold',choice:quiz.answer,revision:quiz.revision}});
  assert.equal(answered.json.records.threshold.correct,true);assert.deepEqual((await hub.request('/bootstrap')).passed,gradesBeforeQuiz);
  await hub.stop();await hub.ensure();assert.equal((await hub.request('/function-review')).records.threshold.correct,true);
  passed.push('native understanding checks persist across service restart separately from grades');
  const visual=await hub.message('api',{path:'/lesson/T03/walkthrough',method:'GET'});assert.equal(visual.json.demo.steps.length,2);
  assert.ok(visual.json.demo.results.step2.output);passed.push('packaged visual demo exposes real step images through the native bridge');
  await hub.message('openWalkthrough',{key:'T03',parameter:130});
  const visualFile=vscode.window.activeTextEditor.document.fileName;assert.equal(path.basename(visualFile),'practice.py');
  await fs.appendFile(visualFile,'\n# keep my visual experiment\n');await hub.message('openWalkthrough',{key:'T03',parameter:130});
  assert.ok((await fs.readFile(visualFile,'utf8')).includes('keep my visual experiment'));assert.equal(await fs.readFile(hub.file('T03'),'utf8'),beforeExample);
  await assert.rejects(hub.message('openWalkthrough',{key:'T03',parameter:999}),/参数/);passed.push('visual scaffold preserves learner edits and leaves graded source untouched');
  await hub.message('runWalkthrough',{key:'T03',parameter:130});
  const visualZip=path.join(path.dirname(visualFile),'results.zip');for(let i=0;i<100;i++){try{await fs.stat(visualZip);if(hub.tasks.size===0)break;}catch{}await new Promise(r=>setTimeout(r,100));}
  const emptyVisual=await hub.message('readWalkthrough',{key:'T03',parameter:130});assert.deepEqual(emptyVisual.results,{});passed.push('native task runs the learner scaffold and empty runs show no invented results');
  const scaffold=await fs.readFile(visualFile,'utf8');await fs.writeFile(visualFile,'raise RuntimeError("before result archive")\n');await hub.message('runWalkthrough',{key:'T03',parameter:130});
  for(let i=0;i<100&&hub.tasks.size;i++)await new Promise(r=>setTimeout(r,100));
  await assert.rejects(hub.message('readWalkthrough',{key:'T03',parameter:130}),/尚未生成/);await fs.writeFile(visualFile,scaffold);passed.push('early native execution failure cannot import a previous results archive as current');
  await new Promise((resolve,reject)=>require('node:child_process').execFile(hub.pythonExe,[path.join(path.dirname(visualFile),'reference.py')],{env:{...process.env,PYTHONUTF8:'1'}},(error)=>error?reject(error):resolve()));
  const visualOwn=await hub.message('readWalkthrough',{key:'T03',parameter:130});assert.equal(Object.keys(visualOwn.results).length,2);assert.ok(visualOwn.results.step2.output);assert.deepEqual((await hub.request('/bootstrap')).passed,gradesBeforeQuiz);
  const visualState={...visual.json.progress,step:1,notes:{step2:'host visual note'},done:[0]};await hub.message('api',{path:'/lesson/T03/walkthrough/progress',method:'POST',body:visualState});
  await hub.stop();await hub.ensure();assert.equal((await hub.request('/lesson/T03/walkthrough')).progress.notes.step2,'host visual note');passed.push('native result imports and step progress survive service restart without granting grades');
  const featureRef=JSON.parse((await hub.request('/lesson/E07/reference')).code);
  const featureRoot=path.join(hub.root,'projects','E07');for(const [name,content] of Object.entries(featureRef))await fs.writeFile(path.join(featureRoot,name),content);
  const featureJob=await hub.request('/jobs','POST',{lesson:'E07',code:JSON.stringify(featureRef),note:'',verify:false,project_block:'matches',block_source:'standard'});
  let step;for(let i=0;i<200;i++){step=await hub.request('/jobs/'+featureJob.id);if(!['queued','running'].includes(step.status))break;await new Promise(r=>setTimeout(r,100));}
  assert.ok(step.result?.passed,JSON.stringify(step));assert.equal(step.result.verify,false);
  passed.push('packaged E07 Hamming step executes with explicit standard upstream input');
  const crashed=hub.child;crashed.kill();
  for(let i=0;i<100&&hub.service;i++)await new Promise(r=>setTimeout(r,50));
  assert.ok(hub.failure);assert.equal(hub.service,null);await assert.rejects(hub.request('/bootstrap'),/服务已退出/);
  await hub.restart();assert.equal((await hub.request('/bootstrap')).passed.V01,true);passed.push('unexpected Python exit is reported and explicit restart preserves progress');
  const old=hub.service.url;await hub.stop();await hub.ensure();assert.equal((await hub.request('/bootstrap')).passed.V01,true);assert.equal((await hub.request('/lesson/V01')).note,'host note');passed.push('service restart preserves grades and notes');
  await hub.request('/clear','POST',{scope:'cache',confirmation:'CLEAR'});assert.equal((await hub.request('/bootstrap')).passed.V01,true);
  await hub.request('/clear','POST',{scope:'history',confirmation:'CLEAR'});assert.equal((await hub.request('/bootstrap')).passed.V01,false);assert.equal((await hub.request('/lesson/V01')).note,'host note');
  await hub.request('/clear','POST',{scope:'all',confirmation:'CLEAR'});assert.deepEqual((await hub.request('/bootstrap')).settings,{});assert.equal((await hub.request('/lesson/V01')).note,'');assert.equal(await fs.readFile(hub.file('V01'),'utf8'),savedCode);passed.push('three clear scopes preserve source and obey their boundaries');
  const {zipSync,unzipSync,strToU8,strFromU8}=require('fflate');
  const crypto=require('node:crypto');
  const content=unzipSync(await fs.readFile(process.env.VLH_TEST_PACKAGE));
  const manifest=JSON.parse(strFromU8(content['extension/package.json']));const parts=manifest.version.split('.').map(Number);parts[2]++;const nextVersion=parts.join('.');manifest.version=nextVersion;content['extension/package.json']=strToU8(JSON.stringify(manifest));
  content['extension.vsixmanifest']=strToU8(strFromU8(content['extension.vsixmanifest']).replace(/(<Identity\b[^>]*\bVersion=")[^"]+(" )/,(_all,prefix,suffix)=>prefix+nextVersion+suffix).replace(/(<Identity\b[^>]*\bVersion=")[^"]+(")/,(_all,prefix,suffix)=>prefix+nextVersion+suffix));
  const updateBytes=Buffer.from(zipSync(content));
  const update={version:nextVersion,name:'vision-learning-hub-'+nextVersion+'.vsix',url:'https://api.github.com/repos/CaoYujie-code/VisionLearningHub/releases/assets/123',size:updateBytes.length,digest:crypto.createHash('sha256').update(updateBytes).digest('hex')};
  hub.updater.fetcher=async()=>new Response(updateBytes);
  hub.updater.notify=async()=> '稍后';
  assert.ok(await hub.updater.install(update,undefined));
  const installed=await fs.readdir(process.env.VLH_ISOLATED_EXTENSIONS);assert.ok(installed.some(name=>name.toLowerCase().startsWith('caoyujie-code.vision-learning-hub-'+nextVersion)));
  passed.push('verified update installs via official VS Code command in isolated extensions directory');
  const finalUrl=hub.service.url;await hub.stop();let closed=false;try{await fetch(finalUrl,{signal:AbortSignal.timeout(500)});}catch{closed=true;}assert.ok(closed);passed.push('owned service stops');
  await fs.writeFile(process.env.VLH_TEST_REPORT,JSON.stringify({passed,errors:[]},null,2));
 }catch(error){await fs.writeFile(process.env.VLH_TEST_REPORT,JSON.stringify({passed,error:error?.stack||error?.message||String(error)},null,2));throw error;}
 finally{await hub?.stop();hub?.panel?.dispose();}
};
