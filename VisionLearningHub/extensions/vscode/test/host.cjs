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
  const boot=await hub.request('/bootstrap');assert.equal(boot.lessons.length,32);assert.equal(boot.courses.length,16);assert.equal(hub.test.items.size,32);passed.push('32 native files, 16 courses and Test Explorer items');
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
  assert.equal(hub.viewState?.lessons,32,'Webview must execute React and communicate through the bridge');passed.push('native learning webview created with local assets');
  const report=await require('../src/environment.cjs').probePython(hub.pythonExe);assert.ok(report.ok);assert.ok(report.checks.some(c=>c.module==='cv2'&&c.ok));passed.push('structured environment diagnosis identifies Python and required packages');
  await hub.message('viewReady',{page:'practice',course:null,lesson:'V01',lessons:32});
  assert.equal(hub.context.workspaceState.get(hub.stateKey()).lesson,'V01');
  hub.panel.dispose();await hub.show();
  for(let i=0;i<100&&(hub.viewState?.page!=='practice'||hub.viewState?.lesson!=='V01');i++)await new Promise(r=>setTimeout(r,100));
  assert.equal(hub.viewState.lesson,'V01');assert.equal(hub.viewState.page,'practice');passed.push('closed learning panel restores persistent page and exercise');
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
