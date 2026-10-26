import {chromium} from 'playwright';
import assert from 'node:assert/strict';
const browser=await chromium.launch({executablePath:'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',headless:true});
try{
 const page=await browser.newPage({viewport:{width:1440,height:1000}});
 await page.goto(process.env.VLH_TEST_URL||'http://127.0.0.1:8796');
 await page.getByRole('heading',{name:'沿着路线，一步步实践'}).waitFor();
 await page.screenshot({path:'validation/01-home.png',fullPage:true});
 await page.locator('.sidebar nav').getByRole('button',{name:'图像实验室',exact:true}).click();
 await page.locator('.lab-images img').nth(2).waitFor();
 await page.getByRole('button',{name:'全局阈值 用亮度分离区域'}).click();
 await page.getByLabel('实验输入').selectOption('dim');
 await page.getByLabel('亮度阈值').fill('90');
 await page.getByRole('button',{name:'运行实验',exact:true}).click();
 await page.waitForFunction(()=>document.querySelector('.reference-code')?.textContent.includes('threshold(gray, 90'));
 await page.evaluate(()=>window.scrollTo(0,0));
 await page.screenshot({path:'validation/02-lab.png',fullPage:true});
 for(const width of [1440,390]){
  await page.setViewportSize({width,height:1000});
  await page.waitForTimeout(150);
  const boxes=await page.locator('.photo img').evaluateAll(images=>images.map(img=>{
   const image=img.getBoundingClientRect(),frame=img.closest('figure').getBoundingClientRect();
   return {bottom:image.bottom,limit:frame.bottom,right:image.right,edge:frame.right,complete:img.complete&&img.naturalWidth>0};
  }));
  for(const box of boxes){assert.ok(box.complete);assert.ok(box.bottom<=box.limit+1,JSON.stringify(box));assert.ok(box.right<=box.edge+1);}
 }
 console.log('PASS desktop/mobile image previews display without cropping');
}finally{await browser.close();}
