"""python -m service.cli --help. All ERPsim operations are GET via the original reader."""
import argparse
import os
from pathlib import Path
import random
import signal
import threading
import time
from erpsim.loaders import read_file, read_workbook
from erpsim.odata import ODataClient, ODataError, DEFAULT_URL
from erpsim.schema import DEFAULT_SYNC, ENTITIES, EXPORTS
from erpsim.sync import refresh
from .cloud import CloudStore, CloudError


def parser():
    p = argparse.ArgumentParser(description='ERPsim → Supabase; pouze čtení ERPsim')
    p.add_argument('--local', action='store_true', help='Pouze lokální testovací API 127.0.0.1')
    sub = p.add_subparsers(dest='command', required=True)
    probe = sub.add_parser('probe', help='Test OData bez zápisu a bez Supabase')
    probe.add_argument('--dataset', choices=list(ENTITIES), default='Current_Game_Rules')
    provision = sub.add_parser('create-game')
    provision.add_argument('--team', required=True)
    provision.add_argument('--name', required=True)
    provision.add_argument('--purpose', choices=['trial','competition'], required=True)
    imp = sub.add_parser('import')
    imp.add_argument('--game', required=True)
    imp.add_argument('--file', type=Path, required=True)
    imp.add_argument('--origin', required=True, help='Stabilní označení zdroje, např. zkouska; bez názvu souboru')
    imp.add_argument('--dataset', choices=['Auto','Workbook', *ENTITIES, *EXPORTS], default='Workbook')
    imp.add_argument('--sheet')
    imp.add_argument('--separator', default=';')
    imp.add_argument('--decimal', choices=['.',','], default='.')
    imp.add_argument('--encoding', default='utf-8-sig')
    sync = sub.add_parser('sync')
    sync.add_argument('--game', required=True)
    sync.add_argument('--once', action='store_true')
    sync.add_argument('--datasets', nargs='+', choices=list(ENTITIES), default=None)
    return p


def client():
    return ODataClient(os.environ.get('ERPSIM_ODATA_URL', DEFAULT_URL),
                       os.environ.get('ERPSIM_ODATA_USER', ''), os.environ.get('ERPSIM_ODATA_PASSWORD', ''))


def run(args):
    if args.command == 'probe':
        result = client().probe(args.dataset)
        print('OData připojení a schéma ověřeno. Zkušební čtení:', result['sample_rows'], 'řádků.')
        return
    store = CloudStore(allow_local=args.local)
    if args.command == 'create-game':
        game = store.request('POST','games',{'team_id':args.team,'name':args.name,'purpose':args.purpose})[0]
        store.request('POST','game_settings',{'game_id':game['id']})
        print('ID nové hry:',game['id'])
        return
    if args.command == 'import':
        import re
        if not re.fullmatch('[a-zA-Z0-9_-]+',args.origin):
            raise CloudError('Označení zdroje smí obsahovat pouze písmena, číslice, _ a -.')
        content = args.file.read_bytes()
        if args.dataset == 'Workbook':
            data, skipped = read_workbook(content, args.file.name)
            print('Nepodporované listy vynechány:', len(skipped))
        else:
            dataset, rows = read_file(content,args.file.name,args.dataset,args.sheet,
                args.separator,args.decimal,args.encoding)
            data = {dataset:rows}
        with store.lease(args.game):
            for dataset, rows in data.items():
                attempt = store.begin(args.game,dataset,'file:'+args.origin)
                try:
                    store.finish(attempt,rows)
                except Exception:
                    store.fail(attempt,'Import nebyl uložen. Ověřte schéma, připojení a zámek hry.')
                    raise
                print(dataset, ':',len(rows),'řádků ověřeno a uloženo.')
        return
    stopped = threading.Event()
    for sig in (signal.SIGINT,signal.SIGTERM):
        signal.signal(sig,lambda *_: stopped.set())
    failures = 0
    with store.lease(args.game):
        while not stopped.is_set():
            if store.lost.is_set():
                raise CloudError('Zámek hry ztracen; synchronizátor končí.')
            started = time.monotonic()
            settings = store.request('GET',f'game_settings?game_id=eq.{args.game}')
            interval = settings[0]['interval_seconds'] if settings else 30
            source = client()
            class CycleClient:
                # Cache this cycle's metadata without modifying the original reader.
                def __init__(self):
                    self.rules_ok = False
                    try:
                        self.live = source.metadata()
                        self.error = None
                    except ODataError as exc:
                        self.live = None
                        self.error = exc
                def metadata(self):
                    if self.error:
                        raise self.error
                    return self.live
                def read(self, dataset):
                    if dataset != 'Current_Game_Rules' and not self.rules_ok:
                        raise ODataError('Skutečná pravidla hry nebyla načtena; nový snímek této entity nebyl publikován.')
                    rows = source.read(dataset)
                    if dataset == 'Current_Game_Rules':
                        if not rows:
                            raise ODataError('Current_Game_Rules jsou prázdná; ověřte aktivní hru.')
                        self.rules_ok = True
                    return rows
            cycle = CycleClient()
            datasets = args.datasets if args.datasets is not None else [d for d in ENTITIES if cycle.live and d in cycle.live]
            if cycle.error:
                datasets = args.datasets or list(DEFAULT_SYNC)
            results = refresh(store,args.game,cycle,datasets)
            errors = sum('error' in r for r in results.values())
            failures = failures+1 if errors else 0
            duration = time.monotonic()-started
            print(f'Aktualizace: {len(results)-errors}/{len(results)} zdrojů; trvání {duration:.1f}s.', flush=True)
            if args.once:
                if errors:
                    raise CloudError('Některé zdroje selhaly; podrobnosti jsou v diagnostice hry.')
                return
            # No overlapping cycles. Respect requested cadence when possible; cap backoff at 5 minutes.
            delay = max(1,interval-duration) if not failures else min(300,interval*2**min(failures,4))+random.uniform(0,3)
            stopped.wait(delay)


def main():
    args = parser().parse_args()
    try:
        run(args)
    except (CloudError,ODataError) as exc:
        print(str(exc))
        return 1
    except (ValueError,OSError):
        print('Soubor nebo konfigurace není platná. Ověřte formát, cestu a schéma; tajné údaje se nevypisují.')
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
