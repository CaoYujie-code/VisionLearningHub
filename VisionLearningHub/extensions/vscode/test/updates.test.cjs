const {test}=require('node:test');
const assert=require('node:assert/strict');
const crypto=require('node:crypto');
const {zipSync,strToU8}=require('fflate');
const {API,newer,releaseInfo,githubFetch,latest,download}=require('../src/updates.cjs');
const identity='CaoYujie-code.vision-learning-hub';
function fixture(manifest={publisher:'CaoYujie-code',name:'vision-learning-hub',version:'0.3.2'}){
 const bytes=Buffer.from(zipSync({'extension/package.json':strToU8(JSON.stringify(manifest))}));
 const release={tag_name:'v0.3.2',draft:false,prerelease:false,assets:[{id:7,url:API+'/releases/assets/7',name:'vision-learning-hub-0.3.2.vsix',size:bytes.length,digest:'sha256:'+crypto.createHash('sha256').update(bytes).digest('hex')}]};
 return {bytes,release,update:releaseInfo(release,'0.3.1')};
}
test('numeric versions prevent downgrades and reject malformed releases',()=>{
 assert.ok(newer('v0.3.10','0.3.2'));assert.ok(!newer('0.3.1','0.3.1'));assert.ok(!newer('0.2.9','0.3.1'));
 assert.throws(()=>newer('0.3.2-beta','0.3.1'));assert.equal(releaseInfo({...fixture().release,prerelease:true},'0.3.1'),null);
 assert.equal(releaseInfo(fixture().release,'0.3.2'),null);
});
test('release requires correct asset source, size and digest',()=>{
 for(const patch of [{digest:null},{size:51*1024*1024},{url:'https://other.test/file'},{name:'other.vsix'}]){
  const f=fixture();Object.assign(f.release.assets[0],patch);assert.throws(()=>releaseInfo(f.release,'0.3.1'));
 }
});
test('verified package identity and version are checked before installation',async()=>{
 const f=fixture();assert.deepEqual(await download(f.update,identity,{fetcher:async()=>new Response(f.bytes)}),f.bytes);
 await assert.rejects(download({...f.update,digest:'a'.repeat(64)},identity,{fetcher:async()=>new Response(f.bytes)}),/校验失败/);
 const other=fixture({publisher:'another',name:'extension',version:'0.3.2'});
 await assert.rejects(download(other.update,identity,{fetcher:async()=>new Response(other.bytes)}),/身份或版本/);
 const wrong=fixture({publisher:'CaoYujie-code',name:'vision-learning-hub',version:'0.3.3'});
 await assert.rejects(download(wrong.update,identity,{fetcher:async()=>new Response(wrong.bytes)}),/身份或版本/);
});
test('private asset redirects never forward GitHub credentials to asset hosts',async()=>{
 const calls=[];await githubFetch(API+'/releases/assets/7',{token:'test-only',fetcher:async(url,init)=>{
  calls.push({url,headers:{...init.headers}});
  return calls.length===1?new Response(null,{status:302,headers:{location:'https://release-assets.githubusercontent.com/example'}}):new Response('asset');
 }});
 assert.equal(calls[0].headers.Authorization,'Bearer test-only');assert.equal(calls[1].headers.Authorization,undefined);
 await assert.rejects(githubFetch(API+'/releases/assets/7',{fetcher:async()=>new Response(null,{status:302,headers:{location:'https://untrusted.test/asset'}})}),/重定向/);
});
test('missing and failed release queries return actionable errors',async()=>{
 await assert.rejects(latest('0.3.1',{fetcher:async()=>new Response('{}',{status:404})}),e=>e.code==='NOT_FOUND');
 await assert.rejects(latest('0.3.1',{fetcher:async()=>new Response('{}',{status:403})}),/GitHub 403/);
 const f=fixture();assert.equal((await latest('0.3.1',{fetcher:async()=>new Response(JSON.stringify(f.release))})).version,'0.3.2');
});
