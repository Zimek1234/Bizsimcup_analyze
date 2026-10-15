export type Row=Record<string,string|number|null>;
export type Snapshot={id:string;dataset:string;origin:string;rows:Row[];views:Row[];created_at:string};
export type Head={dataset:string;origin:string;last_success:string;snapshots:Snapshot};
export type Game={id:string;name:string;purpose:'trial'|'competition'};
export type Settings={interval_seconds:number;stale_seconds:number;stock_days:number;margin_percent:number;marketing_limit:number|null;currency:string|null;unit:string|null};
export type Run={id:string;dataset:string;origin:string;status:string;started_at:string;finished_at:string|null;error:string|null;row_count:number|null};
export type DashboardData={games:Game[];game:Game|null;heads:Head[];runs:Run[];settings:Settings;editable:boolean;preview:boolean};
export const defaultSettings:Settings={interval_seconds:30,stale_seconds:180,stock_days:3,margin_percent:10,marketing_limit:null,currency:null,unit:null};
