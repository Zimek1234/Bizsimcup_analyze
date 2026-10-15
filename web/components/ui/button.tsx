import * as React from 'react';
import {Slot} from '@radix-ui/react-slot';
import {cva,type VariantProps} from 'class-variance-authority';
import {cn} from '@/lib/utils';
const variants=cva('inline-flex items-center justify-center rounded-lg text-sm font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 disabled:pointer-events-none disabled:opacity-50 px-4 py-2',{variants:{variant:{default:'bg-slate-900 text-white hover:bg-slate-700',outline:'border border-slate-300 bg-white hover:bg-slate-50',ghost:'hover:bg-slate-100'}},defaultVariants:{variant:'default'}});
export function Button({className,variant,asChild=false,...props}:React.ComponentProps<'button'> & VariantProps<typeof variants> & {asChild?:boolean}){const Comp=asChild?Slot:'button';return <Comp className={cn(variants({variant,className}))} {...props}/>;}
