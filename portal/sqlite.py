import json
import sqlite3
from contextlib import closing, contextmanager
from dataclasses import asdict
from pathlib import Path

from .domain import Request, Status, Unavailable
from .ports import Receipt


class SQLiteStorage:
    def __init__(self, path: Path):
        self.path = path

    def initialize(self) -> None:
        with self.transaction(write=True) as repo:
            repo.db.execute(
                "CREATE TABLE IF NOT EXISTS requests (id TEXT PRIMARY KEY, "
                "owner TEXT NOT NULL, status TEXT NOT NULL, body TEXT NOT NULL)"
            )
            repo.db.execute(
                "CREATE TABLE IF NOT EXISTS receipts (actor_id TEXT NOT NULL, "
                "key TEXT NOT NULL, fingerprint TEXT NOT NULL, "
                "request_id TEXT NOT NULL, status TEXT NOT NULL, "
                "PRIMARY KEY (actor_id, key))"
            )

    @contextmanager
    def transaction(self, *, write: bool = False):
        try:
            with closing(sqlite3.connect(self.path, timeout=1)) as db, db:
                db.execute("BEGIN IMMEDIATE" if write else "BEGIN")
                yield SQLiteRepository(db)
        except sqlite3.Error as error:
            raise Unavailable(
                "Stockage indisponible. Réessayez avec la même clé pour une commande."
            ) from error


class SQLiteRepository:
    def __init__(self, db: sqlite3.Connection):
        self.db = db

    @staticmethod
    def decode(body: str) -> Request:
        fields = json.loads(body)
        fields["status"] = Status(fields["status"])
        return Request(**fields)

    def get(self, request_id: str) -> Request | None:
        row = self.db.execute(
            "SELECT body FROM requests WHERE id = ?", (request_id,)
        ).fetchone()
        return self.decode(row[0]) if row is not None else None

    def list(self, owner: str | None, status: Status | None) -> list[Request]:
        rows = self.db.execute(
            "SELECT body FROM requests WHERE (? IS NULL OR owner = ?) "
            "AND (? IS NULL OR status = ?) ORDER BY id",
            (owner, owner, status, status),
        )
        return [self.decode(body) for (body,) in rows]

    def save(self, request: Request) -> None:
        self.db.execute(
            "INSERT INTO requests (id, owner, status, body) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET status = excluded.status, body = excluded.body",
            (request.id, request.owner, request.status, json.dumps(asdict(request))),
        )

    def receipt(self, actor_id: str, key: str) -> Receipt | None:
        row = self.db.execute(
            "SELECT fingerprint, request_id, status FROM receipts "
            "WHERE actor_id = ? AND key = ?",
            (actor_id, key),
        ).fetchone()
        return Receipt(*row) if row is not None else None

    def record(self, actor_id: str, key: str, receipt: Receipt) -> None:
        self.db.execute(
            "INSERT INTO receipts VALUES (?, ?, ?, ?, ?)",
            (actor_id, key, receipt.fingerprint, receipt.request_id, receipt.status),
        )
