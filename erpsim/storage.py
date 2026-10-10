"""SQLite history and latest projection. Every entity import commits atomically."""
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import json
import sqlite3
import uuid
from .schema import natural_key, normalize, ENTITIES

SNAPSHOTS = set(ENTITIES) | {"InventoryExport", "SalesExport", "SummarySalesExport", "MarketExport"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


class Store:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS games(
                    id TEXT PRIMARY KEY, name TEXT NOT NULL, created_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS runs(
                    id INTEGER PRIMARY KEY, game_id TEXT NOT NULL REFERENCES games(id),
                    dataset TEXT NOT NULL, source TEXT NOT NULL, started_at TEXT NOT NULL,
                    finished_at TEXT, status TEXT NOT NULL, row_count INTEGER NOT NULL DEFAULT 0,
                    changed_count INTEGER NOT NULL DEFAULT 0, error TEXT, game_time TEXT);
                CREATE TABLE IF NOT EXISTS observations(
                    run_id INTEGER NOT NULL REFERENCES runs(id), record_key TEXT NOT NULL,
                    payload TEXT NOT NULL, PRIMARY KEY(run_id, record_key));
                CREATE TABLE IF NOT EXISTS facts(
                    game_id TEXT NOT NULL REFERENCES games(id), dataset TEXT NOT NULL,
                    record_key TEXT NOT NULL, payload TEXT NOT NULL,
                    first_run INTEGER NOT NULL REFERENCES runs(id), last_run INTEGER NOT NULL REFERENCES runs(id),
                    PRIMARY KEY(game_id, dataset, record_key));
                CREATE INDEX IF NOT EXISTS runs_game ON runs(game_id, dataset, id);
                CREATE TABLE IF NOT EXISTS settings(
                    game_id TEXT PRIMARY KEY REFERENCES games(id), payload TEXT NOT NULL);
                PRAGMA user_version=1;
            """)

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        try:
            with db:
                yield db
        finally:
            db.close()

    def games(self) -> list[dict]:
        with self.connection() as db:
            return [dict(r) for r in db.execute("SELECT * FROM games ORDER BY created_at")]

    def create_game(self, name: str) -> str:
        name = name.strip()
        if not name:
            raise ValueError("Zadejte název hry.")
        key = str(uuid.uuid4())
        with self.connection() as db:
            db.execute("INSERT INTO games VALUES(?,?,?)", (key, name, utc_now()))
        return key

    def begin(self, game: str, dataset: str, source: str, game_time: str | None = None) -> int:
        with self.connection() as db:
            cursor = db.execute("""INSERT INTO runs(game_id,dataset,source,started_at,status,game_time)
                                   VALUES(?,?,?,?,'running',?)""", (game, dataset, source, utc_now(), game_time))
            return cursor.lastrowid

    def fail(self, run: int, error: str):
        with self.connection() as db:
            db.execute("UPDATE runs SET status='failed',finished_at=?,error=? WHERE id=? AND status='running'",
                       (utc_now(), error[:500], run))

    def finish(self, run: int, rows: list[dict]) -> dict:
        with self.connection() as db:
            attempt = db.execute("SELECT * FROM runs WHERE id=?", (run,)).fetchone()
            if attempt is None or attempt["status"] != "running":
                raise ValueError("Aktualizace už byla dokončena nebo neexistuje.")
            dataset, game = attempt["dataset"], attempt["game_id"]
            rows = normalize(dataset, rows)
            changed = 0
            for index, row in enumerate(rows):
                key = natural_key(dataset, row)
                if dataset == "SalesExport":
                    key += f":{index}"
                payload = json.dumps(row, sort_keys=True, ensure_ascii=False)
                old = db.execute("SELECT payload,last_run FROM facts WHERE game_id=? AND dataset=? AND record_key=?",
                                 (game, dataset, key)).fetchone()
                db.execute("INSERT INTO observations VALUES(?,?,?)", (run, key, payload))
                # A late-finishing concurrent read must not overwrite a later-started read.
                if old is None or old["last_run"] < run:
                    changed += int(old is None or old["payload"] != payload)
                    db.execute("""INSERT INTO facts VALUES(?,?,?,?,?,?)
                        ON CONFLICT(game_id,dataset,record_key) DO UPDATE SET
                        payload=excluded.payload,last_run=excluded.last_run""", (game, dataset, key, payload, run, run))
            db.execute("UPDATE runs SET status='success',finished_at=?,row_count=?,changed_count=? WHERE id=?",
                       (utc_now(), len(rows), changed, run))
        return {"rows": len(rows), "changed": changed}

    def import_rows(self, game: str, dataset: str, rows: list[dict], source: str = "file",
                    game_time: str | None = None) -> dict:
        run = self.begin(game, dataset, source, game_time)
        try:
            return self.finish(run, rows)
        except Exception:
            self.fail(run, "Import neprošel validací; předchozí data zachována.")
            raise

    def records(self, game: str, dataset: str, as_of: int | None = None) -> list[dict]:
        with self.connection() as db:
            if dataset in SNAPSHOTS:
                latest = db.execute("""SELECT MAX(id) FROM runs WHERE game_id=? AND dataset=?
                                       AND status='success' AND (? IS NULL OR id<=?)""",
                                    (game, dataset, as_of, as_of)).fetchone()[0]
                rows = db.execute("SELECT payload FROM observations WHERE run_id=?", (latest,))
            else:
                # Reconstruct the latest revision of each identity at the selected download.
                rows = db.execute("""SELECT o.payload FROM observations o JOIN runs r ON r.id=o.run_id
                    WHERE r.game_id=? AND r.dataset=? AND r.status='success'
                    AND (? IS NULL OR r.id<=?) AND o.run_id=(
                      SELECT MAX(o2.run_id) FROM observations o2 JOIN runs r2 ON r2.id=o2.run_id
                      WHERE r2.game_id=r.game_id AND r2.dataset=r.dataset AND r2.status='success'
                      AND o2.record_key=o.record_key AND (? IS NULL OR r2.id<=?))""",
                                  (game, dataset, as_of, as_of, as_of, as_of))
            return [json.loads(r[0]) for r in rows]

    def runs(self, game: str) -> list[dict]:
        with self.connection() as db:
            return [dict(r) for r in db.execute("SELECT * FROM runs WHERE game_id=? ORDER BY id DESC", (game,))]

    def backup(self) -> bytes:
        # SQLite backup includes committed WAL contents; never copy only the live .db file.
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "backup.sqlite"
            with self.connection() as source:
                dest = sqlite3.connect(target)
                try:
                    source.backup(dest)
                finally:
                    dest.close()
            return target.read_bytes()

    def settings(self, game: str) -> dict:
        with self.connection() as db:
            row = db.execute("SELECT payload FROM settings WHERE game_id=?", (game,)).fetchone()
            return json.loads(row[0]) if row else {}

    def save_settings(self, game: str, settings: dict):
        with self.connection() as db:
            db.execute("INSERT INTO settings VALUES(?,?) ON CONFLICT(game_id) DO UPDATE SET payload=excluded.payload",
                       (game, json.dumps(settings, ensure_ascii=False)))
