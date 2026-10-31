import {useState} from 'react';
import type {Boot,Lesson} from './api';
import {firstRound,terms,troubleshooting} from './beginner-data';
import './beginner.css';

export function BeginnerStart({boot,open}:{boot:Boot;open:(id:string)=>void}){
 const path=firstRound.filter(item=>boot.lessons.some(l=>l.id===item.id));
 const next=path.find(item=>!boot.passed[item.id]);
 return <section className="panel beginner-start" aria-label="新手第一轮学习"><div className="section-heading"><div><h2>第一次学视觉，先完成这一小段</h2><p>一次选一题：先看懂输入输出，再手敲一小步，最后验收。</p></div><b>{path.filter(item=>boot.passed[item.id]).length}/{path.length} 已验收</b></div>
 {next?<p className="note-box">建议从 <b>{next.id} · {next.title}</b> 继续。{next.outcome}<button className="text-button" onClick={()=>open(next.id)}>打开推荐题 {next.id}</button></p>:<p className="note-box">首轮八题当前代码均已验收。可以复盘下面任一题，再到完整路线选择算法或工程。</p>}
 <details><summary>查看首轮顺序与每题目标</summary><ol className="beginner-path">{path.map(item=><li key={item.id}><button className="text-button" onClick={()=>open(item.id)}>{item.id} · {item.title}</button><span>{item.outcome}</span><small>{boot.passed[item.id]?'当前代码已验收':'尚未验收'}</small></li>)}</ol></details><p className="small muted">按当前代码的验收记录推荐，不把阅读或自评当成通关；也可以自由选择题目。</p></section>;
}

export function BeginnerCard({lesson}:{lesson:Lesson}){
 const card=firstRound.find(item=>item.id===lesson.id);
 if(!card)return null;
 return <section className="beginner-card" aria-label="本题起步卡"><h3>这题先弄清三件事</h3><dl><div><dt>拿到什么</dt><dd>{card.input}</dd></div><div><dt>交出什么</dt><dd>{card.output}</dd></div><div><dt>先试哪一步</dt><dd>{card.first}</dd></div></dl><p><b>自查重点：</b>{card.check}</p></section>;
}

export function BeginnerHelp({lessonId,available,openTab}:{lessonId:string;available:boolean;openTab:(tab:string)=>void}){
 const [query,setQuery]=useState(''),[symptom,setSymptom]=useState('start');
 const recommended=firstRound.find(item=>item.id===lessonId)?.terms as readonly string[]|undefined;
 const needle=query.trim().toLowerCase();
 const visible=terms.filter(term=>!needle||[term.id,term.name,term.meaning,term.example,term.pitfall].join(' ').toLowerCase().includes(needle));
 const chosen=troubleshooting.find(item=>item.id===symptom)||troubleshooting[0];
 const target=chosen.tab==='逐步图解'&&!available?'知识与提示':chosen.tab;
 return <div className="beginner-help"><details><summary>术语看不懂？用小例子查一查</summary><label className="field-label">搜索术语<input aria-label="搜索新手术语" placeholder="例如 shape、ROI、return、掩膜" value={query} onChange={e=>setQuery(e.target.value)}/></label>{recommended&&<p className="small">本题先看：{recommended.map(id=>terms.find(t=>t.id===id)?.name).join('；')}。</p>}
 <div className="beginner-terms">{visible.map(term=><article key={term.id}><h4>{term.name}</h4><p>{term.meaning}</p><p className="beginner-example">{term.example}</p><p className="small"><b>容易弄错：</b>{term.pitfall}</p></article>)}</div>{!visible.length&&<p>没有找到这个词。试试更短的中文或函数名，例如“掩膜”或“shape”。</p>}</details>
 <details><summary>卡住了？按现象找到下一步</summary><label>我遇到的情况<select aria-label="新手排查现象" value={symptom} onChange={e=>setSymptom(e.target.value)}>{troubleshooting.map(item=><option value={item.id} key={item.id}>{item.name}</option>)}</select></label><ol>{chosen.steps.map(line=><li key={line}>{line}</li>)}</ol><p className="small muted">这是排查顺序，具体原因仍需结合本次报错和数组结果确认。</p><button className="secondary" onClick={()=>openTab(target)}>{target===chosen.tab?chosen.action:'查看本题提示'}</button></details></div>;
}
