import {useEffect} from 'react';
export function Icon({name,size=20}:{name:string;size?:number}) {
 const paths:Record<string,string> = {
 home:'M3 10 12 3l9 7v11h-6v-7H9v7H3Z',route:'M6 4h12v5H6zM6 15h12v5H6zM12 9v6',
 lab:'M9 3h6M10 3v7l-6 9q-1 2 2 2h12q3 0 2-2l-6-9V3M7 15h10',
 code:'m8 6-6 6 6 6m8-12 6 6-6 6m-3-15-2 18',book:'M3 4h7q2 0 2 2 0-2 2-2h7v16h-7q-2 0-2 2 0-2-2-2H3ZM12 6v16',
 history:'M3 11a9 9 0 1 1 2 7M3 4v7h7M12 7v5l3 2',arrow:'M4 12h16m-6-6 6 6-6 6',check:'m5 12 4 4L19 6',
 search:'M10 3a7 7 0 1 0 0 14 7 7 0 0 0 0-14m5 12 6 6',star:'m12 3 3 6 6 1-4 5 1 6-6-3-6 3 1-6-4-5 6-1Z',
 external:'M14 3h7v7m0-7L10 14M9 3H3v18h18v-6',close:'m6 6 12 12M6 18 18 6',play:'m8 4 12 8-12 8Z',save:'M4 3h13l4 4v14H3V3h1m3 0v6h10V3M7 21v-8h10v8',
 terminal:'m4 6 6 6-6 6m9 0h7',chevron:'m9 5 7 7-7 7',download:'M12 3v12m-5-5 5 5 5-5M4 17v4h16v-4',eye:'M2 12q10-16 20 0-10 16-20 0m10-3a3 3 0 1 0 0 6 3 3 0 0 0 0-6'};
 return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.65" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={paths[name]||paths.code}/></svg>;
}
export function Tag({children,tone=''}:{children:React.ReactNode;tone?:string}) {return <span className={'tag '+tone}>{children}</span>;}
export function Modal({title,children,onClose,wide=false}:{title:string;children:React.ReactNode;onClose:()=>void;wide?:boolean}) {
 useEffect(()=>{const fn=(e:KeyboardEvent)=>{if(e.key==='Escape')onClose();};document.addEventListener('keydown',fn);const previous=document.body.style.overflow;document.body.style.overflow='hidden';return()=>{document.removeEventListener('keydown',fn);document.body.style.overflow=previous;};},[onClose]);
 return <div className="overlay" onClick={onClose}><section className={'modal '+(wide?'wide':'')} role="dialog" aria-modal="true" aria-label={title} onClick={e=>e.stopPropagation()}><header><h2>{title}</h2><button autoFocus className="icon-button" aria-label="关闭" onClick={onClose}><Icon name="close"/></button></header>{children}</section></div>;
}
export function Photo({src,label,onZoom}:{src?:string|null;label:string;onZoom?:(src:string)=>void}) {return <figure className="photo"><figcaption>{label}{src&&<span>点击放大</span>}</figcaption><div>{src?<button onClick={()=>onZoom?.(src)} aria-label={'放大'+label}><img src={src} alt={label}/></button>:<p className="muted">运行后在这里查看图像</p>}</div></figure>;}
export function Empty({title,body}:{title:string;body:string}) {return <div className="empty"><Icon name="lab" size={32}/><h3>{title}</h3><p>{body}</p></div>;}
