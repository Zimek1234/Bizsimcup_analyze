-- Read-only diagnostics after installation. Never paste a key/password into SQL.
select tablename, rowsecurity as rls_enabled
from pg_tables
where schemaname='public' and tablename in
 ('teams','team_members','games','game_settings','sync_leases','ingestion_runs','snapshots','source_heads')
order by tablename;

select t.name as team_name, m.user_id, m.role
from public.team_members m join public.teams t on t.id=m.team_id;

select g.id as game_id,g.name,g.purpose,h.dataset,h.origin,h.last_success,
 r.status,r.row_count
from public.games g
left join public.source_heads h on h.game_id=g.id
left join public.ingestion_runs r on r.id=h.run_id
order by g.created_at,h.origin,h.dataset;

select g.name,r.dataset,r.origin,r.status,r.started_at,r.finished_at,r.error
from public.ingestion_runs r join public.games g on g.id=r.game_id
order by r.started_at desc limit 50;
