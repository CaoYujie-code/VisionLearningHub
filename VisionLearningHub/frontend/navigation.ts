import {useEffect,useRef,useState} from 'react';
import {readViewState,saveViewState,isIDE,ide} from './ide';
export type Page='projects'|'project'|'home'|'route'|'lab'|'practice'|'resources'|'records';
type Place={page:Page;course:string|null;lesson:string;scroll?:number};
let leave:()=>Promise<void>=async()=>{};
export function beforeLeave(save:()=>Promise<void>){leave=save;return()=>{if(leave===save)leave=async()=>{};};}
export function useMemory<T>(key:string,initial:T){
 const [value,setValue]=useState<T>(()=>readViewState().memory?.[key]??initial);
 useEffect(()=>{saveViewState({memory:{...readViewState().memory,[key]:value}});if(isIDE)void ide('rememberView',{memory:readViewState().memory}).catch(()=>{});},[key,value]);
 return [value,setValue] as const;
}
export function useNavigation(notify:(s:string)=>void){
 const initial=readViewState();
 const normalize=(v:any):Place=>({page:['home','route','projects','project','lab','practice','resources','records'].includes(v?.page)?v.page==='practice'&&/^E\d{2}$/.test(v.lesson)?'project':v.page:'home',course:typeof v?.course==='string'?v.course:null,lesson:typeof v?.lesson==='string'?v.lesson:'P01',scroll:Number.isFinite(v?.scroll)?v.scroll:0});
 const [place,setPlace]=useState<Place>(()=>normalize(initial));
 const [trail,setTrail]=useState<Place[]>(()=>Array.isArray(initial.trail)?initial.trail.slice(-30).map(normalize):[]);
 const [lastBasic,setBasic]=useState(initial.lastBasic||(!initial.lesson?.startsWith('E')?initial.lesson:null)||'P01');
 const [lastProject,setProject]=useState(initial.lastProject||'E01');
 const [lastLearning,setLast]=useState<string|null>(initial.lastLearning||null);
 const current=useRef(place);current.current=place;const stack=useRef(trail);stack.current=trail;const locked=useRef(false);
 useEffect(()=>{saveViewState({...place,trail,lastBasic,lastProject,lastLearning});},[place,trail,lastBasic,lastProject,lastLearning]);
 const apply=(target:Place,next:Place[])=>{setPlace(target);setTrail(next);current.current=target;stack.current=next;if(target.page==='practice'){setBasic(target.lesson);setLast(target.lesson);}if(target.page==='project'){setProject(target.lesson);setLast(target.lesson);}requestAnimationFrame(()=>window.scrollTo(0,target.scroll||0));};
 const move=async(target:Place,next?:Place[],pop=false)=>{
  if(locked.current)return;locked.current=true;
  try{await leave();const previous={...current.current,scroll:window.scrollY};const history=next??[...stack.current,previous].slice(-30);
   if(!isIDE&&!pop){window.history.replaceState({vlh:previous,trail:stack.current},'');window.history.pushState({vlh:target,trail:history},'');}
   apply(target,history);
  }catch(e){notify('保存失败，已留在当前页面，请重试：'+(e as Error).message);if(pop&&!isIDE)window.history.pushState({vlh:current.current,trail:stack.current},'');}
  finally{locked.current=false;}
 };
 useEffect(()=>{const y=place.scroll||0;if(!y)return;const restore=()=>{if(document.documentElement.scrollHeight-window.innerHeight>=y){window.scrollTo(0,y);observer.disconnect();}};const observer=new ResizeObserver(restore);observer.observe(document.body);const timer=setTimeout(()=>observer.disconnect(),2000);restore();return()=>{clearTimeout(timer);observer.disconnect();};},[place]);
 useEffect(()=>{const reset=()=>{setBasic('P01');setProject('E01');setLast(null);setTrail([]);saveViewState({memory:{},trail:[],lastBasic:'P01',lastProject:'E01',lastLearning:null,...current.current});if(!isIDE)window.history.replaceState({vlh:current.current,trail:[]},'');};window.addEventListener('vlh-reset-navigation',reset);return()=>window.removeEventListener('vlh-reset-navigation',reset);},[]);
 const moveRef=useRef(move);moveRef.current=move;
 useEffect(()=>{if(isIDE)return;window.history.replaceState({vlh:current.current,trail:stack.current},'');const listener=(e:PopStateEvent)=>{if(e.state?.vlh)void moveRef.current(normalize(e.state.vlh),(e.state.trail||[]).map(normalize),true);};window.addEventListener('popstate',listener);return()=>window.removeEventListener('popstate',listener);},[]);
 const go=(page:Page)=>void move({page,course:null,lesson:page==='practice'?lastBasic:page==='project'?lastProject:place.lesson});
 const openLesson=(lesson:string)=>void move({page:lesson.startsWith('E')?'project':'practice',lesson,course:null});
 const openCourse=(course:string)=>void move({page:'route',course,lesson:place.lesson});
 const back=()=>{const prev=stack.current.at(-1);void move(prev||{page:place.page==='project'?'projects':place.page==='practice'?'practice':'route',lesson:place.page==='practice'?lastBasic:place.lesson,course:null},stack.current.slice(0,-1));};
 const previous=trail.at(-1);const backLabel=previous?previous.page==='project'?'返回工程 '+previous.lesson:previous.page==='practice'?'返回练习 '+previous.lesson:previous.page==='route'&&previous.course?'返回章节 '+previous.course:({projects:'返回工程项目',home:'返回学习总览',records:'返回记录与设置',route:'返回学习路线',resources:'返回学习资料库',lab:'返回图像实验室'} as Record<string,string>)[previous.page]||'返回上一页':place.page==='project'?'返回工程项目':'返回基础练习';
 return {...place,trail,lastBasic,lastProject,lastLearning,go,openLesson,openCourse,back,backLabel,restore:(v:any)=>{if(v.memory)saveViewState({memory:v.memory});if(v.lastBasic)setBasic(v.lastBasic);if(v.lastProject)setProject(v.lastProject);if(v.lastLearning)setLast(v.lastLearning);void move(normalize(v),Array.isArray(v.trail)?v.trail.map(normalize):[]);}};
}
