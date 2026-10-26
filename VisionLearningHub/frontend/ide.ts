declare function acquireVsCodeApi(): {postMessage(value:unknown):void;getState():any;setState(value:unknown):void};
const host = typeof acquireVsCodeApi === 'function' ? acquireVsCodeApi() : null;
export const isIDE = !!host;
let sequence = 0;
const waiting = new Map<number,{resolve:(v:any)=>void;reject:(e:Error)=>void;timer:ReturnType<typeof setTimeout>}>();
window.addEventListener('message',event=>{
 const m=event.data;
 if(m?.type==='vlh-response'){
  const p=waiting.get(m.id);if(!p)return;waiting.delete(m.id);clearTimeout(p.timer);
  if(m.error)p.reject(new Error(m.error));else p.resolve(m.value);
 }
 if(m?.type==='vlh-offline')window.dispatchEvent(new CustomEvent('vlh-offline',{detail:m.message}));
 if(m?.type==='vlh-refresh')window.dispatchEvent(new Event('vlh-refresh'));
 if(m?.type==='vlh-navigate')window.dispatchEvent(new CustomEvent('vlh-navigate',{detail:m}));
});
export function ide<T=any>(action:string,args:unknown={}):Promise<T>{
 if(!host)return Promise.reject(new Error('此操作需要 VS Code 插件'));
 const id=++sequence;
 return new Promise((resolve,reject)=>{
  const timer=setTimeout(()=>{waiting.delete(id);reject(new Error('扩展响应超时，请查看 Vision 输出日志'));},120000);
  waiting.set(id,{resolve,reject,timer});host.postMessage({type:'vlh-request',id,action,args});
 });
}
export const readViewState=()=>host?.getState()||{};
export const saveViewState=(state:unknown)=>host?.setState(state);
export async function confirmAction(message:string){return isIDE?ide<boolean>('confirm',{message}):window.confirm(message);}
export async function bridgeRequest(path:string,init:RequestInit={}){
 let body:unknown=init.body;
 if(body instanceof FormData){
  const file=body.get('file');if(!(file instanceof File))throw new Error('请选择文件');
  const limit=path==='/restore'?128:12;if(file.size>limit*1024*1024)throw new Error(`文件不能超过 ${limit} MB`);
  const bytes=new Uint8Array(await file.arrayBuffer());let binary='';
  for(let i=0;i<bytes.length;i+=32768)binary+=String.fromCharCode(...bytes.subarray(i,i+32768));
  body={file:{name:file.name,type:file.type,data:btoa(binary)}};
 }
 const value=await ide<{status:number;json?:unknown;base64?:string}>('api',{path,method:init.method||'GET',body});
 if(value.base64){const raw=atob(value.base64);return new Response(Uint8Array.from(raw,c=>c.charCodeAt(0)),{status:value.status});}
 return new Response(JSON.stringify(value.json),{status:value.status,headers:{'Content-Type':'application/json'}});
}
if(host){
 document.documentElement.classList.add('ide-mode');
 document.addEventListener('click',event=>{
  const a=(event.target as Element)?.closest('a[href]');if(!a)return;
  const href=a.getAttribute('href')||'';
  if(/^https?:\/\//.test(href)){event.preventDefault();void ide('external',{url:href});}
 });
}
