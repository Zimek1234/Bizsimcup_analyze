-- Run in Supabase SQL Editor or `supabase db push`. No ERPsim credentials here.
create extension if not exists pgcrypto;
create table public.teams (id uuid primary key default gen_random_uuid(), name text not null);
create table public.team_members (
 team_id uuid references public.teams on delete cascade,
 user_id uuid references auth.users on delete cascade,
 role text not null check(role in ('viewer','editor','admin')), primary key(team_id,user_id));
create table public.games (
 id uuid primary key default gen_random_uuid(), team_id uuid not null references public.teams,
 name text not null, purpose text not null check(purpose in ('trial','competition')),
 created_at timestamptz not null default now());
create table public.game_settings (
 game_id uuid primary key references public.games on delete cascade,
 interval_seconds integer not null default 30 check(interval_seconds between 10 and 3600),
 stale_seconds integer not null default 180 check(stale_seconds between 30 and 86400),
 stock_days numeric not null default 3 check(stock_days between 0 and 1000),
 margin_percent numeric not null default 10 check(margin_percent between -1000 and 100),
 marketing_limit numeric check(marketing_limit >= 0),
 currency text, unit text, updated_at timestamptz not null default now());
create table public.sync_leases (
 game_id uuid primary key references public.games on delete cascade, owner uuid not null,
 fence bigint not null default 1, expires_at timestamptz not null);
create table public.ingestion_runs (
 id uuid primary key default gen_random_uuid(), game_id uuid not null references public.games,
 dataset text not null, origin text not null check(origin ~ '^(odata|file:[a-zA-Z0-9_-]+)$'),
 started_at timestamptz not null default clock_timestamp(), finished_at timestamptz,
 status text not null default 'running' check(status in ('running','success','failed')),
 row_count integer, error text, game_time text);
create table public.snapshots (
 id uuid primary key default gen_random_uuid(), game_id uuid not null references public.games,
 dataset text not null, origin text not null, content_hash text not null,
 rows jsonb not null check(jsonb_typeof(rows)='array'), views jsonb not null check(jsonb_typeof(views)='array'),
 created_at timestamptz not null default clock_timestamp(),
 unique(game_id,dataset,origin,content_hash));
create table public.source_heads (
 game_id uuid references public.games, dataset text not null, origin text not null,
 snapshot_id uuid not null references public.snapshots, run_id uuid not null references public.ingestion_runs,
 last_success timestamptz not null, primary key(game_id,dataset,origin));
create index ingestion_history on public.ingestion_runs(game_id,origin,started_at desc);
create index snapshot_lookup on public.snapshots(game_id,origin,dataset);

create function public.is_member(t uuid, edit boolean default false) returns boolean
language sql stable security definer set search_path='' as $$
 select exists(select 1 from public.team_members m where m.team_id=t and m.user_id=auth.uid()
 and (not edit or m.role in ('editor','admin')));
$$;
create function public.can_read_game(g uuid, edit boolean default false) returns boolean
language sql stable security definer set search_path='' as $$
 select exists(select 1 from public.games x where x.id=g and public.is_member(x.team_id,edit));
$$;
alter table public.teams enable row level security;
alter table public.team_members enable row level security;
alter table public.games enable row level security;
alter table public.game_settings enable row level security;
alter table public.sync_leases enable row level security;
alter table public.ingestion_runs enable row level security;
alter table public.snapshots enable row level security;
alter table public.source_heads enable row level security;
create policy team_read on public.teams for select to authenticated using(public.is_member(id));
create policy members_read on public.team_members for select to authenticated using(public.is_member(team_id));
create policy games_read on public.games for select to authenticated using(public.is_member(team_id));
create policy settings_read on public.game_settings for select to authenticated using(public.can_read_game(game_id));
create policy settings_edit on public.game_settings for update to authenticated
 using(public.can_read_game(game_id,true)) with check(public.can_read_game(game_id,true));
create policy runs_read on public.ingestion_runs for select to authenticated using(public.can_read_game(game_id));
create policy snapshots_read on public.snapshots for select to authenticated using(public.can_read_game(game_id));
create policy heads_read on public.source_heads for select to authenticated using(public.can_read_game(game_id));
revoke all on public.teams,public.team_members,public.games,public.game_settings,public.sync_leases,public.ingestion_runs,public.snapshots,public.source_heads from anon, authenticated;
grant select on public.teams, public.team_members, public.games, public.game_settings,
 public.ingestion_runs, public.snapshots, public.source_heads to authenticated;
grant update(interval_seconds,stale_seconds,stock_days,margin_percent,marketing_limit,currency,unit,updated_at)
 on public.game_settings to authenticated;
grant all on public.teams,public.team_members,public.games,public.game_settings,public.sync_leases,public.ingestion_runs,public.snapshots,public.source_heads to service_role;

create function public.acquire_lease(p_game uuid,p_owner uuid) returns bigint
language plpgsql security definer set search_path='' as $$
declare f bigint;
begin
 insert into public.sync_leases(game_id,owner,fence,expires_at)
 values(p_game,p_owner,1,clock_timestamp()+interval '120 seconds')
 on conflict(game_id) do update set owner=excluded.owner,fence=public.sync_leases.fence+1,
 expires_at=excluded.expires_at where public.sync_leases.expires_at<clock_timestamp()
 returning fence into f;
 return f;
end; $$;
create function public.heartbeat(p_game uuid,p_owner uuid,p_fence bigint) returns boolean
language plpgsql security definer set search_path='' as $$
begin
 update public.sync_leases set expires_at=clock_timestamp()+interval '120 seconds'
 where game_id=p_game and owner=p_owner and fence=p_fence and expires_at>clock_timestamp();
 return found;
end; $$;
create function public.release_lease(p_game uuid,p_owner uuid,p_fence bigint) returns void
language sql security definer set search_path='' as $$
 update public.sync_leases set expires_at=clock_timestamp() where game_id=p_game and owner=p_owner and fence=p_fence;
$$;
create function public.publish_snapshot(p_run uuid,p_owner uuid,p_fence bigint,p_hash text,p_rows jsonb,p_views jsonb)
returns uuid language plpgsql security definer set search_path='' as $$
declare r public.ingestion_runs; s uuid;
begin
 select * into r from public.ingestion_runs where id=p_run and status='running' for update;
 if r.id is null then raise exception 'run not active'; end if;
 -- Lock also serializes takeover with publication. A stale worker can never publish.
 perform 1 from public.sync_leases where game_id=r.game_id and owner=p_owner and fence=p_fence
 and expires_at>clock_timestamp() for update;
 if not found then raise exception 'lease lost'; end if;
 insert into public.snapshots(game_id,dataset,origin,content_hash,rows,views)
 values(r.game_id,r.dataset,r.origin,p_hash,p_rows,p_views)
 on conflict(game_id,dataset,origin,content_hash) do update set content_hash=excluded.content_hash returning id into s;
 update public.ingestion_runs set status='success', finished_at=clock_timestamp(),row_count=jsonb_array_length(p_rows) where id=p_run;
 insert into public.source_heads values(r.game_id,r.dataset,r.origin,s,p_run,clock_timestamp())
 on conflict(game_id,dataset,origin) do update set snapshot_id=excluded.snapshot_id,run_id=excluded.run_id,last_success=excluded.last_success;
 return s;
end; $$;
-- Revoke PostgreSQL's default PUBLIC function execute permission, especially worker RPCs.
revoke all on function public.is_member(uuid,boolean),public.can_read_game(uuid,boolean),
 public.acquire_lease(uuid,uuid),public.heartbeat(uuid,uuid,bigint),public.release_lease(uuid,uuid,bigint),
 public.publish_snapshot(uuid,uuid,bigint,text,jsonb,jsonb) from public,anon,authenticated;
grant execute on function public.is_member(uuid,boolean),public.can_read_game(uuid,boolean) to authenticated,service_role;
grant execute on function public.acquire_lease(uuid,uuid),public.heartbeat(uuid,uuid,bigint),
 public.release_lease(uuid,uuid,bigint),public.publish_snapshot(uuid,uuid,bigint,text,jsonb,jsonb) to service_role;
