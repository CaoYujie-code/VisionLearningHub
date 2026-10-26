import {Tag} from './ui';

export type GuideBlock={id:string;title:string;purpose:string;command:string;contract:string;hints:string[];lesson:string;resource:string};
export type Guide={version:number;starter:string;blocks:GuideBlock[]};
export type BlockProgress=Record<string,{state:'passed'|'failed'|'stale';stamp:number}>;
export type GuideNotes={mode:'guided'|'independent';block:string;source:'own'|'standard';hints:Record<string,number>};
type Props={guide:Guide;notes:GuideNotes;progress:BlockProgress;hasCheckpoint:boolean;busy:boolean;
 change:(patch:Partial<GuideNotes>)=>void;run:(block:string,source:string)=>void;initialize:()=>void;code:()=>void;open:(lesson:string)=>void};

export function ProjectGuide({guide,notes,progress,hasCheckpoint,busy,change,run,initialize,code,open}:Props){
 const block=guide.blocks.find(b=>b.id===notes.block)||guide.blocks[0];
 const source=block.id==='render'?notes.source:'own';
 const level=notes.hints[block.id]||0;
 const status=(id:string,input:string)=>{
  const state=progress[id+':'+input]?.state;
  return state==='passed'?'当前源码通过':state==='failed'?'需要修改':state==='stale'?'源码已变，需重验':'尚未检查';
 };
 return <section className="panel guided-panel" aria-label="分块学习面板">
  <div className="title-row"><h2>分块学习</h2><span className="small muted">5 个任务块 · 可自由切换 · 检查只读取当前源码</span></div>
  <div className="guided-layout"><nav aria-label="工程任务块" className="guided-blocks">
   {guide.blocks.map((item,i)=><button key={item.id} className={item.id===block.id?'selected':''} onClick={()=>change({block:item.id})}>
    <b>{i+1}. {item.title}</b><span>{status(item.id,item.id==='render'?notes.source:'own')}</span>
   </button>)}
  </nav><article className="guided-detail">
   <div className="title-row"><h3>{block.title}</h3><Tag tone={progress[block.id+':'+source]?.state==='passed'?'green':''}>{status(block.id,source)}</Tag></div>
   <p>{block.purpose}</p><h4>这一块交付什么</h4><p>{block.contract}</p>
   <div className="actions"><button className="text-button" onClick={()=>open(block.lesson)}>复习前置题 {block.lesson}</button><a href={block.resource} target="_blank" rel="noreferrer">查阅官方资料 ↗</a></div>
   {block.id==='render'&&<div className="guide-source"><label>绘图输入 <select aria-label="任务块输入来源" value={notes.source} onChange={e=>change({source:e.target.value as 'own'|'standard'})}><option value="standard">标准检测结果：单独学习绘图</option><option value="own">自己的检测结果：检查模块衔接</option></select></label><p className="small muted">标准结果由教学基线生成，明确记录为辅助练习；自己的输入会先检查检测块。两者均不代表完整工程通过。</p></div>}
   {!hasCheckpoint&&<div className="note-box">此工程还没有分块入口。添加只会创建 checkpoint.py，保留已有模块。也可切换独立挑战直接运行 main.py。<button className="secondary" disabled={busy} onClick={initialize}>添加分块入口</button></div>}
   <pre className="light-code">python {block.command} --input data/sample --output step-output --config config.json</pre>
   {block.id==='render'&&<p className="small muted">在终端运行时，输入目录须包含 _detections.json。导出工程的 data/standard 可用于标准输入；平台按钮会自动准备本次选择的输入。</p>}
   <div className="actions"><button className="secondary" onClick={code}>打开本块代码</button><button className="primary" disabled={busy||(!hasCheckpoint&&!['batch','accept'].includes(block.id))} onClick={()=>run(block.id,source)}>{block.id==='accept'?'运行完整工程验收':'检查当前任务块'}</button></div>
   <div className="guide-hints"><button className="text-button" onClick={()=>change({hints:{...notes.hints,[block.id]:level>=block.hints.length?0:level+1}})}>{level>=block.hints.length?'收起提示':'展开下一层提示'}</button>{block.hints.slice(0,level).map((hint,i)=><p className="note-box" key={i}><b>提示 {i+1}：</b>{hint}</p>)}</div>
   <p className="small muted">只实现当前分支即可。函数名与模块划分由你决定；checkpoint.py 是可编辑的普通命令行入口。读写/检测/绘图检查2批输入，批处理检查开发样例，完整验收检查5批。</p>
  </article></div>
 </section>;
}
