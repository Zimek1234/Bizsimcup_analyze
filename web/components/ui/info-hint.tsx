'use client';
import {useEffect,useId,useRef,useState} from 'react';
import {createPortal} from 'react-dom';
import {Info} from 'lucide-react';

/** Read-only hint outside the table's scroll container, accessible on touch. */
export function InfoHint({label,children}:{label:string;children:string}){
 const id=useId(),button=useRef<HTMLButtonElement>(null),tip=useRef<HTMLDivElement>(null);
 const timer=useRef<ReturnType<typeof setTimeout>|null>(null);
 const focused=useRef(false);
 const [open,setOpen]=useState(false),[pinned,setPinned]=useState(false);
 const [position,setPosition]=useState({left:12,top:12});
 const cancel=()=>{if(timer.current)clearTimeout(timer.current);timer.current=null;};
 const place=()=>{const rect=button.current?.getBoundingClientRect();if(!rect)return;const width=Math.min(288,window.innerWidth-24),height=tip.current?.offsetHeight??100;setPosition({left:Math.max(12,Math.min(rect.right-width,window.innerWidth-width-12)),top:Math.max(12,rect.bottom+8+height<=window.innerHeight-12?rect.bottom+8:rect.top-height-8)});};
 const show=()=>{cancel();place();setOpen(true);};
 const hide=()=>{cancel();if(!pinned&&!focused.current)timer.current=setTimeout(()=>setOpen(false),150);};
 useEffect(()=>{
  if(!open)return;
  place();
  const outside=(e:PointerEvent)=>{if(!button.current?.contains(e.target as Node)&&!tip.current?.contains(e.target as Node)){setPinned(false);setOpen(false);}};
  const escape=(e:KeyboardEvent)=>{if(e.key==='Escape'){cancel();setPinned(false);setOpen(false);}};
  window.addEventListener('resize',place);window.addEventListener('scroll',place,true);document.addEventListener('pointerdown',outside);document.addEventListener('keydown',escape);
  return()=>{window.removeEventListener('resize',place);window.removeEventListener('scroll',place,true);document.removeEventListener('pointerdown',outside);document.removeEventListener('keydown',escape);cancel();};
 },[open]);
 useEffect(()=>()=>cancel(),[]);
 return <><button ref={button} type="button" aria-label={label} aria-expanded={open} aria-describedby={open?id:undefined} onMouseEnter={show} onMouseLeave={hide} onFocus={()=>{focused.current=true;show();}} onBlur={()=>{focused.current=false;cancel();setPinned(false);setOpen(false);}} onClick={()=>{cancel();place();setPinned(!pinned);setOpen(!pinned);}} className="inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-slate-400 hover:text-teal-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-700"><Info size={14} aria-hidden="true"/></button>
 {open&&createPortal(<div ref={tip} id={id} role="tooltip" onMouseEnter={cancel} onMouseLeave={hide} style={{...position,width:'min(288px, calc(100vw - 24px))',maxHeight:'calc(100vh - 24px)'}} className="fixed z-50 overflow-y-auto rounded-lg border border-slate-200 bg-white p-3 text-left text-xs leading-5 text-slate-700 shadow-lg">{children}</div>,document.body)}</>;
}
