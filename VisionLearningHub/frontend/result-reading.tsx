import type {Frame} from './walkthrough';

/** Read metadata from the actual array; never infer correctness from its picture. */
export function ResultReading({frame:f}:{frame:Frame}) {
 const count=f.shape.reduce((a,b)=>a*b,1);
 const shape=f.kind==='matrix'
  ? `${f.shape[0]} 行、${f.shape[1]} 列。行列的业务含义见本步说明和列名，不是图像宽高。`
  : f.shape.length===1
   ? `${f.shape[0]} 个元素的一维数组。下标从 0 开始，不是 ${f.shape[0]} 像素宽的照片。`
   : `${f.shape[0]} 行（高）、${f.shape[1]} 列（宽）${f.shape.length===3?`、${f.shape[2]} 个通道`:''}。访问位置用 array[行, 列]；OpenCV 的点坐标通常写 (x, y)，对应（列, 行）。`;
 const dtype=f.dtype==='uint8'
  ? '每个元素是 0～255 的整数。类型本身不说明它是灰度、颜色还是掩膜，也不代表运算时可以忽略溢出。'
  : f.dtype.startsWith('float')
   ? '浮点数，可以表示小数；不自动限定在 0～1，也可能有负值。不要为了显示而先把计算结果转成 uint8。'
   : f.dtype.startsWith('uint')
    ? '无符号整数，不能表示负数。标签编号与计数的意义由本步决定。'
    : '有符号整数，可以表示负数；例如 -1 可能是课程约定的标记，需要结合本步说明理解。';
 const reading:Record<string,string>={
  image:'按空间位置看图；三通道不自动代表 RGB，通道顺序由本步代码决定，HSV 也可以是三通道。显示转换见图下注释。',
  signed:'这是带正负号的数据。正负可表示变化方向；预览颜色用于区分符号，不是物体本身的颜色。',
  magnitude:'先看数值大小和单位。预览亮度是显示映射后的结果，不能把图上的亮度直接当成原始梯度或距离。',
  heatmap:'先读本图的最小值和最大值。各图可能独立缩放，同样的颜色未必对应相同的原始数值。',
  labels:'颜色辅助区分区域编号。编号不是类别，也不是跨帧身份；编号的最大值不能代替实际目标数。',
  histogram:'横轴是灰度级，纵轴是该灰度出现的次数。看峰的位置和分布，不能凭两张图的峰高比较次数，需核对纵轴尺度。',
  curve:'横轴是输入灰度，纵轴是输出灰度。先选一个输入值，沿曲线读输出，再判断它变亮还是变暗。',
  matrix:'按列名和原值读表。预览图中文字可能四舍五入，展开“查看原始数值表”核对；表的行数也不一定是目标数。',
 };
 const nonzero=f.kind==='histogram'?'这里统计有非零计数的灰度级数量，不是总像素数。'
  :f.kind==='labels'?'这里统计非背景元素数量，不是连通区域个数。'
  :f.shape.length===3?'三通道中每个通道分别计数，不是非黑像素数，也不是物体数。'
  :'这里只统计不等于 0 的元素，不能直接当作目标个数或正确率。';
 return <details className="walk-reading"><summary>这些数值和图像怎么看？</summary><dl>
  <dt>shape：数组怎么排</dt><dd><code>{f.shape.join(' × ')}</code>：{shape}{count===0&&' 这是空数组，不是装满 0 的数组；是否合理取决于本步任务。'}</dd>
  <dt>dtype：每个元素怎么存</dt><dd><code>{f.dtype}</code>：{dtype}</dd>
  <dt>原值范围：计算结果有多大</dt><dd>{f.minimum===null||f.maximum===null?'空数组没有最小值和最大值。':`最小值 ${String(f.minimum)}，最大值 ${String(f.maximum)}。这是原始数组的范围，不是预览图的亮度范围；范围正常也不能证明算法正确。`}</dd>
  <dt>非零元素：有多少项不为 0</dt><dd>{f.nonzero} / {count} 个元素。{nonzero}</dd>
  <dt>这类结果先看哪里</dt><dd>{reading[f.kind]||'结合本步说明、原始数值和显示转换规则阅读结果。'}</dd>
 </dl></details>;
}

type Step={id:string;title:string};
type Own={stale:boolean;parameter:number;results:Record<string,Frame>};
type Status={kind:string;label:string;help:string};
function resultStatus(frame:Frame|undefined):Status {
 if(!frame)return {kind:'missing',label:'未保存',help:'检查 practice.py 中本步的处理与保存代码，重新运行后导入最新 results.zip；也检查程序是否在本步前报错。'};
 const d=frame.difference;
 if(!d)return {kind:'unknown',label:'尚无数值比较',help:'此记录没有比较信息。重新运行并导入结果后再检查，不能据此判断一致。'};
 if(!d.available)return {kind:'incompatible',label:'暂不能比较',help:d.reason||'先核对数组尺寸、数据类型和数值范围。'};
 if(d.different>0)return {kind:'different',label:'存在数值差异',help:`${d.different} / ${d.total} 个元素超出本次容差。查看本步差异索引，再检查输入、参数和运算；差异不是错误原因的自动诊断。`};
 return {kind:'same',label:'本次样例数值一致',help:d.total===0?'双方都是相同尺寸和类型的空数组。还需要测试存在结果的输入。':'本次保存数组在比较容差内一致；仍需检查返回值和其他输入。'};
}

export function ResultChecklist({steps,own,parameter,index,busy,onSelect}:{steps:Step[];own:Own|null;parameter:number;index:number;busy:boolean;onSelect:(index:number)=>void}) {
 const blocked=own?.stale?'课程已更新，旧结果暂不比较。请重新打开实验包、运行并导入。'
  :own&&own.parameter!==parameter?`当前演示参数为 ${parameter}，导入参数为 ${own.parameter}，暂不比较。可在下方导入区切换到导入参数，或重新运行当前参数的实验包。`:'';
 const states=steps.map(step=>resultStatus(own?.results[step.id]));
 const missing=states.findIndex(s=>s.kind==='missing');
 const issue=states.findIndex(s=>['unknown','incompatible','different'].includes(s.kind));
 const same=states.filter(s=>s.kind==='same').length;
 return <section className="walk-checklist" aria-label="分步结果检查清单"><h3>我的结果：下一步检查哪里</h3>
  <p className="small muted">依据最近一次导入的数组。修改本地代码后需要重新运行并导入；这里不会自动读取未保存的代码，也不会授予通关。</p>
  {blocked?<p className="note-box" role="status">{blocked}</p>:<>
   <p>{own?`本次样例数值一致 ${same} / ${steps.length} 步；未保存 ${states.filter(s=>s.kind==='missing').length} 步。`:'还未导入自己的结果。先完成一小步，运行 practice.py，再导入 results.zip。教学演示不会替你填写清单。'}</p>
   {own&&<div className="actions">{missing>=0&&<button className="secondary" disabled={busy} onClick={()=>onSelect(missing)}>查看首个未保存步骤</button>}{issue>=0&&<button className="secondary" disabled={busy} onClick={()=>onSelect(issue)}>查看首个待检查步骤</button>}</div>}
   <ol>{steps.map((step,i)=><li key={step.id} data-result-status={own?states[i].kind:'unimported'}><button className="text-button" disabled={busy} aria-current={index===i?'step':undefined} onClick={()=>onSelect(i)}>{i+1}. {step.title}</button><span className="walk-result-status">{own?states[i].label:'尚未导入'}</span>{own&&<p className="small">{states[i].help}</p>}</li>)}</ol>
   {own&&same===steps.length&&<p className="note-box">下一步：换一组参数再解释变化，然后用“独立挑战：回到原题”完成 solve 的返回值和多样例验收。数组一致无法证明字符串返回正确，也无法证明独立完成。</p>}
  </>}
 </section>;
}
