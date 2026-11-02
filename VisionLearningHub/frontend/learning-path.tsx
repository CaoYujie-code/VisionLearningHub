import type {Boot} from './api';
import {useMemory} from './navigation';
import {learningPaths} from './continuation-data';
import './beginner.css';

export function LearningPath({boot,open,current}:{boot:Boot;open:(id:string)=>void;current?:string}){
 const [selected,setSelected]=useMemory('beginner.path','detector');
 const path=learningPaths.find(p=>p.id===selected)||learningPaths[0];
 const steps=path.steps.filter(s=>boot.lessons.some(l=>l.id===s.id));
 const next=steps.find(s=>!boot.passed[s.id]);
 const ready=path.prepare.filter(id=>!boot.passed[id]);
 const position=steps.findIndex(s=>s.id===current);
 const label=(id:string)=>id+' · '+(boot.lessons.find(l=>l.id===id)?.title||'练习');
 return <section className="panel learning-path" aria-label="目标学习路线">
  <h2>{current?'沿目标路线继续':'首轮之后，选一个想完成的目标'}</h2>
  <label>我的学习目标<select aria-label="选择目标路线" value={path.id} onChange={e=>setSelected(e.target.value)}>{learningPaths.map(p=><option key={p.id} value={p.id}>{p.title}</option>)}</select></label>
  <p>{path.goal}</p><p className="small muted">{path.boundary}</p>
  {ready.length>0&&<details className="path-preparation"><summary>建议先复习的基础（{ready.length} 项未验收）</summary><p className="small">可以直接尝试路线；遇到输入或数组问题时再回来补齐。</p><div className="actions">{ready.map(id=><button key={id} className="text-button" onClick={()=>open(id)}>{label(id)}</button>)}</div></details>}
  <p aria-label="目标路线进度">{steps.filter(s=>boot.passed[s.id]).length}/{steps.length} 当前代码已验收</p>
  {next?<button className="primary" onClick={()=>open(next.id)}>继续路线：{label(next.id)}</button>:<p className="note-box">本路线当前代码均已验收。可以回看任一环节，或切换目标继续学习。</p>}
  {current&&(position>=0?<nav className="actions path-neighbors" aria-label="路线前后题"><span className="small">当前为第 {position+1}/{steps.length} 步</span>{position>0&&<button className="secondary" onClick={()=>open(steps[position-1].id)}>上一题：{steps[position-1].id}</button>}{position<steps.length-1&&<button className="secondary" onClick={()=>open(steps[position+1].id)}>下一题：{steps[position+1].id}</button>}</nav>:<p className="small muted">当前题 {current} 不在所选路线中；可以切换目标或回看路线中的任一题。</p>)}
  <details><summary>展开路线步骤与学习目的</summary><ol className="beginner-path">{steps.map(s=><li key={s.id} aria-current={s.id===current?'step':undefined}><button className="text-button" onClick={()=>open(s.id)}>{label(s.id)}</button><span>{s.why}</span><small>{s.id===current?'当前题 · ':''}{boot.passed[s.id]?'当前代码已验收':'尚未验收'}</small></li>)}</ol></details>
  <p className="small muted">目标选择会记住。路线进度共用已有验收记录；自由跳题不计通关，修改代码后需重新验收。</p>
 </section>;
}
