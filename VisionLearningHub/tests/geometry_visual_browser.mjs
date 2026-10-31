import {chromium} from 'playwright';
import assert from 'node:assert/strict';
import {mkdir,writeFile,mkdtemp} from 'node:fs/promises';
import path from 'node:path';
import {tmpdir} from 'node:os';
import {execFileSync} from 'node:child_process';
const browser=await chromium.launch({executablePath:'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',headless:true});
const page=await browser.newPage({viewport:{width:1480,height:1050}});const errors=[];let passed=0;
page.on('pageerror',e=>errors.push(e.message));const ok=name=>{passed++;console.log('PASS '+name);};
async function api(route){return page.evaluate(async route=>{const r=await fetch('/api'+route,{headers:{'X-VLH-Token':document.querySelector('meta[name="vlh-token"]').content}});if(!r.ok)throw new Error(await r.text());return r.json();},route);}
const region=page.getByRole('region',{name:'逐步图解学习'});
async function open(key){await page.locator('.lesson-scroll').getByRole('button',{name:new RegExp('^'+key)}).click();await page.waitForFunction(key=>document.querySelector('.task-description .mono')?.textContent===key,key);await page.getByRole('button',{name:'逐步图解',exact:true}).click();await region.locator('.walk-steps button').first().waitFor();}
async function step(index){await region.locator('.walk-steps button').nth(index).click();await region.getByText('观察与位置已保存',{exact:true}).waitFor();}
async function parameter(value){await region.getByLabel('图解实验参数').selectOption(String(value));await page.waitForFunction(value=>document.querySelector('.walk-experiment select').value===String(value)&&!document.querySelector('.walk-experiment').disabled,value);await region.getByText('观察与位置已保存',{exact:true}).waitFor();}
async function imported(key,value,mutation=''){
 const bundle=await api('/lesson/'+key+'/walkthrough/files/'+value);const folder=await mkdtemp(path.join(tmpdir(),'vlh-geometry-'));
 for(const f of bundle.files)await writeFile(path.join(folder,f.name),Buffer.from(f.base64,'base64'));
 const python=path.resolve('.venv/Scripts/python.exe');execFileSync(python,[path.join(folder,'reference.py')],{env:{...process.env,PYTHONUTF8:'1'}});
 if(mutation){await writeFile(path.join(folder,'mutate.py'),`from pathlib import Path\nimport io, zipfile, numpy as np\np=Path(__file__).with_name('results.zip')\nwith zipfile.ZipFile(p) as z: data={n:z.read(n) for n in z.namelist()}\n${mutation}\nwith zipfile.ZipFile(p,'w') as z:\n    for n,b in data.items(): z.writestr(n,b)\n`);execFileSync(python,[path.join(folder,'mutate.py')]);}
 await region.getByLabel('导入步骤结果').setInputFiles(path.join(folder,'results.zip'));await region.getByText(/已保存 \d+\/\d+ 步/).waitFor();
}
try{
 await mkdir('validation',{recursive:true});await page.goto(process.env.VLH_TEST_URL);await page.getByRole('button',{name:'从基础开始',exact:true}).click();const before=(await api('/bootstrap')).passed;
 const filter=page.getByRole('checkbox',{name:'只看有逐步图解的题（37/44）'});await filter.check();assert.equal(await page.locator('.lesson-scroll button').count(),37);await page.reload();await filter.waitFor();assert.equal(await filter.isChecked(),true);assert.equal(await page.locator('.lesson-scroll button').count(),37);await filter.uncheck();assert.equal(await page.locator('.lesson-scroll button').count(),44);ok('visual-only lesson filter persists and can return to all foundations');
 for(const key of ['P01','P02','T07','T08','T09','T12','A04','A05']){
  await open(key);const demo=(await api('/lesson/'+key+'/walkthrough')).demo;assert.equal(await region.locator('.walk-steps button').count(),demo.steps.length);
  for(let i=0;i<demo.steps.length;i++){await step(i);await page.waitForFunction(()=>[...document.querySelectorAll('.walk-step img')].every(img=>img.complete&&img.naturalWidth>0));assert.equal(await region.locator('.walk-step img').count(),2);}
  ok(key+' every stage displays and explains its real intermediate result');
 }
 await open('A05');await step(2);await region.locator('.walk-step').screenshot({path:'validation/24-nms-trace.png'});
 await open('P01');await parameter(150);await step(2);await region.getByText('空数组：无数值范围',{exact:false}).waitFor();await imported('P01',150);await region.locator('.walk-own').getByText(/超出容差的元素：0 \/ 0/).waitFor();await region.locator('.walk-step').getByText('查看原始数值表',{exact:true}).last().click();await region.locator('.walk-step').getByText('空结果：没有符合条件的项',{exact:true}).waitFor();ok('empty filtered indices render and import as an empty table, never as a fake zero row');
 await open('A04');await step(0);await imported('A04',0,"raw=io.BytesIO(); np.save(raw,np.array([[0.5]]),allow_pickle=False); data['step3.npy']=raw.getvalue()");
 await region.getByRole('button',{name:'定位首个有差异的步骤'}).click();await region.getByText('观察与位置已保存',{exact:true}).waitFor();assert.equal((await api('/lesson/A04/walkthrough')).progress.step,2);await region.locator('.walk-own').getByText(/首个差异的数组索引.*\[0, 0\]/).waitFor();if(await page.getByLabel('关闭提示',{exact:true}).count())await page.getByLabel('关闭提示',{exact:true}).click();await region.locator('.walk-own').screenshot({path:'validation/25-numeric-difference.png'});assert.deepEqual((await api('/bootstrap')).passed,before);ok('changed raw result reveals numeric error and jumps to the first differing step without granting completion');
 await page.reload();await region.getByRole('button',{name:'定位首个有差异的步骤'}).waitFor();await region.locator('.walk-own').getByText(/超出容差的元素：1 \/ 1/).waitFor();ok('diagnostic snapshot and selected step survive reload');
 await imported('A04',0,"raw=io.BytesIO(); np.save(raw,np.array([[0.5,0.1]]),allow_pickle=False); data['step3.npy']=raw.getvalue()");await region.locator('.walk-own').getByText('尺寸或类型不一致，先核对数组约定，再比较数值。',{exact:true}).waitFor();ok('incompatible shapes explain why numeric comparison is unavailable');
 if(await page.getByLabel('关闭提示',{exact:true}).count())await page.getByLabel('关闭提示',{exact:true}).click();await page.setViewportSize({width:390,height:844});await open('A05');await step(2);await region.getByText('查看原始数值表',{exact:true}).last().click();assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),false);await region.locator('.walk-step').screenshot({path:'validation/26-nms-mobile.png'});ok('NMS trace and numeric table fit a narrow screen');
 assert.deepEqual(errors,[]);await writeFile('validation/geometry-visual-browser-results.json',JSON.stringify({version:'0.11.0',passed,errors},null,2));
}finally{await browser.close();}
