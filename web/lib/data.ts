import 'server-only';
import {supabase} from './supabase';
import {defaultSettings,type DashboardData,type Game} from './types';
export async function loadDashboard(gameId?:string,asof?:string):Promise<DashboardData>{
 const db=await supabase();const {data:{user},error:authError}=await db.auth.getUser();
 if(authError||!user)throw new Error('AUTH');
 const gamesResult=await db.from('games').select('id,name,purpose,team_id').order('created_at');
 if(gamesResult.error)throw new Error('DATA');
 const games=(gamesResult.data??[]) as (Game & {team_id:string})[];
 const game=gameId?games.find(g=>g.id===gameId)??null:games[0]??null;
 const preview=process.env.VERCEL_ENV==='preview';
 if(!game)return {games,game:null,heads:[],runs:[],settings:defaultSettings,editable:false,preview};
 const [heads,runs,settings,member]=await Promise.all([
  asof?db.rpc('source_heads_at',{p_game:game.id,p_asof:asof}):db.from('source_heads').select('dataset,origin,last_success,snapshots(*)').eq('game_id',game.id),
  db.from('ingestion_runs').select('id,dataset,origin,status,started_at,finished_at,error,row_count').eq('game_id',game.id).order('started_at',{ascending:false}).limit(100),
  db.from('game_settings').select('*').eq('game_id',game.id).maybeSingle(),
  db.from('team_members').select('role').eq('team_id',game.team_id).eq('user_id',user.id).maybeSingle()
 ]);
 if(heads.error||runs.error||settings.error||member.error)throw new Error('DATA');
 return {games,game,heads:heads.data as unknown as DashboardData['heads'],runs:runs.data??[],settings:settings.data??defaultSettings,editable:!preview&&['editor','admin'].includes(member.data?.role??''),preview};
}
