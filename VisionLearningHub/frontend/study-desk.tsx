import {useEffect,useRef,useState} from 'react';
import {StudyPlanEditor,planLabels,Plan} from './study-plan';
import {api,download,send} from './api';
import {useMemory} from './navigation';
import './study-desk.css';

type Result={status:'none'|'stale'|'parameter'|'check'|'same'|'unreadable';saved:number;missing:number;different:number;unknown:number};
type Row={plan:Plan;id:string;title:string;total:number;step:number;step_title:string;parameter:number;done:number;notes:{step:number;title:string;text:string}[];started:boolean;changed:boolean;verified:boolean;attention:boolean;result:Result};
type Data={rows:Row[];counts:{total:number;started:number;verified:number;notes:number;attention:number}};
const filters=[['next','下一步学'],['stuck','暂时卡住'],['review','待复习'],['continue','继续学习'],['attention','结果待检查'],['notes','有观察笔记'],['verify','待正式验收'],['all','全部基础题']];
function resultText(r:Result){
 if(r.status==='none')return '尚未导入自己的步骤结果';
 if(r.status==='stale')return '导入结果属于旧课程版本，请重新生成实验包';
 if(r.status==='parameter')return '导入参数与当前所选参数不同，进入图解后核对';
 if(r.status==='unreadable')return '导入记录无法读取，请进入图解重新导入';
 if(r.status==='same')return '本次导入数值一致，仍需回原题验收';
 return `已保存 ${r.saved} 步；缺失 ${r.missing} 步，有差异 ${r.different} 步，无法比较 ${r.unknown} 步`;
}
export function StudyDesk({open,notify}:{open:(id:string,tab?:string)=>void;notify:(text:string)=>void}){
 const [data,setData]=useState<Data|null>(null),[error,setError]=useState(''),[busy,setBusy]=useState(false),[exporting,setExporting]=useState(false);
 const [filter,setFilter]=useMemory('desk.filter','continue'),[query,setQuery]=useMemory('desk.query','');
 const [editing,setEditing]=useState<Row|null>(null);
 const savePlan=async(id:string,plan:Plan)=>{const saved=await send<{plan:Plan}>('/study-plan/'+id,plan);setData(current=>current?{...current,rows:current.rows.map(r=>r.id===id?{...r,plan:saved.plan}:r)}:current);notify(saved.plan.status==='none'?'已清除本题学习安排':'学习安排已保存');};
 const alive=useRef(true),request=useRef(0);
 const load=async()=>{const id=++request.current;setBusy(true);setError('');try{const next=await api<Data>('/study-desk');if(alive.current&&id===request.current)setData(next);}catch(e){if(alive.current&&id===request.current)setError((e as Error).message);}finally{if(alive.current&&id===request.current)setBusy(false);}};
 useEffect(()=>{alive.current=true;void load();return()=>{alive.current=false;};},[]);
 const selected=filters.some(f=>f[0]===filter)?filter:'continue',needle=query.trim().toLowerCase();
 const rows=(data?.rows||[]).filter(r=>selected==='all'||selected===r.plan.status||selected==='continue'&&r.started&&(!r.verified||r.attention)||selected==='attention'&&r.attention||selected==='notes'&&r.notes.length>0||selected==='verify'&&!r.verified)
  .filter(r=>[r.id,r.title,r.step_title,r.plan.note,...r.notes.map(n=>n.text)].join(' ').toLowerCase().includes(needle));
 return <section className="panel study-desk" aria-label="我的学习台">
  <div className="section-heading"><div><h2>我的学习台</h2><p>集中找回图解位置、观察笔记和待检查的结果。</p></div><button className="secondary" disabled={busy||!!editing} onClick={()=>void load()}>{busy?'读取中…':'刷新学习台'}</button></div>
  {error&&<div className="error-box" role="alert">{error}。{data?'下方保留上次读取的记录，可能不是最新状态。':'暂时无法读取学习记录。'}<button className="text-button" disabled={busy||!!editing} onClick={()=>void load()}>重试读取学习台</button></div>}
  {!data&&!error&&<p role="status">正在整理已有学习记录…</p>}
  {data&&<><p className="desk-counts" aria-label="学习台统计">{data.counts.started}/{data.counts.total} 题有图解记录 · {data.counts.notes} 条观察笔记 · {data.counts.attention} 题结果或版本待检查 · {data.counts.verified} 题当前代码已验收</p>
   <p className="small" aria-label="个人学习安排统计">下一步学 {data.rows.filter(r=>r.plan.status==='next').length} 题 · 暂时卡住 {data.rows.filter(r=>r.plan.status==='stuck').length} 题 · 待复习 {data.rows.filter(r=>r.plan.status==='review').length} 题。个人安排与正式成绩独立。</p>
   <details><summary>展开学习清单与笔记检索</summary>
    <div className="desk-toolbar"><label>查找题目或笔记<input aria-label="搜索学习台" placeholder="题号、标题、观察笔记或卡点" value={query} onChange={e=>setQuery(e.target.value)}/></label><label>查看范围<select aria-label="学习台筛选" value={selected} onChange={e=>setFilter(e.target.value)}>{filters.map(([id,label])=><option key={id} value={id}>{label}</option>)}</select></label></div>
    <p className="small muted">找到 {rows.length} 题。“继续学习”显示已有图解记录且尚未验收或仍需检查的题；正式验收不受自查勾选影响。</p>
    {!rows.length&&<p className="note-box">没有符合条件的记录。可以切换“全部基础题”，或清空搜索开始一题。</p>}
    <div className="desk-list">{rows.map(r=><article key={r.id} aria-label={'学习记录 '+r.id}>
     <h3>{r.id} · {r.title}</h3>{r.plan.status!=='none'&&<div className="desk-plan"><b>我的安排：{planLabels[r.plan.status]}</b>{r.plan.note&&<p>{r.plan.note}</p>}</div>}<p>图解自查 {r.done}/{r.total} 步 · {r.verified?'当前代码已验收':'当前代码待验收'}</p>
     <p className="small">保存位置：第 {r.step+1} 步 · {r.step_title} · 参数 {r.parameter}</p>
     {r.changed&&<p className="note-box">课程已更新，旧版自查不计入当前进度。</p>}
     <p className={r.attention?'note-box':'small muted'}>{resultText(r.result)}</p>
     <div className="actions"><button className="primary" onClick={()=>open(r.id,'逐步图解')}>{r.started?'继续图解':'开始图解'} · {r.id}</button><button className="secondary" onClick={()=>open(r.id,'任务')}>回原题练习 · {r.id}</button></div>
     <button className="text-button" disabled={busy} onClick={()=>setEditing(r)}>安排学习 · {r.id}</button>
     {r.notes.length>0&&<details className="desk-notes"><summary>查看观察笔记（{r.notes.length}）</summary>{r.notes.map(n=><div key={n.step}><b>第 {n.step+1} 步 · {n.title}</b><p>{n.text}</p></div>)}</details>}
    </article>)}</div>
   </details>
   <div className="actions"><button className="secondary" disabled={exporting} onClick={()=>{setExporting(true);void download('/study-desk/export','vision-study-notes.md').catch(e=>notify(e.message)).finally(()=>{if(alive.current)setExporting(false);});}}>{exporting?'正在导出…':'导出全部图解笔记'}</button></div>
   <p className="small muted">安排需点击保存，不自动勾选或授予成绩。笔记导出为 Markdown，包含全部已记录或已安排题目，不受当前筛选影响；完整备份请到“记录与设置”。</p>
  </>}
  {editing&&<StudyPlanEditor key={editing.id} id={editing.id} initial={editing.plan} save={plan=>savePlan(editing.id,plan)} close={()=>setEditing(null)}/>}
 </section>;
}
