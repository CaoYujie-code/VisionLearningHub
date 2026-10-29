import {useEffect,useState} from 'react';
import {useMemory} from './navigation';
import {Boot,Lesson,FunctionCard,download,api,send} from './api';
import {FunctionReview,ReviewState} from './function-review';
import {isIDE,ide} from './ide';

export function FunctionGuideView({lesson,boot,open,notes,notify,onPending}:{lesson:Lesson;boot:Boot;open:(id:string)=>void;notes:()=>void;notify:(message:string)=>void;onPending:(task:Promise<unknown>|null)=>void}){
 const [query,setQuery]=useMemory(lesson.id+'.functions.query','');
 const [scope,setScope]=useMemory(lesson.id+'.functions.scope','current');
 const [selected,setSelected]=useMemory(lesson.id+'.functions.card','');
 const [busy,setBusy]=useState(false);
 const [review,setReview]=useState<ReviewState|null>(null),[reviewError,setReviewError]=useState(''),[saving,setSaving]=useState(false);
 useEffect(()=>{let alive=true;api<ReviewState>('/function-review').then(r=>{if(alive)setReview(r);}).catch(e=>{if(alive)setReviewError(e.message);});return()=>{alive=false;};},[]);
 const reloadReview=()=>{setReviewError('');void api<ReviewState>('/function-review').then(setReview).catch(e=>setReviewError(e.message));};
 const guide=lesson.function_guide;
 if(!guide)return <p>此题的函数讲解尚未提供。</p>;
 const all=Array.from(new Map(boot.lessons.flatMap(l=>l.function_guide?.cards||[]).map(c=>[c.id,c])).values());
 const candidates=(scope==='current'?guide.cards:all).filter(c=>scope!=='review'||Boolean(review?.records[c.id]&&!review.records[c.id].correct));
 const cards=candidates.filter(c=>(c.name+' '+c.signature+' '+c.use+' '+c.parameters.map(p=>p.name).join(' ')).toLowerCase().includes(query.trim().toLowerCase()));
 const card:FunctionCard|undefined=cards.find(c=>c.id===selected)||cards[0];
 const related=card?boot.lessons.filter(l=>l.function_guide?.cards.some(c=>c.id===card.id)):[];
 const owner=related.some(l=>l.id===lesson.id)?lesson.id:related[0]?.id;
 const submitReview=async(choice:number)=>{if(!card)return;setSelected(card.id);setSaving(true);setReviewError('');try{const task=send<ReviewState>('/function-review',{card:card.id,choice,revision:card.quiz.revision});onPending(task);const result=await task;setReview(result);if(scope==='review'&&result.records[card.id].correct){setScope('all');notify('已移出待巩固，切换到全部函数保留本题解析');}}catch(e){setReviewError((e as Error).message);throw e;}finally{setSaving(false);onPending(null);}};
 const exportExamples=async()=>{setBusy(true);try{await download('/lesson/'+lesson.id+'/examples',lesson.id+'-function-examples.zip');}catch(e){notify((e as Error).message);}finally{setBusy(false);}};
 return <section className="function-guide" aria-label="函数与场景学习">
  <div className="note-box"><b>本题如何选择方法</b><p>{guide.decision}</p><p className="small">先预测 → 独立文件手敲 → 运行断言 → 改一个参数 → 回到题目验收。示例使用自带小输入，不替换你的解题代码，也不计通关。</p></div>
  <details className="function-primer"><summary>第一次看函数调用：函数名、参数、返回值是什么？</summary><p>import cv2 导入 OpenCV；import numpy as np 给 NumPy 起别名 np。cv2.threshold 中点号表示访问库里的函数，括号内是传给它的实际数据和参数。</p><pre className="light-code">used, mask = cv2.threshold(gray, 100, 255, cv2.THRESH_BINARY)</pre><p>这里 gray 是输入数组，100 是阈值，255 是选中像素的输出值，最后一个常量选择处理方式。函数返回两个值，左侧分别接到 used 和 mask；写 _, mask 表示本次不使用第一个值。return 把结果交给调用者，print 只显示日志。</p><p>shape 是数组属性（不加括号），copy() 是方法（加括号）。H/W 分别是高/宽；uint8 是 0～255 的8位无符号整数；float32 是浮点数。像素数组 image[y,x] 先行后列，OpenCV点坐标 (x,y) 先横后纵。</p></details>
  <div className="function-toolbar"><label>查阅范围 <select aria-label="函数查阅范围" value={scope} onChange={e=>{setScope(e.target.value);setSelected('');}}><option value="current">本题相关函数</option><option value="all">全部函数与算法组件</option><option value="review">待巩固的函数</option></select></label><input aria-label="搜索函数或场景" placeholder="例如 threshold、椒盐、dtype…" value={query} onChange={e=>setQuery(e.target.value)}/><span className="small muted">{cards.length} 组讲解</span></div>
  {review&&<p className="small muted" aria-label="函数理解记录">已判断 {review.answered}/{review.total} 组 · 当前答对 {review.correct} 组 · 待巩固 {review.review} 组（与代码验收分开）</p>}
  {reviewError&&<div className="error-box" role="alert">自测记录尚未保存或读取失败：{reviewError}<button className="text-button" onClick={reloadReview}>重新读取记录</button></div>}
  <div className="function-nav" role="navigation" aria-label="函数讲解列表">{cards.map(c=><button key={c.id} className={c.id===card?.id?'selected':''} aria-pressed={c.id===card?.id} onClick={()=>setSelected(c.id)}>{c.name}</button>)}</div>
  {card?<article key={card.id} className="function-card"><h3>{card.name}</h3><pre className="light-code">{card.signature}</pre>
   <div className="function-table"><table><caption>关键参数怎么选</caption><thead><tr><th>参数</th><th>含义</th><th>选择与限制</th></tr></thead><tbody>{card.parameters.map(p=><tr key={p.name}><th scope="row">{p.name}</th><td>{p.meaning}</td><td>{p.choice}</td></tr>)}</tbody></table></div>
   <p><b>返回值怎么看：</b>{card.returns}</p><div className="function-scenarios"><div><h4>适合什么场景</h4><p>{card.use}</p></div><div><h4>什么时候要换方法</h4><p>{card.avoid}</p></div></div><p className="note-box"><b>常见错误：</b>{card.pitfall}</p>
   <h4>可独立运行的最小例子</h4><p className="small muted">先手敲到单独的 .py 文件，使用现有 OpenCV / NumPy 解释器运行。示例不是 solve(image, params) 的完整答案。</p><pre className="reference-code" tabIndex={0} aria-label="函数最小示例">{card.example}</pre>
   <p><b>预期结果：</b>{card.expect}</p><p><b>动手改一处：</b>{card.experiment}</p>
   <div className="actions">{isIDE&&<button className="secondary" onClick={()=>ide('openFunctionExample',{key:owner,id:card.id}).catch(e=>notify(e.message))}>在 VS Code 打开独立示例</button>}<a href={card.docs} target="_blank" rel="noreferrer">查阅本函数官方资料 ↗</a></div>
   <FunctionReview key={card.id} card={card} record={review?.records[card.id]} ready={Boolean(review)} busy={saving} submit={submitReview}/>
   <div className="dependency-row"><span>用到它的练习</span>{related.map(l=><button key={l.id} disabled={l.id===lesson.id} onClick={()=>open(l.id)}>{l.id} {l.title}</button>)}</div>
  </article>:<p role="status">{scope==='review'?(review?'目前没有匹配的待巩固项。未作答的函数请在本题或全部列表学习。':'正在读取自测记录…'):'没有匹配内容。可清空搜索或切换“全部函数与算法组件”。'}</p>}
  <div className="function-review"><h4>学完这题，尝试解释</h4><p>{guide.question}</p><div className="actions"><button className="secondary" onClick={notes}>去笔记记录实验</button><button className="secondary" disabled={busy} onClick={()=>void exportExamples()}>下载当前题 {lesson.id} 的示例与讲义</button></div><p className="small muted">下载含课程原版 Python 示例与离线 README，可在 VS Code / PyCharm 使用。自己改过的独立示例请另存或用 Git 保存。讲解覆盖课程核心函数与关键参数；完整重载见官方资料。</p></div>
 </section>;
}
