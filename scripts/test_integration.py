"""Real local Auth/PostgREST/RLS/lease tests. Requires scripts/local_stack.py. No production access."""
from pathlib import Path
import json
import os
import secrets
import subprocess
import sys
import uuid
from decimal import Decimal
import requests
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from service.cloud import CloudStore,CloudError
from erpsim.loaders import read_workbook
from erpsim.schema import ENTITIES
from erpsim.sync import refresh
from erpsim.odata import ODataError

def main():
    env=dict(x.split('=',1) for x in (ROOT/'.local/worker.env').read_text().splitlines())
    assert env['SUPABASE_URL']=='http://127.0.0.1:54321','Integration tests must stay local'
    os.environ.update(env);store=CloudStore(allow_local=True)
    url=store.url;anon=dict(x.split('=',1) for x in (ROOT/'web/.env.local').read_text().splitlines())['NEXT_PUBLIC_SUPABASE_ANON_KEY']
    def auth_user():
        email=secrets.token_hex(8)+'@example.test';password=secrets.token_urlsafe(25)
        r=requests.post(url+'/auth/v1/admin/users',headers={'apikey':store.key,'Authorization':'Bearer '+store.key},json={'email':email,'password':password,'email_confirm':True},timeout=20)
        assert r.status_code==200,'Local Auth provisioning failed'
        user=r.json()['id']
        r=requests.post(url+'/auth/v1/token?grant_type=password',headers={'apikey':anon},json={'email':email,'password':password},timeout=20)
        assert r.ok,'Real password authentication failed'
        return user,r.json()['access_token']
    def rest(token,method,path,payload=None):
        return requests.request(method,url+'/rest/v1/'+path,headers={'apikey':anon,'Authorization':'Bearer '+token,'Prefer':'return=representation'},json=payload,timeout=30)
    users=[auth_user() for _ in range(3)]
    team=store.request('POST','teams',{'name':'Integration '+secrets.token_hex(4)})[0]['id']
    for (user,_),role in zip(users,['viewer','editor','viewer']):
        if user!=users[-1][0]:store.request('POST','team_members',{'team_id':team,'user_id':user,'role':role})
    games=[store.request('POST','games',{'team_id':team,'name':'Integration '+p,'purpose':p})[0]['id'] for p in ['trial','competition']]
    for g in games:store.request('POST','game_settings',{'game_id':g})
    workbook,_=read_workbook((ROOT/'samples/BIZ SIM data ze zkušebky.xlsx').read_bytes(),'a.xlsx')
    rows=workbook['Sales'];game=games[0]
    try:
        snapshots=[]
        with store.lease(game):
            competing=CloudStore(allow_local=True)
            try:
                with competing.lease(game):raise AssertionError('Duplicate worker acquired lease')
            except CloudError:pass
            for _ in range(2):
                run=store.begin(game,'Sales','file:test');snapshots.append(store.finish(run,rows)['snapshot'])
            assert snapshots[0]==snapshots[1],'Repeat import did not reuse snapshot'
            # Preserve last good data when the unchanged refresh reader reports an outage.
            class Outage:
                def metadata(self):raise ODataError('Síťový výpadek nebo timeout; předchozí data zachována.')
            result=refresh(store,game,Outage(),['Sales'])
            assert result['Sales'].get('error')
            before=store.request('GET',f'source_heads?game_id=eq.{game}&dataset=eq.Sales')[0]['snapshot_id']
            assert before==snapshots[0]
            # Valid metadata, failure while reading pages: no partial snapshot published.
            class FailedRead:
                def metadata(self):return ENTITIES
                def read(self,dataset):
                    if dataset=='Sales':raise ODataError('Timeout druhé stránky; neúplná data zachována.')
                    return workbook[dataset]
            result=refresh(store,game,FailedRead(),['Sales'])
            assert result['Sales'].get('error')
            assert store.request('GET',f'source_heads?game_id=eq.{game}&dataset=eq.Sales')[0]['snapshot_id']==before
        data=store.request('GET',f'snapshots?id=eq.{snapshots[0]}')[0]
        assert len(data['rows'])==186
        assert sum(Decimal(r['NET_VALUE']) for r in data['rows'])==Decimal('3973037.2')
        assert store.request('GET',f'source_heads?game_id=eq.{games[1]}')==[],'Games mixed'
        viewer=users[0][1];editor=users[1][1];outsider=users[2][1]
        for table in ['games','snapshots','source_heads','ingestion_runs','game_settings','team_members']:
            r=rest(outsider,'GET',table);assert r.ok and r.json()==[],f'Outsider read {table}'
        assert rest(viewer,'GET',f'snapshots?id=eq.{snapshots[0]}').json()[0]['id']==snapshots[0]
        assert rest(anon,'GET','games').status_code in (401,403),'Anonymous access permitted'
        r=rest(viewer,'PATCH',f'game_settings?game_id=eq.{game}',{'stock_days':7});assert not r.ok or r.json()==[]
        r=rest(editor,'PATCH',f'game_settings?game_id=eq.{game}',{'stock_days':7});assert r.ok and r.json()[0]['stock_days']==7
        assert rest(editor,'POST','games',{'team_id':team,'name':'unauthorized','purpose':'trial'}).status_code in (401,403)
        assert rest(editor,'POST','rpc/acquire_lease',{'p_game':game,'p_owner':str(uuid.uuid4())}).status_code in (401,403,404)
        assert rest(viewer,'POST','rpc/source_heads_at',{'p_game':game,'p_asof':'2000-01-01T00:00:00Z'}).json()==[]
        assert rest(outsider,'POST','rpc/source_heads_at',{'p_game':game,'p_asof':'2100-01-01T00:00:00Z'}).json()==[]
        # Expire old lease, transfer ownership, ensure fencing rejects late publication.
        with store.lease(game):
            run=store.begin(game,'Sales','odata');old_fence=store.fence
            subprocess.run(['docker','exec','erpsim-local-db-1','psql','-U','postgres','-c',
                f"update public.sync_leases set expires_at=clock_timestamp()-interval '1 second' where game_id='{game}'"],check=True,stdout=subprocess.DEVNULL)
            competing=CloudStore(allow_local=True)
            with competing.lease(game):
                assert competing.fence>old_fence
                try:store.finish(run,rows);raise AssertionError('Fenced worker published')
                except CloudError:pass
            store.fail(run,'Zámek hry byl převzat; snímek nebyl publikován.')
        try:
            store.validate_rules(games[1],workbook['Current_Game_Rules'])
            raise AssertionError('Introduction accepted for competition')
        except CloudError:pass
        # Exercise the real worker orchestration against actual database, using the supplied export as OData fixture.
        from service import cli
        original_client = cli.client
        class WorkbookClient:
            def metadata(self):return ENTITIES
            def read(self,dataset):return workbook[dataset]
        class MissingRules(WorkbookClient):
            def read(self,dataset):return [] if dataset=='Current_Game_Rules' else workbook[dataset]
        try:
            before_rules=store.request('GET',f'source_heads?game_id=eq.{games[0]}&origin=eq.odata')
            cli.client=lambda:MissingRules()
            args=cli.parser().parse_args(['--local','sync','--game',games[0],'--once'])
            try:cli.run(args);raise AssertionError('Worker accepted missing game rules')
            except CloudError:pass
            assert store.request('GET',f'source_heads?game_id=eq.{games[0]}&origin=eq.odata')==before_rules
            cli.client=lambda:WorkbookClient()
            cli.run(args)
            assert len(store.request('GET',f'source_heads?game_id=eq.{games[0]}&origin=eq.odata'))==len(ENTITIES)
        finally:cli.client=original_client
        print('PASS: actual Auth, member RLS, outsider/anonymous denial, editor/viewer settings, game isolation, duplicate import, outage/partial-page preservation, lease exclusion/fencing, RLS history, full worker fixture cycle and missing-rules refusal.')
    finally:
        # Remove only this test's own rows/accounts, keeping local demo intact.
        for g in games:
            for table in ['source_heads','ingestion_runs','snapshots','sync_leases','game_settings']:
                store.request('DELETE',f'{table}?game_id=eq.{g}')
            store.request('DELETE',f'games?id=eq.{g}')
        store.request('DELETE',f'teams?id=eq.{team}')
        for user,_ in users:
            requests.delete(url+'/auth/v1/admin/users/'+user,headers={'apikey':store.key,'Authorization':'Bearer '+store.key},timeout=20)
if __name__=='__main__':main()
