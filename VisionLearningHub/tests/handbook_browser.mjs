import {chromium} from 'playwright';
import assert from 'node:assert/strict';
import {mkdir,writeFile} from 'node:fs/promises';
const browser=await chromium.launch({executablePath:'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',headless:true});
const page=await browser.newPage({viewport:{width:1440,height:1080}});const errors=[];let passed=0;
page.on('pageerror',e=>errors.push(e.message));const ok=name=>{passed++;console.log('PASS '+name);};
async function api(path,method='GET',body){return page.evaluate(async({path,method,body})=>{const r=await fetch('/api'+path,{method,headers:{'X-VLH-Token':document.querySelector('meta[name="vlh-token"]').content,'Content-Type':'application/json'},...(body?{body:JSON.stringify(body)}:{})});if(!r.ok)throw new Error(await r.text());return r.json();},{path,method,body});}
async function until(check){for(let i=0;i<180;i++){if(await check())return;await new Promise(r=>setTimeout(r,100));}throw new Error('timed out');}
async function run(){const wait=page.waitForResponse(r=>r.url().endsWith('/api/jobs')&&r.request().method()==='POST');await page.getByRole('button',{name:'检查当前任务块',exact:true}).click();const id=(await(await wait).json()).id;let job;await until(async()=>{job=await api('/jobs/'+id);return !['queued','running','stopping'].includes(job.status);});assert.equal(job.status,'done',JSON.stringify(job));await until(()=>page.getByRole('button',{name:'检查当前任务块',exact:true}).isEnabled());return job.result;}
try{
 await mkdir('validation',{recursive:true});await page.goto(process.env.VLH_TEST_URL);await page.getByRole('button',{name:'从基础开始',exact:true}).click();
 await page.locator('.lesson-scroll').getByRole('button',{name:/^T03/}).click();await page.getByLabel('Python 代码编辑器').waitFor();
 const before=await api('/lesson/T03');const passedBefore=(await api('/bootstrap')).passed;
 await page.getByRole('button',{name:'先学本题函数怎么用',exact:true}).click();const guide=page.getByRole('region',{name:'函数与场景学习'});
 assert.equal(await page.getByRole('navigation',{name:'函数讲解列表'}).getByRole('button').count(),2);
 await guide.getByRole('button',{name:'cv2.threshold：固定阈值与Otsu',exact:true}).click();await guide.getByRole('table').waitFor();assert.ok((await guide.getByLabel('函数最小示例').innerText()).includes('assert used==100'));await guide.getByText('适合什么场景',{exact:true}).waitFor();ok('T03 exposes parameters, outputs, scenarios and executable assertions');
 await page.getByLabel('函数查阅范围').selectOption('all');assert.equal(await page.getByRole('navigation',{name:'函数讲解列表'}).getByRole('button').count(),40);
 await page.getByLabel('搜索函数或场景').fill('椒盐');assert.ok(await page.getByRole('navigation',{name:'函数讲解列表'}).getByRole('button').count()>0);
 await page.getByLabel('搜索函数或场景').fill('not-a-function');await page.getByRole('status').filter({hasText:'没有匹配内容'}).waitFor();
 await page.getByLabel('搜索函数或场景').fill('');await page.getByLabel('函数查阅范围').selectOption('current');await guide.getByRole('button',{name:'cv2.threshold：固定阈值与Otsu',exact:true}).click();ok('all-function search, scenario search and empty state');
 const dl=page.waitForEvent('download');await guide.getByRole('button',{name:'下载当前题 T03 的示例与讲义',exact:true}).click();const zip=await dl;assert.equal(zip.suggestedFilename(),'T03-function-examples.zip');await zip.saveAs('validation/T03-function-examples.zip');
 assert.equal((await api('/lesson/T03')).code,before.code);assert.deepEqual((await api('/bootstrap')).passed,passedBefore);ok('download is separate from learner source and progress');
 await guide.getByRole('button',{name:/^V06 /}).click();await page.locator('.task-description h2').filter({hasText:'V06'}).waitFor();await page.getByRole('button',{name:/← 返回练习 T03/}).click();await guide.waitFor();await guide.getByRole('heading',{name:'cv2.threshold：固定阈值与Otsu',exact:true}).waitFor();ok('related lesson and back restore function selection');
 await guide.getByRole('button',{name:'去笔记记录实验',exact:true}).click();const save=page.waitForResponse(r=>r.url().endsWith('/api/lesson/T03')&&r.request().method()==='PUT');await page.getByLabel('练习笔记').fill('预测：100等于阈值应输出0；实测通过。');await save;
 await page.getByRole('button',{name:'函数与场景',exact:true}).click();await page.reload();await guide.waitFor();await guide.getByRole('heading',{name:'cv2.threshold：固定阈值与Otsu',exact:true}).waitFor();assert.ok((await api('/lesson/T03')).note.includes('实测通过'));ok('experiment note and function tab survive refresh');
 await guide.screenshot({path:'validation/15-function-handbook.png'});await page.setViewportSize({width:390,height:844});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),false);await guide.screenshot({path:'validation/16-function-handbook-mobile.png'});ok('handbook is readable without page overflow on mobile');await page.setViewportSize({width:1440,height:1080});
 const ref=JSON.parse((await api('/lesson/E07/reference')).code);ref['main.py']="raise NotImplementedError('full project unfinished')\n";
 ref['feature_steps.py']=ref['feature_steps.py'].replace('def run_step(block,input_dir,output_dir,config):',"def run_step(block,input_dir,output_dir,config):\n    if block=='features':raise RuntimeError('upstream unfinished')");
 await api('/lesson/E07','PUT',{code:JSON.stringify(ref),note:JSON.stringify({projectNote:2,text:'',completed:[],mode:'guided',block:'matches',source:'standard',hints:{},studied:[]})});
 await page.locator('.sidebar nav').getByRole('button',{name:'工程项目',exact:true}).click();await page.getByLabel('搜索工程').fill('E07');await page.getByRole('button',{name:'进入工程任务'}).click();
 const nav=page.getByRole('navigation',{name:'工程任务块'});await nav.waitFor();assert.equal(await nav.getByRole('button').count(),10);await page.getByLabel('任务块输入来源').selectOption('standard');assert.equal((await run()).passed,true);await page.getByText('本次测量事实',{exact:true}).waitFor();await page.getByText('逐张中间结果',{exact:true}).click();assert.ok(await page.locator('.report-artifacts img').count()>0);assert.equal((await api('/bootstrap')).passed.E07,false);ok('E07 standard matching is independently checked and shows measured facts and artifacts');
 await page.getByLabel('任务块输入来源').selectOption('own');assert.equal((await run()).passed,false);await page.getByText('排查建议：',{exact:true}).waitFor();assert.equal((await api('/projects/E07')).block_progress['matches:standard'].state,'passed');ok('unfinished own upstream fails without erasing standard-input result');
 assert.deepEqual(errors,[]);await writeFile('validation/handbook-browser-results.json',JSON.stringify({version:'0.8.0',passed,errors},null,2));
}finally{await browser.close();}
