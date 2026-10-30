import {isIDE,bridgeRequest,ide} from './ide';
import type {Project} from './projects';
export type FunctionCard = {id:string;name:string;signature:string;parameters:{name:string;meaning:string;choice:string}[];returns:string;use:string;avoid:string;pitfall:string;example:string;expect:string;experiment:string;docs:string;quiz:{question:string;options:{text:string;explanation:string}[];answer:number;revision:string}};
export type FunctionGuide = {decision:string;question:string;cards:FunctionCard[]};
export type Lesson = {id:string; title:string; goal:string; contract:string; knowledge:string; hints:string[]; prerequisites:string[]; course:string; function_guide?:FunctionGuide};
export type Course = {id:string; title:string; subtitle:string; track:string; lessons:string[]; resources:string[]; sections:{title:string; paragraphs:string[]}[]; use:string[]; avoid:string[]; checks:string[]; readiness:string};
export type Resource = {id:string; title:string; stage:string; url:string; topics:string; reading_task:string; priority:string; checked_at:string; version_note:string};
export type CourseState = {checks:number[]; note:string};
export type Boot = {walkthroughs:string[];projects:Project[]; courses:Course[]; lessons:Lesson[]; resources:Resource[]; passed:Record<string,boolean>; settings:Record<string,unknown>; attempts:number; active_job:Job|null};
export type Sample = {seed:number; input:string; output:string|null; passed:boolean; params:unknown; checks:{name:string; ok:boolean; detail:string; hint?:string}[]; summary:string; error?:{type:string; message:string; line?:number; lesson?:string}; preview_note?:string; facts?:{name:string;value:unknown}[]; artifacts?:{label:string;output:string|null}[]};
export type Report = {lesson:string; verify:boolean; passed:boolean; reports:Sample[]; log:string};
export type Job = {id:string; lesson:string; status:string; result?:Report; error?:string; stale?:boolean; passed?:Record<string,boolean>};
export type DraftData = {code:string; note:string; input:string; params:unknown; history:{stamp:number; passed:boolean; verified:boolean; report:Report}[]};
export const token = document.querySelector<HTMLMetaElement>('meta[name="vlh-token"]')?.content || '';
export async function request(path:string, init:RequestInit = {}) {
  const response = await (isIDE ? bridgeRequest : (p:string,i:RequestInit)=>fetch('/api'+p,i))(path, {...init, headers:{'X-VLH-Token':token, ...(init.body && !(init.body instanceof FormData) ? {'Content-Type':'application/json'} : {}), ...init.headers}});
  if (!response.ok) {
    const value = await response.json().catch(() => ({detail:'服务器暂时无法响应'}));
    throw new Error(typeof value.detail === 'string' ? value.detail : '输入格式不正确，请检查后重试');
  }
  return response;
}
export async function api<T>(path:string, init:RequestInit = {}):Promise<T> {return (await request(path, init)).json();}
export function send<T>(path:string, value:unknown, method='POST') {return api<T>(path,{method,body:JSON.stringify(value)});}
export async function download(path:string, name:string) {
  if(isIDE){await ide('download',{path,name});return;}
  const blob = await (await request(path)).blob(); const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a'); anchor.href=url; anchor.download=name; anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
const queues = new Map<string, Promise<unknown>>();
export function saveDraft(id:string, code:string, note:string) {
  const next = (queues.get(id) || Promise.resolve()).catch(() => {}).then(() => send<{passed:Record<string,boolean>}>('/lesson/'+id,{code,note},'PUT'));
  queues.set(id, next); return next;
}
export async function drain(id:string) {await queues.get(id);}
const settingQueues = new Map<string, Promise<unknown>>();
export function saveSettingValue(key:string,value:unknown) {
  const next=(settingQueues.get(key)||Promise.resolve()).catch(()=>{}).then(()=>send('/settings/'+key,{value},'PUT'));
  settingQueues.set(key,next);return next;
}
export const when = (stamp:number) => new Date(stamp*1000).toLocaleString('zh-CN',{month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit'});
export function courseState(boot:Boot, id:string):CourseState {return (boot.settings['hub.course.'+id] as CourseState) || {checks:[],note:''};}
