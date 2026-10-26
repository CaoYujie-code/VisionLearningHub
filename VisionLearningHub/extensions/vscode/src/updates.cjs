'use strict';
const crypto=require('node:crypto');
const {unzipSync,strFromU8}=require('fflate');
const REPOSITORY='CaoYujie-code/VisionLearningHub';
const API='https://api.github.com/repos/'+REPOSITORY;
const LIMIT=50*1024*1024;
function version(value){
  if(typeof value!=='string'||!/^v?(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$/.test(value))throw new Error('发布版本号无效');
  return value.replace(/^v/,'');
}
function newer(candidate,current){
  const a=version(candidate).split('.').map(Number),b=version(current).split('.').map(Number);
  for(let i=0;i<3;i++){if(a[i]!==b[i])return a[i]>b[i];}return false;
}
function releaseInfo(release,current){
  if(release.draft||release.prerelease)return null;
  const tag=version(release.tag_name);if(!newer(tag,current))return null;
  const name=`vision-learning-hub-${tag}.vsix`,asset=release.assets?.find(a=>a.name===name);
  if(!asset||!Number.isSafeInteger(asset.size)||asset.size<1||asset.size>LIMIT)throw new Error('新版本尚未提供完整 VSIX 安装包');
  if(!Number.isSafeInteger(asset.id)||asset.id<1||asset.url!==API+'/releases/assets/'+asset.id)throw new Error('更新安装包来源无效');
  if(!/^sha256:[a-f0-9]{64}$/.test(asset.digest||''))throw new Error('发布安装包缺少 SHA-256 校验值，请维护者重新上传');
  return {version:tag,name,url:asset.url,size:asset.size,digest:asset.digest.slice(7),notes:typeof release.body==='string'?release.body.slice(0,2000):'',page:'https://github.com/'+REPOSITORY+'/releases/tag/'+encodeURIComponent(release.tag_name)};
}
async function githubFetch(url,{token,accept='application/vnd.github+json',signal,fetcher=fetch}={}){
  if(!url.startsWith(API+'/'))throw new Error('更新请求超出项目仓库');
  let target=url;
  let headers={Accept:accept,'X-GitHub-Api-Version':'2022-11-28','User-Agent':'VisionLearningHub-Updater'};
  if(token)headers.Authorization='Bearer '+token;
  for(let i=0;i<5;i++){
    const response=await fetcher(target,{headers,signal,redirect:'manual'});
    if(![301,302,303,307,308].includes(response.status))return response;
    const redirected=new URL(response.headers.get('location'),target);
    if(redirected.protocol!=='https:'||!['api.github.com','github.com','release-assets.githubusercontent.com','objects.githubusercontent.com'].includes(redirected.hostname))throw new Error('更新下载重定向到不支持的地址');
    if(new URL(target).origin!==redirected.origin){headers={...headers};delete headers.Authorization;}
    target=redirected.href;
  }
  throw new Error('更新下载重定向次数过多');
}
async function latest(current,options){
  const response=await githubFetch(API+'/releases/latest',options);
  if(response.status===404){const error=new Error('尚无可用发布版本，或当前账号无权读取私有仓库');error.code='NOT_FOUND';throw error;}
  if(!response.ok)throw new Error('检查更新失败（GitHub '+response.status+'），请稍后重试');
  return releaseInfo(await response.json(),current);
}
async function download(update,identity,options){
  const response=await githubFetch(update.url,{...options,accept:'application/octet-stream'});
  if(!response.ok)throw new Error('下载安装包失败（GitHub '+response.status+'）');
  const declared=Number(response.headers.get('content-length')||0);if(declared>LIMIT)throw new Error('安装包过大');
  const chunks=[];let size=0;
  for await(const chunk of response.body){size+=chunk.length;if(size>LIMIT){await response.body.cancel?.().catch(()=>{});throw new Error('安装包过大');}chunks.push(Buffer.from(chunk));}
  const bytes=Buffer.concat(chunks);
  if(size!==update.size||crypto.createHash('sha256').update(bytes).digest('hex')!==update.digest)throw new Error('安装包校验失败，已取消更新');
  const entries=unzipSync(bytes,{filter:file=>file.name==='extension/package.json'&&file.originalSize<=1024*1024});
  if(!entries['extension/package.json'])throw new Error('安装包缺少扩展清单');
  const manifest=JSON.parse(strFromU8(entries['extension/package.json']));
  if((manifest.publisher+'.'+manifest.name).toLowerCase()!==identity.toLowerCase()||manifest.version!==update.version)throw new Error('安装包身份或版本不匹配，已取消更新');
  return bytes;
}
module.exports={API,version,newer,releaseInfo,githubFetch,latest,download};
