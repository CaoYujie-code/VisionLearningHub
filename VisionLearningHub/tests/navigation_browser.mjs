import {chromium} from 'playwright';
import assert from 'node:assert/strict';
import {writeFile} from 'node:fs/promises';
const browser=await chromium.launch({executablePath:'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',headless:true});
const page=await browser.newPage({viewport:{width:1440,height:1000}});let passed=0;const errors=[];page.on('pageerror',e=>errors.push(e.message));
const ok=s=>{passed++;console.log('PASS '+s);};
const nav=async name=>{await page.locator('.sidebar nav').getByRole('button',{name,exact:true}).click();};
const project=async key=>{await nav('工程项目');await page.getByLabel('搜索工程').fill('');await page.locator('.engineering-card').filter({hasText:key+' ·'}).getByRole('button',{name:'进入工程任务'}).click();await page.getByRole('button',{name:'分块引导',exact:true}).waitFor();};
async function until(check){for(let i=0;i<100;i++){if(await check())return;await new Promise(r=>setTimeout(r,100));}throw new Error('Navigation state timeout');}
try{
 await page.goto(process.env.VLH_TEST_URL);await page.getByRole('button',{name:'从基础开始',exact:true}).click();await page.getByLabel('Python 代码编辑器').waitFor();
 assert.equal(await page.locator('.lesson-scroll button').count(),44);assert.equal(await page.locator('.lesson-scroll').getByRole('button',{name:/^E0/}).count(),0);ok('basic list excludes engineering tasks');
 await page.locator('.lesson-scroll').getByRole('button',{name:/^V13/}).click();await page.getByLabel('Python 代码编辑器').waitFor();
 await project('E05');await nav('基础练习');await page.locator('.task-description h2').filter({hasText:'V13'}).waitFor();ok('engineering to basics restores last basic lesson');
 await project('E07');await page.getByRole('navigation',{name:'工程任务块'}).getByRole('button',{name:/5\. 算法/}).click();
 await page.getByRole('button',{name:'代码与运行',exact:true}).click();await page.locator('.project-files').getByRole('button',{name:'imaging.py',exact:true}).click();
 const draft='def learner_marker():\n    return 707\n';await page.getByLabel('工程代码编辑器').fill(draft);
 await page.getByRole('button',{name:'复习前置题 V12',exact:true}).click();await page.getByLabel('Python 代码编辑器').waitFor();
 await page.getByRole('button',{name:'← 返回工程 E07',exact:true}).click();await page.getByLabel('工程代码编辑器').waitFor();assert.equal(await page.getByLabel('工程代码编辑器').inputValue(),draft);await page.getByRole('region',{name:'工程专属小任务'}).waitFor();ok('prerequisite return restores project block, file, tab and immediate draft');
 const detail=page.getByRole('region',{name:'工程专属小任务'}).locator('details').first();await detail.locator('summary').click();const saved=page.waitForResponse(r=>r.url().endsWith('/api/lesson/E07')&&r.request().method()==='PUT');await detail.getByRole('checkbox').check();await saved;
 await page.reload();await page.getByLabel('工程代码编辑器').waitFor();assert.equal(await page.getByLabel('工程代码编辑器').inputValue(),draft);await until(()=>page.getByRole('region',{name:'工程专属小任务'}).locator('summary').first().innerText().then(t=>t.includes('已自查')));ok('refresh preserves view and project-specific self checks');
 await nav('学习总览');await page.getByRole('button',{name:'继续上次学习 · E07',exact:true}).click();await page.getByLabel('工程代码编辑器').waitFor();await page.getByRole('button',{name:'← 返回学习总览',exact:true}).click();await page.getByRole('button',{name:'从基础开始',exact:true}).waitFor();ok('resume means last visited task, with correct origin');
 await nav('工程项目');await page.getByLabel('搜索工程').fill('E06');await page.getByRole('button',{name:'进入工程任务'}).click();await page.getByRole('button',{name:'← 返回工程项目',exact:true}).click();assert.equal(await page.getByLabel('搜索工程').inputValue(),'E06');assert.equal(await page.locator('.engineering-card').count(),1);ok('project list filter survives return');
 await nav('学习路线');await page.getByLabel('搜索课程').fill('S28');await page.locator('.course-card').click();await page.locator('.reader-side .task-link').click();await page.getByRole('button',{name:'← 返回章节 S28',exact:true}).click();await page.getByLabel('我的理解与疑问').waitFor();ok('chapter origin is retained');
 await nav('基础练习');await page.getByLabel('Python 代码编辑器').waitFor();await nav('工程项目');await page.getByLabel('搜索工程').waitFor();await page.goBack();await page.getByLabel('Python 代码编辑器').waitFor();await page.goForward();await page.getByLabel('搜索工程').waitFor();ok('browser back and forward restore route');
 await nav('基础练习');await page.getByLabel('Python 代码编辑器').fill('# draft must survive failed save\n');
 await page.route('**/api/lesson/*',route=>route.request().method()==='PUT'?route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({detail:'simulated save failure'})}):route.continue());
 await nav('工程项目');await page.getByText(/保存失败，已留在当前页面/).waitFor();assert.equal(await page.getByLabel('Python 代码编辑器').inputValue(),'# draft must survive failed save\n');await page.unroute('**/api/lesson/*');await nav('工程项目');await page.getByLabel('搜索工程').waitFor();ok('failed save blocks navigation; retry succeeds without losing source');
 await project('E09');await page.getByRole('navigation',{name:'工程任务块'}).getByRole('button',{name:/2\. 算法/}).click();await page.getByRole('region',{name:'工程专属小任务'}).waitFor();assert.equal(await page.getByRole('region',{name:'工程专属小任务'}).locator('details').count(),7);
 if(await page.getByRole('button',{name:'关闭提示',exact:true}).count())await page.getByRole('button',{name:'关闭提示',exact:true}).click();await page.getByRole('region',{name:'工程专属小任务'}).locator('summary').first().click();await page.getByText('12张模拟棋盘、空图、坏图',{exact:false}).waitFor();await page.getByRole('region',{name:'分块学习面板'}).screenshot({path:'validation/14-calibration-learning.png'});await page.setViewportSize({width:390,height:844});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),false);ok('calibration study tasks and mobile layout');
 assert.deepEqual(errors,[]);await writeFile('validation/navigation-browser-results.json',JSON.stringify({version:'0.7.0',passed,errors},null,2));
}finally{await browser.close();}
