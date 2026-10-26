import {chromium} from 'playwright';
import assert from 'node:assert/strict';
import {mkdir,writeFile,readFile} from 'node:fs/promises';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);const {unzipSync}=require('../extensions/vscode/node_modules/fflate');
const browser=await chromium.launch({executablePath:'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',headless:true});
const page=await browser.newPage({viewport:{width:1440,height:1000},acceptDownloads:true});
const url=process.env.VLH_TEST_URL;let passed=0;const errors=[];
page.on('pageerror',e=>errors.push(e.message));page.on('response',r=>{if(r.status()>=500)errors.push(String(r.status())+' '+r.url());});
function ok(name){passed++;console.log('PASS '+name);}
async function local(path,method='GET',body){return page.evaluate(async({path,method,body})=>{const token=document.querySelector('meta[name="vlh-token"]').content;const r=await fetch('/api'+path,{method,headers:{'X-VLH-Token':token,'Content-Type':'application/json'},...(body?{body:JSON.stringify(body)}:{})});if(!r.ok)throw new Error(await r.text());return r.json();},{path,method,body});}
async function nav(name){await page.locator('.sidebar nav').getByRole('button',{name,exact:true}).click();}
async function selectProject(key){await nav('工程项目');await page.locator('.engineering-card').filter({hasText:key+' ·'}).getByRole('button',{name:'进入工程任务',exact:false}).click();await page.getByRole('heading',{name:'工程交付约定',exact:true}).waitFor();}
try{
 await mkdir('validation',{recursive:true});await page.goto(url);await page.getByRole('heading',{name:'沿着路线，一步步实践'}).waitFor();
 await nav('工程项目');assert.equal(await page.locator('.engineering-card').count(),8);
 await page.waitForFunction(()=>[...document.querySelectorAll('.engineering-card>img')].every(img=>img.complete&&img.naturalWidth>0));
 await page.screenshot({path:'validation/09-engineering-projects.png',fullPage:true});ok('eight engineering briefs display attributed photographic assets');
 await page.getByLabel('搜索工程').fill('缺陷');assert.equal(await page.locator('.engineering-card').count(),1);await page.getByLabel('搜索工程').fill('');ok('engineering search filters scenario descriptions');
 for(const key of ['E01','E02','E03','E04','E05','E06','E07','E08']){
  await selectProject(key);assert.equal(await page.locator('.check-line').count(),5);
  assert.ok(await page.getByRole('link',{name:'查看上游来源说明'}).count());
  await page.locator('.check-line input').first().check();
  await page.getByRole('button',{name:'代码与运行',exact:true}).click();
  const editor=page.getByLabel('工程代码编辑器');await editor.waitFor();
  if(key==='E01'){
   await page.getByRole('button',{name:'运行开发样例',exact:true}).click();await page.getByText('NotImplementedError',{exact:true}).waitFor();ok('unfinished project fails with a visible TODO error');
  }
  const reference=JSON.parse((await local('/lesson/'+key+'/reference')).code);
  for(const [name,code]of Object.entries(reference)){
   await page.locator('.project-files').getByRole('button',{name,exact:true}).click();await editor.fill(code);
  }
  if(key==='E01'){
   await page.getByLabel('新模块文件名').fill('detector.py');await page.getByRole('button',{name:'添加模块',exact:true}).click();
   await editor.fill('def marker():\n    return "custom-module"\n');
   await page.locator('.project-files').getByRole('button',{name:'pipeline.py',exact:true}).click();await editor.fill('from detector import marker\n'+reference['pipeline.py']);
  }
  const completed=page.waitForResponse(r=>r.url().endsWith('/api/jobs')&&r.request().method()==='POST');
  await page.getByRole('button',{name:'多场景工程验收',exact:true}).click();await completed;
  await page.getByText('当前源码已验收',{exact:true}).waitFor();
  await page.waitForFunction(()=>document.querySelectorAll('.sample-tabs button').length===5);
  await page.waitForFunction(()=>[...document.querySelectorAll('.image-pair img')].length===2&&[...document.querySelectorAll('.image-pair img')].every(img=>img.complete&&img.naturalWidth>0));
  assert.equal((await local('/bootstrap')).passed[key],true);
  await page.getByRole('button',{name:'复盘与历史',exact:true}).click();await page.getByLabel('工程复盘笔记').fill(key+'：记录输入、函数分工、失败样例。');
  await nav('工程项目');
  await page.waitForFunction(async key=>{const token=document.querySelector('meta[name="vlh-token"]').content;const data=await (await fetch('/api/projects/'+key,{headers:{'X-VLH-Token':token}})).json();return JSON.parse(data.note).text.includes('失败样例');},key);
  ok(key+' multi-file editing, five batches, artifacts and engineering notes');
 }
 await selectProject('E01');assert.ok(await page.locator('.check-line input').first().isChecked());
 const download=page.waitForEvent('download');await page.getByRole('button',{name:'导出工程与素材',exact:true}).click();await (await download).saveAs('validation/engineering-E01.zip');
 const entries=unzipSync(await readFile('validation/engineering-E01.zip'));assert.ok(entries['E01/detector.py']);assert.ok(entries['E01/data/holdout/995/_manifest.json']);ok('download contains custom source, public data and holdout input batches');
 await page.getByRole('button',{name:'代码与运行',exact:true}).click();await page.getByRole('button',{name:'查看参考工程',exact:true}).click();await page.getByRole('dialog').waitFor();
 assert.ok((await page.locator('.reference-code').innerText()).includes('run_batch'));await page.getByRole('button',{name:'关闭',exact:true}).click();ok('reference project is inspectable without overwriting learner files');
 const data=await local('/projects/E01');const original=await page.request.get(url+data.images[3].input);assert.equal(original.status(),200);
 await page.locator('.upload-control input').setInputFiles({name:'我的工位.png',mimeType:'image/png',buffer:await original.body()});
 await page.waitForFunction(()=>document.querySelectorAll('.sample-tabs button').length===1);
 await page.getByText('自有图片工程交付',{exact:true}).waitFor();ok('own image exploration reports delivery without claiming labelled accuracy');
 await page.screenshot({path:'validation/10-engineering-workbench.png',fullPage:true});
 await page.setViewportSize({width:390,height:844});
 for(const key of ['E01','E04']){
  await selectProject(key);assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),false);
  await page.getByRole('button',{name:'代码与运行',exact:true}).click();assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),false);
 }
 await page.screenshot({path:'validation/11-engineering-mobile.png',fullPage:true});ok('engineering brief and modular editor fit a mobile viewport');
 assert.deepEqual(errors,[]);ok('engineering workflows have no JS exceptions or HTTP 5xx');
 await writeFile('validation/projects-browser-results.json',JSON.stringify({version:(await local('/health')).version,passed,errors,projects:8,stages:40},null,2));
}finally{await browser.close();}
