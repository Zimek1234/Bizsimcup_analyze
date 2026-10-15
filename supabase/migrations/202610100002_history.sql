-- Every successful fetch links to its immutable complete snapshot, even when content repeats.
alter table public.ingestion_runs add column snapshot_id uuid references public.snapshots;
update public.ingestion_runs r set snapshot_id=h.snapshot_id from public.source_heads h where h.run_id=r.id;
create or replace function public.publish_snapshot(p_run uuid,p_owner uuid,p_fence bigint,p_hash text,p_rows jsonb,p_views jsonb)
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
 update public.ingestion_runs set status='success', finished_at=clock_timestamp(),row_count=jsonb_array_length(p_rows),snapshot_id=s where id=p_run;
 insert into public.source_heads values(r.game_id,r.dataset,r.origin,s,p_run,clock_timestamp())
 on conflict(game_id,dataset,origin) do update set snapshot_id=excluded.snapshot_id,run_id=excluded.run_id,last_success=excluded.last_success;
 return s;
end; $$;

create function public.source_heads_at(p_game uuid,p_asof timestamptz) returns jsonb
language sql stable security invoker set search_path='' as $$
 select coalesce(jsonb_agg(jsonb_build_object('dataset',r.dataset,'origin',r.origin,
 'last_success',r.finished_at,'snapshots',to_jsonb(s))),'[]'::jsonb)
 from (select distinct on (dataset,origin) * from public.ingestion_runs
 where game_id=p_game and status='success' and finished_at<=p_asof and snapshot_id is not null
 order by dataset,origin,started_at desc) r
 join public.snapshots s on s.id=r.snapshot_id;
$$;
revoke all on function public.source_heads_at(uuid,timestamptz) from public,anon;
grant execute on function public.source_heads_at(uuid,timestamptz) to authenticated,service_role;
