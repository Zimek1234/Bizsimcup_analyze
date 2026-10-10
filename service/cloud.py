"""Supabase adapter to the existing refresh protocol. Secrets never enter analytics payloads."""
from contextlib import contextmanager
from decimal import Decimal
import hashlib
import json
import os
import threading
import uuid
from urllib.parse import urlsplit
import requests
from erpsim.analytics import views
from erpsim.schema import normalize


class CloudError(RuntimeError):
    pass


def serial(value):
    return str(value) if isinstance(value, Decimal) else value


class CloudStore:
    def __init__(self, url=None, key=None, allow_local=False):
        self.url = (url or os.environ.get('SUPABASE_URL', '')).rstrip('/')
        self.key = key or os.environ.get('SUPABASE_SERVICE_ROLE_KEY', '')
        parts=urlsplit(self.url)
        valid_url=bool(parts.hostname) and not (parts.username or parts.password or parts.query or parts.fragment or parts.path.strip('/'))
        secure=parts.scheme=='https' or (allow_local and parts.scheme=='http' and parts.hostname=='127.0.0.1')
        if not self.key or not valid_url or not secure:
            raise CloudError('Nastavte HTTPS SUPABASE_URL a SUPABASE_SERVICE_ROLE_KEY v prostředí služby.')
        self.owner = str(uuid.uuid4())
        self.game = None
        self.fence = None
        self.lost = threading.Event()

    def request(self, method, path, payload=None):
        try:
            response = requests.request(method, self.url + '/rest/v1/' + path,
                headers={'apikey': self.key, 'Authorization': 'Bearer ' + self.key,
                         'Prefer': 'return=representation'}, json=payload, timeout=(5, 60), allow_redirects=False)
        except requests.RequestException:
            raise CloudError('Supabase není dostupná; ověřte síť, adresu projektu a stav služby.') from None
        if not response.ok:
            # Do not expose raw URLs, response bodies, tokens or database details.
            if response.status_code in (401, 403):
                raise CloudError('Supabase odmítla přístup; ověřte klíč služby a oprávnění.')
            raise CloudError('Ukládání do Supabase selhalo; ověřte migrace a zámek hry.')
        return response.json() if response.content else None

    def rpc(self, name, **payload):
        return self.request('POST', 'rpc/' + name, payload)

    @contextmanager
    def lease(self, game):
        try:
            game = str(uuid.UUID(game))
        except (ValueError,AttributeError):
            raise CloudError('ID hry musí být platné UUID vytvořené pro konkrétní herní běh.') from None
        self.game = game
        self.fence = self.rpc('acquire_lease', p_game=game, p_owner=self.owner)
        if self.fence is None:
            raise CloudError('Pro tuto hru již pracuje jiný synchronizátor nebo import.')
        self.lost.clear()
        stop = threading.Event()
        def beat():
            while not stop.wait(15):
                try:
                    if not self.rpc('heartbeat', p_game=game, p_owner=self.owner, p_fence=self.fence):
                        self.lost.set()
                        return
                except CloudError:
                    self.lost.set()
                    return
        thread = threading.Thread(target=beat, daemon=True)
        thread.start()
        try:
            yield self
        finally:
            stop.set()
            thread.join(timeout=65)
            try:
                self.rpc('release_lease', p_game=game, p_owner=self.owner, p_fence=self.fence)
            except CloudError:
                pass
            self.game = self.fence = None

    def begin(self, game, dataset, source, game_time=None):
        game = str(uuid.UUID(game))
        if game != self.game or self.fence is None or self.lost.is_set():
            raise CloudError('Zámek hry byl ztracen; publikování bylo zastaveno.')
        return self.request('POST', 'ingestion_runs', {'game_id':game, 'dataset':dataset,
            'origin':source, 'game_time':game_time})[0]['id']

    def fail(self, run, error):
        from datetime import datetime, timezone
        self.request('PATCH', f'ingestion_runs?id=eq.{run}&status=eq.running',
            {'status':'failed', 'finished_at':datetime.now(timezone.utc).isoformat(), 'error':error[:500]})

    def validate_rules(self, game, rows):
        games=self.request('GET',f'games?id=eq.{str(uuid.UUID(game))}&select=purpose')
        if not games:
            raise CloudError('Hra nebyla nalezena; ověřte její UUID a projekt Supabase.')
        if games[0]['purpose']=='competition' and any('introduction' in str(r.get('SCENARIO','')).lower() for r in rows):
            raise CloudError('Pravidla Introduction nepatří do soutěžní hry. Použijte zkušební UUID nebo připojte skutečné Manufacturing Extended.')

    def finish(self, run, rows):
        attempt = self.request('GET', f'ingestion_runs?id=eq.{run}&select=dataset')[0]
        rows = normalize(attempt['dataset'], rows)
        if attempt['dataset']=='Current_Game_Rules':
            self.validate_rules(self.game,rows)
        # Decimal views are computed by the unchanged, verified Python implementation.
        projection = json.loads(json.dumps(views(attempt['dataset'], rows), default=serial))
        encoded = json.dumps(rows, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
        snapshot = self.rpc('publish_snapshot', p_run=run, p_owner=self.owner, p_fence=self.fence,
            p_hash=hashlib.sha256(encoded.encode()).hexdigest(), p_rows=rows, p_views=projection)
        return {'snapshot':snapshot, 'rows':len(rows)}
