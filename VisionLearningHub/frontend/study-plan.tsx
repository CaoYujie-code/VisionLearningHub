import {useEffect,useRef,useState} from 'react';
import {beforeLeave} from './navigation';
import {Modal} from './ui';
export type Plan={status:'none'|'next'|'stuck'|'review';note:string};
export const planLabels={none:'未安排',next:'下一步学',stuck:'暂时卡住',review:'待复习'};

export function StudyPlanEditor({id,initial,save,close}:{id:string;initial:Plan;save:(plan:Plan)=>Promise<void>;close:()=>void}){
 const [draft,setDraft]=useState<Plan>(initial),[busy,setBusy]=useState(false),[error,setError]=useState('');
 const dirty=draft.status!==initial.status||draft.note!==initial.note;
 const current=useRef({dirty,busy});current.current={dirty,busy};
 useEffect(()=>beforeLeave(async()=>{if(current.current.busy)throw new Error('学习安排正在保存，请稍后再离开');if(current.current.dirty)throw new Error('学习安排尚未保存，请先保存或取消修改');}),[]);
 useEffect(()=>{if(!dirty&&!busy)return;const warn=(e:BeforeUnloadEvent)=>e.preventDefault();window.addEventListener('beforeunload',warn);return()=>window.removeEventListener('beforeunload',warn);},[dirty,busy]);
 const attemptClose=()=>{if(busy)return;if(dirty){setError('安排尚未保存。请保存，或点击“取消修改”放弃本次编辑。');return;}close();};
 const submit=async(value:Plan)=>{setError('');if(value.status==='none'&&value.note!==''){setError('请先选择学习安排；清除安排请使用“清除本题安排”。');return;}setBusy(true);try{await save(value);close();}catch(e){setError((e as Error).message);}finally{setBusy(false);}};
 return <Modal title={'安排学习 · '+id} onClose={attemptClose}>
  <p>记录你想做的下一步。安排由你维护，不改变题目成绩；已验收的题也可以标记为待复习。</p>
  <label className="field-label">学习安排<select aria-label="学习安排状态" disabled={busy} value={draft.status} onChange={e=>setDraft({...draft,status:e.target.value as Plan['status']})}>{Object.entries(planLabels).map(([key,label])=><option key={key} value={key}>{label}</option>)}</select></label>
  <label className="field-label">下一步或卡点<textarea className="notes" aria-label="学习安排备注" maxLength={1000} disabled={busy} placeholder="例如：我会用 threshold，但还不知道光照不均时为什么失败。下一次先比较自适应阈值。" value={draft.note} onChange={e=>setDraft({...draft,note:e.target.value})}/></label>
  <p className="small muted">{draft.note.length}/1000 字。点击保存后写入本机，包含在完整备份与笔记导出中。</p>
  {error&&<p className="error-box" role="alert">{error}</p>}
  <div className="actions"><button className="primary" disabled={busy||!dirty} onClick={()=>void submit(draft)}>{busy?'保存中…':'保存安排'}</button><button className="secondary" disabled={busy} onClick={close}>取消修改</button>{initial.status!=='none'&&<button className="text-button" disabled={busy} onClick={()=>void submit({status:'none',note:''})}>清除本题安排</button>}</div>
  <p className="small muted">清除只移除本题安排与这条备注，代码、图解笔记和成绩继续保留。</p>
 </Modal>;
}
