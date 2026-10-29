import {useEffect,useState} from 'react';
import {FunctionCard} from './api';
export type ReviewRecord={choice:number;revision:string;attempts:number;wrong_attempts:number;stamp:number;stale:boolean;correct:boolean};
export type ReviewState={records:Record<string,ReviewRecord>;total:number;answered:number;correct:number;review:number};

export function FunctionReview({card,record,busy,ready,submit}:{card:FunctionCard;record?:ReviewRecord;busy:boolean;ready:boolean;submit:(choice:number)=>Promise<void>}){
 const [choice,setChoice]=useState<number|null>(record&&!record.stale?record.choice:null);
 const [revealed,setRevealed]=useState(Boolean(record&&!record.stale));
 useEffect(()=>{setChoice(record&&!record.stale?record.choice:null);setRevealed(Boolean(record&&!record.stale));},[card.id,record?.revision,record?.attempts]);
 const check=async()=>{if(choice===null)return;try{await submit(choice);setRevealed(true);}catch{/* parent displays a visible error; keep the unsaved choice */}};
 const quiz=card.quiz;
 return <section className="function-quiz" aria-label="函数理解自测"><h4>练一练：场景与参数判断</h4><p>{quiz.question}</p><fieldset disabled={busy||!ready}><legend>选择最符合题设的一项</legend>{quiz.options.map((option,i)=><label className="quiz-option" key={i}><input type="radio" name={'quiz-'+card.id} checked={choice===i} onChange={()=>{setChoice(i);setRevealed(false);}}/><span>{String.fromCharCode(65+i)}. {option.text}</span></label>)}</fieldset>
 <div className="actions"><button className="primary" disabled={choice===null||busy||!ready||revealed} onClick={()=>void check()}>{busy?'正在保存…':'检查选择并保存'}</button>{revealed&&<button className="secondary" disabled={busy} onClick={()=>{setChoice(null);setRevealed(false);}}>重新思考</button>}</div>
 {record?.stale&&<p className="note-box">题目已更新，旧记录保留为待巩固，请重新判断。</p>}
 {revealed&&record&&!record.stale&&<div className="quiz-feedback" role="status"><b>{record.correct?'这次判断正确':'这次需要再想一想'}</b><p>第 {record.attempts} 次提交 · 本版本曾答错 {record.wrong_attempts} 次。理解自测不会增加代码通关进度。</p><ol type="A">{quiz.options.map((option,i)=><li key={i}><b>{i===quiz.answer?'符合题设：':'不符合题设：'}</b>{option.explanation}</li>)}</ol></div>}
 <p className="small muted">记录在本机保存，同一函数在不同题目中共享。答错或题目更新会进入“待巩固”；答对后仍需手敲代码验证。</p></section>;
}
