import {useEffect,useRef,useState} from 'react';
import {api,send,download,when} from './api';
import {ide,isIDE} from './ide';

export const visualLessons=['T01','T02','T03','T04','T05','T06','V03','V04'];
type Frame={output:string;shape:number[];dtype:string;minimum:number;maximum:number;nonzero:number;display_note:string;detail:string;comparison?:string};
type Progress={revision:string;step:number;mode:'guided'|'write';notes:Record<string,string>;done:number[];parameter:number};
type Own={revision:string;parameter:number;stamp:number;stale:boolean;results:Record<string,Frame>};
type Demo={scene:string;target:string;boundary:string;revision:string;parameter:number;input:Frame;results:Record<string,Frame>;control:{name:string;label:string;values:number[];default:number;experiment:string};steps:{id:string;title:string;code:string;value:string;why:string;watch:string;failure:string;question:string;answer:string;lines:string[];before:string}[]};
type Payload={demo:Demo;progress:Progress;own:Own|null};

function Images({left,right,leftLabel,rightLabel}:{left?:Frame;right?:Frame;leftLabel:string;rightLabel:string}){
 const [zoom,setZoom]=useState(1),[single,setSingle]=useState(false),[after,setAfter]=useState(true);
 const panes=useRef<(HTMLDivElement|null)[]>([]);
 const sync=(index:number)=>{const a=panes.current[index],b=panes.current[1-index];if(a&&b&&left&&right&&left.shape[0]===right.shape[0]&&left.shape[1]===right.shape[1]){b.scrollTop=a.scrollTop;b.scrollLeft=a.scrollLeft;}};
 const frame=(f:Frame|undefined,label:string,index:number)=><figure key={label} className="walk-frame"><figcaption>{label}</figcaption><div className="walk-viewport" ref={el=>{panes.current[index]=el;}} onScroll={()=>sync(index)} tabIndex={0} aria-label={label+'图像区域'}>{f?<img src={f.output} alt={label} style={{width:zoom*100+'%'}}/>:<p>尚未运行 / 尚未保存本步结果</p>}</div>{f&&<><p className="small mono">shape={f.shape.join('×')} · {f.dtype} · 原值 [{f.minimum.toFixed(2)}, {f.maximum.toFixed(2)}]</p><p className="small muted">{f.display_note}</p>{f.detail&&<p>{f.detail}</p>}{f.comparison&&<p className="note-box">{f.comparison}</p>}</>}</figure>;
 return <div className="walk-images"><div className="actions"><label>放大 <select aria-label="步骤图像缩放" value={zoom} onChange={e=>setZoom(Number(e.target.value))}>{[1,2,4].map(v=><option key={v} value={v}>{v} 倍</option>)}</select></label><button className="secondary" onClick={()=>setSingle(!single)}>{single?'并排对照':'单图前后切换'}</button>{single&&<button className="secondary" onClick={()=>setAfter(!after)}>{after?'查看处理前':'查看处理后'}</button>}</div><p className="small muted">相同尺寸的并排图同步滚动；裁剪后的图尺寸不同，请按 ROI 坐标对照。</p><div className={single?'walk-pair single':'walk-pair'}>{single?frame(after?right:left,after?rightLabel:leftLabel,after?1:0):<>{frame(left,leftLabel,0)}{frame(right,rightLabel,1)}</>}</div></div>;
}

export function Walkthrough({lessonId,open,independent,notify,onPending}:{lessonId:string;open:(id:string)=>void;independent:()=>void;notify:(s:string)=>void;onPending:(p:Promise<unknown>|null)=>void}){
 const [baseline,setBaseline]=useState<Demo|null>(null);
 const [payload,setPayload]=useState<Payload|null>(null),[error,setError]=useState(''),[busy,setBusy]=useState(false),[saveStatus,setSaveStatus]=useState('');
 const row=useRef<Progress|null>(null),queue=useRef<Promise<unknown>>(Promise.resolve()),alive=useRef(true);
 const route='/lesson/'+lessonId+'/walkthrough';
 useEffect(()=>{alive.current=true;let cancelled=false;if(visualLessons.includes(lessonId))api<Payload>(route).then(p=>{if(!cancelled){row.current=p.progress;setPayload(p);}}).catch(e=>{if(!cancelled)setError(e.message);});return()=>{cancelled=true;alive.current=false;};},[lessonId]);
 const save=(next:Progress)=>{
  row.current=next;setPayload(p=>p?{...p,progress:next}:p);setSaveStatus('保存中…');
  const task=queue.current.catch(()=>{}).then(()=>send(route+'/progress',next));queue.current=task;onPending(task);
  void task.then(()=>{if(alive.current&&queue.current===task)setSaveStatus('观察与位置已保存');},e=>{if(alive.current&&queue.current===task)setSaveStatus('保存失败：'+e.message);}).finally(()=>{if(queue.current===task)onPending(null);});
 };
 if(!visualLessons.includes(lessonId))return <div className="note-box"><p>本题暂未提供逐步图解。第一批覆盖以下 8 题，可先学习对应的观察方法；本题仍可使用“函数与场景”和原有验收。</p><div className="actions">{visualLessons.map(id=><button key={id} className="secondary" onClick={()=>open(id)}>{id}</button>)}</div></div>;
 if(!payload)return <p role="status">{error||'正在生成本题的真实处理结果…'}</p>;
 const {demo,progress,own}=payload;const index=Math.min(progress.step,demo.steps.length-1),s=demo.steps[index];
 const before=s.before==='input'?demo.input:demo.results[s.before];
 const matching=own&&!own.stale&&own.parameter===demo.parameter;
 const experiment=async(value:number)=>{setBusy(true);setError('');try{const next=await send<Demo>(route+'/demo',{parameter:value});setPayload(p=>p?{...p,demo:next}:p);save({...row.current!,parameter:value});}catch(e){setError((e as Error).message);}finally{setBusy(false);}};
 const action=async(fn:()=>Promise<unknown>)=>{setBusy(true);setError('');try{await fn();}catch(e){setError((e as Error).message);}finally{setBusy(false);}};
 const upload=async(file:File)=>{if(file.size>12*1024*1024)throw new Error('结果包不能超过 12 MB');const body=new FormData();body.append('file',file);const result=await api<Own>(route+'/import',{method:'POST',body});setPayload(p=>p?{...p,own:result}:p);notify('已导入实际保存的步骤；这不计基础题通关');};
 return <section className="walkthrough" aria-label="逐步图解学习">
  <div className="walk-intro"><h3>先看懂这道题</h3><p><b>使用场景：</b>{demo.scene}</p><p><b>最终交付：</b>{demo.target}</p><p><b>适用边界：</b>{demo.boundary}</p></div>
  <div className="actions"><button className={progress.mode==='guided'?'primary':'secondary'} disabled={busy} onClick={()=>save({...row.current!,mode:'guided'})}>跟着理解</button><button className={progress.mode==='write'?'primary':'secondary'} disabled={busy} onClick={()=>save({...row.current!,mode:'write'})}>分步手敲</button><button className="secondary" onClick={independent}>独立挑战：回到原题</button></div>
  <p className="small muted">{progress.mode==='guided'?'先预测每一步的变化，再看真实演示和解释。':'先尝试写出本步；参考代码折叠展示，完成后导入自己的中间结果。'} 学习标记由你自评，与代码验收分开。</p>
  <nav className="walk-steps" aria-label="图解步骤">{demo.steps.map((step,i)=><button key={step.id} disabled={busy} className={i===index?'selected':''} aria-current={i===index?'step':undefined} onClick={()=>save({...row.current!,step:i})}>{progress.done.includes(i)?'✓ ':''}{i+1}. {step.title}</button>)}</nav>
  <article className="walk-step"><h3>{index+1}. {s.title}</h3><p><b>为什么做：</b>{s.why}</p><p className="note-box"><b>重点观察：</b>{s.watch}</p>
   <Images key={s.id+'-'+demo.parameter} left={before} right={demo.results[s.id]} leftLabel={s.before==='input'?'教学输入：原始图像':'教学输入：'+demo.steps.find(v=>v.id===s.before)?.title} rightLabel={'教学演示：'+s.title}/>
   <details key={s.id+'-'+progress.mode} open={progress.mode==='guided'} className="walk-code"><summary>本步代码与逐行解释</summary><pre className="reference-code">{s.code}</pre><ol>{s.lines.map(line=><li key={line}>{line}</li>)}</ol><p className="small">教学演示使用固定样例与下方显示的参数，不代表你的代码执行结果。</p></details>
   <p><b>不符合预期时：</b>{s.failure}</p><p><b>先预测 / 解释：</b>{s.question}</p><details key={s.id+'-answer'}><summary>想过之后查看解释</summary><p>{s.answer}</p></details>
  </article>
  <fieldset className="walk-experiment" disabled={busy}><legend>只改一个参数，重新观察</legend><label>{demo.control.label}<select aria-label="图解实验参数" value={demo.parameter} onChange={e=>void experiment(Number(e.target.value))}>{demo.control.values.map(v=><option key={v} value={v}>{v}</option>)}</select></label><p>{demo.control.experiment}</p><p className="small muted">固定同一份 seed 17 输入，真实运行 OpenCV；参数实验不修改原题代码。</p></fieldset>
  <div><button className="secondary" disabled={busy} onClick={()=>void action(async()=>{if(baseline)setBaseline(null);else setBaseline(await send<Demo>(route+'/demo',{parameter:demo.control.default}));})}>{baseline?'收起参数对照':'与默认参数对照'}</button>{baseline&&<><p>保持同一输入，对比默认参数 {baseline.parameter} 与当前参数 {demo.parameter} 的同一步结果。预览缩放规则见图下注释。</p><Images key={'parameter-'+s.id+'-'+demo.parameter} left={baseline.results[s.id]} right={demo.results[s.id]} leftLabel={'默认参数 '+baseline.parameter} rightLabel={'当前参数 '+demo.parameter}/></>}</div>
  <div className="walk-own"><h3>手敲并查看自己的中间结果</h3><p>每个实验包含相同输入、参数、practice.py 手敲文件及可选参考代码。按说明保存步骤，运行后生成 results.zip。</p><div className="actions">
   {isIDE&&<><button className="secondary" disabled={busy} onClick={()=>void action(()=>ide('openWalkthrough',{key:lessonId,parameter:demo.parameter}))}>在 VS Code 打开分步代码</button><button className="secondary" disabled={busy} onClick={()=>void action(()=>ide('runWalkthrough',{key:lessonId,parameter:demo.parameter}))}>运行我的分步代码</button><button className="secondary" disabled={busy} onClick={()=>void action(async()=>{const own=await ide<Own>('readWalkthrough',{key:lessonId,parameter:demo.parameter});setPayload(p=>p?{...p,own}:p);})}>读取我的步骤结果</button></>}
   <button className="secondary" disabled={busy} onClick={()=>void action(()=>download(route+'/export/'+demo.parameter,lessonId+'-steps-'+demo.parameter+'.zip'))}>下载手敲实验包</button>
   <label className="walk-upload">导入 results.zip<input aria-label="导入步骤结果" type="file" accept=".zip" disabled={busy} onChange={e=>{const f=e.target.files?.[0];e.target.value='';if(f)void action(()=>upload(f));}}/></label>
  </div><p className="small muted">每次运行从头生成结果包；只导入本次保存的数据。参考脚本的结果也会显示为“导入结果”，平台不能据此判断是否独立完成。个人代码请另行备份。</p>
  {!own?<p>还没有导入结果。教学图不会填充到你的结果栏。</p>:<><p>导入记录：{when(own.stamp)} · 参数 {own.parameter} · 已保存 {Object.keys(own.results).length}/{demo.steps.length} 步</p>{own.stale?<p className="note-box">课程已更新，请重新生成实验包；旧结果不与当前演示对照。</p>:!matching?<div className="note-box">导入结果参数与当前演示不同。<button className="text-button" disabled={busy} onClick={()=>void experiment(own.parameter)}>切换到导入结果的参数</button></div>:<Images key={'own-'+s.id+'-'+own.stamp} left={demo.results[s.id]} right={own.results[s.id]} leftLabel="教学参考（同一步）" rightLabel="你的导入结果（来源为本地文件）"/>}</>}
  </div>
  <label className="walk-notes">记录预测、实测和适用条件<textarea aria-label="本步观察笔记" maxLength={4000} value={progress.notes[s.id]||''} onChange={e=>save({...row.current!,notes:{...row.current!.notes,[s.id]:e.target.value}})} placeholder="我预测…；实际看到…；如果换成…场景，这个方法可能…"/></label>
  <div className="actions"><button className="secondary" onClick={()=>save({...row.current!,done:progress.done.includes(index)?progress.done.filter(v=>v!==index):[...progress.done,index]})}>{progress.done.includes(index)?'取消本步理解标记':'我能解释这一步'}</button><button className="secondary" disabled={index===0||busy} onClick={()=>save({...row.current!,step:index-1})}>上一步</button><button className="primary" disabled={index===demo.steps.length-1||busy} onClick={()=>save({...row.current!,step:index+1})}>下一步</button><span role="status">{saveStatus}</span>{saveStatus.startsWith('保存失败')&&<button onClick={()=>save(row.current!)}>重试保存</button>}</div>
  {error&&<p className="error-box" role="alert">{error}</p>}
 </section>;
}
