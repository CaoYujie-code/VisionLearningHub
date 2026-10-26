import {chromium} from 'playwright';
import assert from 'node:assert/strict';
import {writeFile} from 'node:fs/promises';
const browser=await chromium.launch({executablePath:'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',headless:true});
const page=await browser.newPage({viewport:{width:1440,height:1000}});const errors=[];let passed=0;
page.on('pageerror',e=>errors.push(e.message));
const ok=name=>{passed++;console.log('PASS '+name);};
async function api(path,method='GET',body){return page.evaluate(async({path,method,body})=>{const r=await fetch('/api'+path,{method,headers:{'X-VLH-Token':document.querySelector('meta[name="vlh-token"]').content,'Content-Type':'application/json'},...(body?{body:JSON.stringify(body)}:{})});if(!r.ok)throw new Error(await r.text());return r.json();},{path,method,body});}
async function block(name){await page.getByRole('navigation',{name:'工程任务块'}).getByRole('button',{name,exact:false}).click();}
async function until(check){for(let i=0;i<120;i++){if(await check())return;await new Promise(resolve=>setTimeout(resolve,100));}throw new Error('Timed out waiting for checkpoint state');}
async function run(){
 const started=page.waitForResponse(r=>r.url().endsWith('/api/jobs')&&r.request().method()==='POST');
 await page.getByRole('button',{name:'检查当前任务块',exact:true}).click();
 const id=(await(await started).json()).id;
 let job;await until(async()=>{job=await api('/jobs/'+id);return !['queued','running','stopping'].includes(job.status);});
 assert.equal(job.status,'done',JSON.stringify(job));assert.ok(job.result);
 await until(()=>page.getByRole('button',{name:'检查当前任务块',exact:true}).isEnabled());
 return job.result;
}
try{
 await page.goto(process.env.VLH_TEST_URL);await page.getByRole('heading',{name:'沿着路线，一步步实践'}).waitFor();
 const reference=JSON.parse((await api('/lesson/E05/reference')).code);
 const partial={...reference,'pipeline.py':"raise NotImplementedError('pipeline not written yet')\n"};delete partial['checkpoint.py'];
 await api('/lesson/E05','PUT',{code:JSON.stringify(partial),note:JSON.stringify({projectNote:1,text:'保留旧复盘',completed:[0]})});
 await page.locator('.sidebar nav').getByRole('button',{name:'工程项目',exact:true}).click();
 await page.locator('.engineering-card').filter({hasText:'E05 ·'}).getByRole('button',{name:'进入工程任务',exact:false}).click();
 await page.getByRole('button',{name:'添加分块入口',exact:true}).click();
 await page.getByText('分块入口已就绪；已有源码保留',{exact:true}).waitFor();
 assert.equal((await api('/projects/E05')).files['pipeline.py'],partial['pipeline.py']);ok('optional guide preserves existing source');
 await page.getByRole('button',{name:'打开本块代码',exact:true}).click();await page.getByLabel('工程代码编辑器').fill(reference['checkpoint.py']);
 assert.equal((await run()).passed,true);ok('input checkpoint runs with unfinished downstream pipeline');
 await block('3. 可视化');assert.equal(await page.getByLabel('任务块输入来源').inputValue(),'standard');
 assert.equal((await run()).passed,true);assert.equal((await api('/bootstrap')).passed.E05,false);ok('standard render does not grant project completion');
 await page.getByLabel('任务块输入来源').selectOption('own');assert.equal((await run()).passed,false);ok('own input reports unfinished upstream algorithm');
 await page.getByRole('button',{name:'展开下一层提示',exact:true}).click();
 const before=(await api('/projects/E05')).files;
 await page.getByRole('button',{name:'独立挑战',exact:true}).click();assert.equal(await page.getByRole('region',{name:'分块学习面板'}).count(),0);
 await page.getByRole('button',{name:'分块引导',exact:true}).click();assert.deepEqual((await api('/projects/E05')).files,before);ok('mode switching preserves code');
 await page.getByRole('button',{name:'任务与素材',exact:true}).click();await page.screenshot({path:'validation/12-guided-engineering.png',fullPage:true});
 await until(async()=>{const note=JSON.parse((await api('/projects/E05')).note);return note.block==='render'&&note.mode==='guided'&&note.hints.render===1;});
 await page.reload();await page.getByRole('heading',{name:'沿着路线，一步步实践'}).waitFor();await page.locator('.sidebar nav').getByRole('button',{name:'工程项目',exact:true}).click();await page.locator('.engineering-card').filter({hasText:'E05 ·'}).getByRole('button',{name:'进入工程任务',exact:false}).click();await page.getByRole('heading',{name:'工程交付约定',exact:true}).waitFor();assert.equal(await page.getByLabel('任务块输入来源').inputValue(),'own');await page.getByText('提示 1：',{exact:true}).waitFor();ok('mode, task, source and hints survive reload');
 await page.getByRole('button',{name:'复盘与历史',exact:true}).click();assert.equal(await page.getByLabel('工程复盘笔记').inputValue(),'保留旧复盘');
 await page.getByRole('button',{name:'代码与运行',exact:true}).click();await page.locator('.project-files').getByRole('button',{name:'imaging.py',exact:true}).click();await page.getByLabel('工程代码编辑器').fill(reference['imaging.py']+'\n# changed\n');await page.getByRole('button',{name:'保存工程文件',exact:true}).click();
 await until(async()=>((await api('/projects/E05')).block_progress['io:own'].state==='stale'));ok('source edit invalidates checkpoint while preserving history');
 await page.setViewportSize({width:390,height:844});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),false);await page.screenshot({path:'validation/13-guided-mobile.png',fullPage:true});ok('mobile guided editor fits');
 assert.deepEqual(errors,[]);ok('no browser errors');
 await writeFile('validation/guides-browser-results.json',JSON.stringify({version:'0.6.0',passed,errors},null,2));
}finally{await browser.close();}
