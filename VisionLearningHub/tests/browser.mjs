import {chromium} from 'playwright';
import assert from 'node:assert/strict';
import {mkdir,writeFile} from 'node:fs/promises';

const url=process.env.VLH_TEST_URL||'http://127.0.0.1:8796';
await mkdir('validation',{recursive:true});
const browser=await chromium.launch({executablePath:'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',headless:true});
const context=await browser.newContext({viewport:{width:1440,height:1000},deviceScaleFactor:1,acceptDownloads:true});
const page=await context.newPage();
const errors=[];
page.on('pageerror',e=>errors.push(e.message));
page.on('response',r=>{if(r.status()>=500)errors.push(`${r.status()} ${r.url()}`);});
let count=0;
function checked(name){count++;console.log(`PASS ${name}`);}
async function local(path,method='GET',body){return page.evaluate(async({path,method,body})=>{const token=document.querySelector('meta[name="vlh-token"]').content;const r=await fetch('/api'+path,{method,headers:{'X-VLH-Token':token,'Content-Type':'application/json'},...(body?{body:JSON.stringify(body)}:{})});if(!r.ok)throw new Error(await r.text());return r.json();},{path,method,body});}
async function noOverflow(label){assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),false,`${label} horizontal overflow`);}
async function nav(name){await page.locator('.sidebar nav').getByRole('button',{name,exact:true}).click();}
try{
 await page.goto(url);await page.getByRole('heading',{name:'沿着路线，一步步实践'}).waitFor();
 const boot=await local('/bootstrap');assert.equal(boot.courses.length,16);assert.equal(boot.lessons.length,32);
 await page.screenshot({path:'validation/01-home.png',fullPage:true});await noOverflow('desktop home');checked('home loads with 16 chapters and 32 exercises');
 await nav('学习路线');await page.getByRole('button',{name:'YOLO',exact:true}).click();assert.equal(await page.locator('.course-card').count(),3);
 await page.locator('.course-card').first().click();await page.getByText('理解训练的闭环',{exact:false}).count();
 assert.ok(await page.locator('.reading').innerText());checked('route filter and lesson reader');
 await nav('学习路线');await page.locator('.course-card').first().click();
 await page.getByLabel('我的理解与疑问').fill('浏览器验证：图像 shape 是高、宽、通道。');
 await page.getByLabel('能解释 return 与 print').check();
 await nav('学习资料库');
 await page.waitForFunction(async()=>{const token=document.querySelector('meta[name="vlh-token"]').content;const r=await fetch('/api/bootstrap',{headers:{'X-VLH-Token':token}});return (await r.json()).settings['hub.course.S00']?.note?.includes('浏览器验证');});
 checked('course note and checklist survive immediate navigation');
 await page.getByRole('textbox',{name:'搜索资料'}).fill('OpenCV');assert.ok(await page.locator('.resource-card').count()>=2);
 const star=page.locator('.resource-card').first().getByRole('button');await star.click();await page.waitForTimeout(350);
 await page.getByRole('button',{name:'只看收藏',exact:true}).click();assert.equal(await page.locator('.resource-card').count(),1);
 checked('official resources search and bookmark');
 await nav('图像实验室');await page.locator('.lab-images img').nth(2).waitFor();
 await page.getByRole('button',{name:'全局阈值 用亮度分离区域'}).click();
 await page.getByLabel('亮度阈值').fill('255');await page.getByRole('button',{name:'运行实验',exact:true}).click();
 await page.getByText('result = cv2.threshold',{exact:false}).waitFor();
 assert.ok((await page.locator('.lab-metrics').innerText()).includes('0%'));
 await page.getByLabel('实验输入').selectOption('dim');await page.getByLabel('亮度阈值').fill('90');await page.getByRole('button',{name:'运行实验',exact:true}).click();await page.waitForTimeout(450);
 await page.evaluate(()=>window.scrollTo(0,0));await page.screenshot({path:'validation/02-lab.png',fullPage:true});checked('real OpenCV threshold and changed input');
 await nav('练习工作台');const editor=page.getByRole('textbox',{name:'Python 代码编辑器'});await editor.waitFor();
 const starter=await editor.inputValue();await editor.fill('def solve(image, params):');await editor.press('End');await editor.press('Enter');await editor.press('Tab');await editor.press('Shift+Tab');await editor.pressSequentially('return []');
 assert.equal(await editor.inputValue(),'def solve(image, params):\n    return []');await editor.press('Control+s');await page.getByText('已保存到本机',{exact:true}).waitFor();await editor.fill(starter);checked('keyboard indentation, newline, and explicit save');
 await page.getByRole('button',{name:'运行样例',exact:true}).click();await page.getByText('NotImplementedError',{exact:true}).waitFor();
 assert.ok(await page.getByRole('button',{name:/定位到 P01 第/}).isVisible());checked('TODO fails with an actionable line number');
 const reference=await local('/lesson/P01/reference');await editor.fill(reference.code);
 await page.getByRole('button',{name:'多样例验收',exact:true}).click();await page.getByText('当前版本已验收',{exact:true}).waitFor();
 assert.equal(await page.locator('.sample-tabs button').count(),5);
 await page.screenshot({path:'validation/03-practice.png',fullPage:true});checked('typed implementation passes five fixtures and updates progress');
 await editor.fill(reference.code+'\n# changed during learning\n');
 await page.getByText('待验收',{exact:true}).waitFor();checked('editing invalidates current verification');
 await page.getByRole('button',{name:'笔记',exact:true}).click();await page.getByRole('textbox',{name:'练习笔记'}).fill('边界：保留面积等于阈值的元素。');
 await nav('记录与设置');
 await page.waitForFunction(async()=>{const token=document.querySelector('meta[name="vlh-token"]').content;const r=await fetch('/api/lesson/P01',{headers:{'X-VLH-Token':token}});return (await r.json()).note.includes('等于阈值');});
 await page.locator('tbody tr').first().getByRole('button',{name:'查看',exact:true}).click();await page.getByRole('dialog').waitFor();await page.getByRole('button',{name:'关闭',exact:true}).click();
 const download=page.waitForEvent('download');await page.getByRole('button',{name:'下载备份',exact:true}).click();await (await download).saveAs('validation/browser-backup.zip');
 checked('draft note navigation, historical report, and backup download');
 await nav('练习工作台');await editor.waitFor();assert.ok((await editor.inputValue()).includes('# changed during learning'));
 await editor.fill('def solve(image, params):\n    while True: pass\n');await page.getByRole('button',{name:'运行样例',exact:true}).click();await page.locator('.job-pill').waitFor();
 await page.reload();await page.locator('.job-pill').waitFor();await page.locator('.job-pill').click();await page.getByRole('button',{name:'停止',exact:true}).click();await page.getByRole('button',{name:'运行样例',exact:true}).waitFor({state:'visible'});
 await page.waitForFunction(()=>!document.querySelector('.job-pill'));checked('running task survives a browser refresh and can be stopped');

 for(const title of ['直方图与自动阈值','局部光照与自适应分割','降噪与边缘梯度','积分图与区域统计']){
  await nav('学习路线');await page.locator('.course-card').filter({hasText:title}).click();
  await page.getByRole('heading',{name:title,exact:true}).waitFor();
  assert.ok((await page.locator('.reading').innerText()).length>100);
  assert.ok(await page.locator('.task-link').count());
 }
 checked('all four new chapters expose their lesson links and reading content');
 for(const key of ['V01','V02','V03','V04','V05','V06']){
  await nav('练习工作台');await page.locator('.lesson-scroll').getByRole('button',{name:new RegExp('^'+key)}).click();
  await page.locator('.task-description h2').filter({hasText:key}).waitFor();
  const reference=await local('/lesson/'+key+'/reference');await editor.fill(reference.code);
  await page.getByRole('button',{name:'多样例验收',exact:true}).click();
  await page.getByText('当前版本已验收',{exact:true}).waitFor();
  assert.equal(await page.locator('.sample-tabs button').count(),5);
  await page.waitForFunction(()=>[...document.querySelectorAll('.image-pair img')].length===2&&[...document.querySelectorAll('.image-pair img')].every(img=>img.complete&&img.naturalWidth>0));
  checked(key+' verified in the browser with output images');
 }
 await page.evaluate(()=>window.scrollTo(0,0));await page.screenshot({path:'validation/06-v020-practice.png',fullPage:true});
 await nav('图像实验室');await page.locator('.lab-images img').nth(2).waitFor();
 const methods=[['gray','灰度转换'],['histogram','灰度直方图'],['threshold','全局阈值'],['otsu','Otsu 自动阈值'],['adaptive','局部自适应阈值'],['blur','高斯平滑'],['median','中值滤波'],['bilateral','双边滤波'],['equalize','直方图均衡'],['sobel','Sobel 梯度'],['hsv','HSV + 形态学'],['canny','Canny 边缘']];
 assert.equal(await page.locator('.method-list button').count(),12);
 let lastResult;
 for(const [key,title] of methods){
  await page.locator('.method-list button').filter({hasText:title}).click();
  if(key==='adaptive'){await page.getByLabel('局部窗口（奇数）').fill('31');await page.getByLabel('局部校正 C').fill('9');}
  const completed=page.waitForResponse(r=>r.url().endsWith('/api/lab')&&r.request().method()==='POST');
  await page.getByRole('button',{name:'运行实验',exact:true}).click();
  const response=await completed;assert.equal(response.status(),200);lastResult=await response.json();assert.equal(lastResult.method,key);
  await page.waitForFunction(src=>document.querySelectorAll('.lab-images img')[2]?.getAttribute('src')===src,lastResult.output);
 }
 checked('all 12 laboratory methods run through their visible controls');
 // A changed method must not silently retarget the lesson link for the previous result.
 await page.locator('.method-list button').filter({hasText:'Sobel 梯度'}).click();
 await page.getByText('参数已改变，点击“运行实验”更新结果。下方仍是上次运行的图像。').waitFor();
 await page.getByRole('button',{name:'去手敲练习',exact:true}).click();
 await page.locator('.task-description h2').filter({hasText:'A02'}).waitFor();
 checked('unapplied parameter changes keep the displayed result and lesson consistent');
 await nav('图像实验室');await page.locator('.lab-images img').nth(2).waitFor();
 const original=await page.request.get(url+lastResult.input);assert.equal(original.status(),200);
 await page.locator('input[type=file]').setInputFiles({name:'中文图片.png',mimeType:'image/png',buffer:await original.body()});
 await page.getByLabel('实验输入').getByRole('option',{name:'我上传的图片'}).waitFor({state:'attached'});
 const uploaded=page.waitForResponse(r=>r.url().endsWith('/api/lab')&&r.request().method()==='POST');
 await page.getByRole('button',{name:'运行实验',exact:true}).click();assert.equal((await uploaded).status(),200);
 checked('image upload and subsequent experiment work in the browser');
 await page.evaluate(()=>window.scrollTo(0,0));await page.screenshot({path:'validation/07-v020-lab.png',fullPage:true});
 await nav('记录与设置');
 const beforeClear=await local('/bootstrap');assert.ok(beforeClear.attempts>0);
 for(const [label,scope] of [['清除实验缓存','cache'],['清除验收历史','history'],['清除全部学习记录','all']]){
  await page.getByRole('button',{name:label,exact:true}).click();
  assert.ok(await page.getByRole('button',{name:'确认清除',exact:true}).isDisabled());
  await page.getByLabel('清除确认').fill('CLEAR');
  const completed=page.waitForResponse(r=>r.url().endsWith('/api/clear')&&r.request().method()==='POST');
  await page.getByRole('button',{name:'确认清除',exact:true}).click();assert.equal((await completed).status(),200);
  await page.locator('.overlay').waitFor({state:'detached'});
  const state=await local('/bootstrap');
  if(scope==='cache')assert.equal(state.attempts,beforeClear.attempts);
  else assert.equal(state.attempts,0);
  if(scope==='all')assert.deepEqual(state.settings,{});
  checked('clear '+scope+' requires explicit confirmation and obeys scope');
 }
 await page.setViewportSize({width:390,height:844});
 for(const name of ['学习总览','学习路线','图像实验室','练习工作台','学习资料库','记录与设置']){
  await nav(name);await page.waitForTimeout(300);await noOverflow('mobile '+name);
  if(name==='学习总览')await page.screenshot({path:'validation/04-mobile-home.png',fullPage:true});
  if(name==='练习工作台')await page.screenshot({path:'validation/05-mobile-practice.png',fullPage:true});
 }
 checked('all six pages fit a 390px viewport');
 assert.deepEqual(errors,[]);checked('no browser exceptions or HTTP 5xx responses');
 await writeFile('validation/browser-results.json',JSON.stringify({version:'0.3.0',chapters:16,lessons:32,labMethods:12,passed:count,errors,viewport:[1440,1000],mobile:[390,844]},null,2));
 console.log(`${count} browser workflows passed`);
}finally{await browser.close();}
