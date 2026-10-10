-- First setup only, AFTER both migrations and creating your confirmed Auth user.
-- Replace DOPLNTE_EMAIL_UZIVATELE only. Never put a password/key in this SQL.
-- May be repeated: it reuses the same team and first games, not a new simulation session.
begin;
do $$
declare
  owner_email text := 'DOPLNTE_EMAIL_UZIVATELE';
  team_name text := 'ERPsim tým';
  owner_id uuid;
  first_team uuid;
  trial_id uuid;
  competition_id uuid;
  matching integer;
begin
  if position('@' in owner_email)=0 then
    raise exception 'Doplňte e-mail účtu vytvořeného v Authentication → Users.';
  end if;
  select count(*), (array_agg(id))[1] into matching, owner_id
    from auth.users where lower(email)=lower(owner_email) and email_confirmed_at is not null;
  if matching <> 1 then
    raise exception 'Nenalezen právě jeden potvrzený Auth účet s tímto e-mailem. Vytvořte/potvrďte uživatele.';
  end if;
  select count(*), (array_agg(id))[1] into matching, first_team
    from public.teams where name=team_name;
  if matching > 1 then
    raise exception 'Existuje více týmů stejného názvu; zvolte jiný team_name nebo kontaktujte správce.';
  end if;
  if first_team is null then
    insert into public.teams(name) values(team_name) returning id into first_team;
  end if;
  insert into public.team_members(team_id,user_id,role) values(first_team,owner_id,'admin')
    on conflict(team_id,user_id) do update set role='admin';
  select count(*), (array_agg(id))[1] into matching, trial_id
    from public.games where team_id=first_team and name='Zkouška Introduction' and purpose='trial';
  if matching>1 then raise exception 'Zkušební hra není jednoznačná.'; end if;
  if trial_id is null then
    insert into public.games(team_id,name,purpose)
      values(first_team,'Zkouška Introduction','trial') returning id into trial_id;
  end if;
  select count(*), (array_agg(id))[1] into matching, competition_id
    from public.games where team_id=first_team and name='Soutěž Manufacturing Extended' and purpose='competition';
  if matching>1 then raise exception 'Soutěžní hra není jednoznačná.'; end if;
  if competition_id is null then
    insert into public.games(team_id,name,purpose)
      values(first_team,'Soutěž Manufacturing Extended','competition') returning id into competition_id;
  end if;
  insert into public.game_settings(game_id) values(trial_id),(competition_id)
    on conflict(game_id) do nothing;
end $$;
commit;

-- Save these identifiers locally. They are not passwords or API keys.
select t.id as team_id, g.id as game_id, g.name, g.purpose
from public.games g join public.teams t on t.id=g.team_id
where t.name='ERPsim tým' order by g.purpose;
