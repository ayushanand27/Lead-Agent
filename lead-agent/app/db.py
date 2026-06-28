"""Database layer — Postgres (Supabase) in production, SQLite for local tests."""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator, Optional

from dotenv import load_dotenv

load_dotenv()

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "leads.db"

_POSTGRES_INIT_SQL = """
CREATE TABLE IF NOT EXISTS leads (
    id BIGSERIAL PRIMARY KEY,
    owner_phone TEXT NOT NULL,
    name TEXT NOT NULL,
    phone TEXT NOT NULL,
    source TEXT NOT NULL,
    status TEXT NOT NULL,
    notes TEXT,
    last_contacted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_leads_owner_phone ON leads (owner_phone);
CREATE INDEX IF NOT EXISTS idx_leads_owner_status ON leads (owner_phone, status);

CREATE TABLE IF NOT EXISTS action_log (
    id BIGSERIAL PRIMARY KEY,
    owner_phone TEXT NOT NULL,
    action TEXT NOT NULL,
    details TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_action_log_owner_phone ON action_log (owner_phone);

CREATE TABLE IF NOT EXISTS pending_actions (
    owner_phone TEXT PRIMARY KEY,
    action_json TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE leads ENABLE ROW LEVEL SECURITY;
ALTER TABLE action_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE pending_actions ENABLE ROW LEVEL SECURITY;
"""

_SQLITE_INIT_SQL = """
CREATE TABLE IF NOT EXISTS leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_phone TEXT NOT NULL,
    name TEXT NOT NULL,
    phone TEXT NOT NULL,
    source TEXT NOT NULL,
    status TEXT NOT NULL,
    notes TEXT,
    last_contacted_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_leads_owner_phone ON leads(owner_phone);
CREATE INDEX IF NOT EXISTS idx_leads_owner_status ON leads(owner_phone, status);

CREATE TABLE IF NOT EXISTS action_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_phone TEXT NOT NULL,
    action TEXT NOT NULL,
    details TEXT NOT NULL,
    timestamp TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_action_log_owner_phone ON action_log(owner_phone);

CREATE TABLE IF NOT EXISTS pending_actions (
    owner_phone TEXT PRIMARY KEY,
    action_json TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


def _use_postgres() -> bool:
    return bool(os.getenv("DATABASE_URL"))


def _connect_postgres():
    """Connect to Supabase/Postgres. Use DATABASE_PASSWORD for special chars on Render."""
    import psycopg
    from psycopg.rows import dict_row

    url = os.environ["DATABASE_URL"].strip()
    password = os.getenv("DATABASE_PASSWORD", "").strip()
    kwargs: dict = {"row_factory": dict_row}
    if password:
        kwargs["password"] = password
    return psycopg.connect(url, **kwargs)


def get_db_path() -> Path:
    configured = os.getenv("DATABASE_PATH")
    if configured:
        return Path(configured)
    return DEFAULT_DB_PATH


def _q(query: str) -> str:
    """Normalize placeholders: Postgres uses %s, SQLite uses ?."""
    if _use_postgres():
        return query
    return query.replace("%s", "?")


def _row_to_dict(row: Any) -> dict:
    if row is None:
        return {}
    if isinstance(row, sqlite3.Row):
        return dict(row)
    return dict(row)


@contextmanager
def get_connection() -> Iterator[Any]:
    if _use_postgres():
        import psycopg
        from psycopg.rows import dict_row

        conn = _connect_postgres()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    else:
        conn = sqlite3.connect(get_db_path())
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


def init_db() -> None:
    script = _POSTGRES_INIT_SQL if _use_postgres() else _SQLITE_INIT_SQL
    with get_connection() as conn:
        if _use_postgres():
            for statement in script.split(";"):
                stmt = statement.strip()
                if stmt:
                    conn.execute(stmt)
        else:
            conn.executescript(script)


def check_connection() -> bool:
    """Return True if the database is reachable (used by /health/ready)."""
    try:
        with get_connection() as conn:
            conn.execute(_q("SELECT 1"))
        return True
    except Exception:
        return False


def seed_test_leads(owner_phone: str) -> int:
    """Insert sample leads for local testing. Returns number of rows inserted."""
    now = datetime.now(timezone.utc)
    samples = [
        {
            "name": "Ramesh Patel",
            "phone": "+919876543210",
            "source": "IndiaMART",
            "status": "warm",
            "notes": "Interested in bulk order, asked for price list",
            "last_contacted_at": (now - timedelta(days=3)).isoformat(),
        },
        {
            "name": "Priya Sharma",
            "phone": "+919123456789",
            "source": "WhatsApp",
            "status": "hot",
            "notes": "Ready to place order this week",
            "last_contacted_at": (now - timedelta(hours=6)).isoformat(),
        },
        {
            "name": "Amit Desai",
            "phone": "+919988776655",
            "source": "Referral",
            "status": "new",
            "notes": None,
            "last_contacted_at": None,
        },
        {
            "name": "Sunita Mehta",
            "phone": "+919811223344",
            "source": "Walk-in",
            "status": "contacted",
            "notes": "Visited showroom on Saturday",
            "last_contacted_at": (now - timedelta(days=1)).isoformat(),
        },
        {
            "name": "Vikram Singh",
            "phone": "+919700112233",
            "source": "IndiaMART",
            "status": "converted",
            "notes": "Closed deal for 50 units",
            "last_contacted_at": (now - timedelta(days=10)).isoformat(),
        },
    ]

    inserted = 0
    insert_sql = _q(
        """
        INSERT INTO leads (
            owner_phone, name, phone, source, status, notes,
            last_contacted_at, created_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
    )
    with get_connection() as conn:
        for lead in samples:
            cursor = conn.execute(
                insert_sql,
                (
                    owner_phone,
                    lead["name"],
                    lead["phone"],
                    lead["source"],
                    lead["status"],
                    lead["notes"],
                    lead["last_contacted_at"],
                    now.isoformat(),
                ),
            )
            if cursor.rowcount:
                inserted += 1
    return inserted


def fetch_leads_for_owner(
    owner_phone: str,
    status_filter: Optional[str] = None,
) -> list[dict]:
    query = """
        SELECT id, owner_phone, name, phone, source, status, notes,
               last_contacted_at, created_at
        FROM leads
        WHERE owner_phone = %s
    """
    params: list[Any] = [owner_phone]

    if status_filter is not None:
        query += " AND status = %s"
        params.append(status_filter)

    query += " ORDER BY created_at DESC"

    with get_connection() as conn:
        rows = conn.execute(_q(query), params).fetchall()
    return [_row_to_dict(row) for row in rows]


def fetch_stale_leads(owner_phone: str, days_since_contact: int) -> list[dict]:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days_since_contact)).isoformat()
    query = _q(
        """
        SELECT id, owner_phone, name, phone, source, status, notes,
               last_contacted_at, created_at
        FROM leads
        WHERE owner_phone = %s
          AND status NOT IN ('converted', 'lost')
          AND (
                last_contacted_at IS NULL
                OR last_contacted_at <= %s
              )
        ORDER BY COALESCE(last_contacted_at, created_at) ASC
        """
    )
    with get_connection() as conn:
        rows = conn.execute(query, (owner_phone, cutoff)).fetchall()
    return [_row_to_dict(row) for row in rows]


def search_leads_for_owner(owner_phone: str, query_text: str) -> list[dict]:
    pattern = f"%{query_text.strip()}%"
    if _use_postgres():
        notes_expr = "COALESCE(notes, '')"
    else:
        notes_expr = "IFNULL(notes, '')"

    query = _q(
        f"""
        SELECT id, owner_phone, name, phone, source, status, notes,
               last_contacted_at, created_at
        FROM leads
        WHERE owner_phone = %s
          AND (
                name LIKE %s
                OR phone LIKE %s
                OR source LIKE %s
                OR {notes_expr} LIKE %s
              )
        ORDER BY created_at DESC
        """
    )
    params = (owner_phone, pattern, pattern, pattern, pattern)
    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
    return [_row_to_dict(row) for row in rows]


def fetch_lead_by_id(owner_phone: str, lead_id: int) -> Optional[dict]:
    query = _q(
        """
        SELECT id, owner_phone, name, phone, source, status, notes,
               last_contacted_at, created_at
        FROM leads
        WHERE id = %s AND owner_phone = %s
        """
    )
    with get_connection() as conn:
        row = conn.execute(query, (lead_id, owner_phone)).fetchone()
    return _row_to_dict(row) if row else None


def insert_lead(
    owner_phone: str,
    name: str,
    phone: str,
    source: str,
    notes: Optional[str] = None,
    status: str = "new",
) -> int:
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        if _use_postgres():
            row = conn.execute(
                _q(
                    """
                    INSERT INTO leads (
                        owner_phone, name, phone, source, status, notes,
                        last_contacted_at, created_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, NULL, %s)
                    RETURNING id
                    """
                ),
                (owner_phone, name, phone, source, status, notes, now),
            ).fetchone()
            return int(row["id"])

        cursor = conn.execute(
            _q(
                """
                INSERT INTO leads (
                    owner_phone, name, phone, source, status, notes,
                    last_contacted_at, created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, NULL, %s)
                """
            ),
            (owner_phone, name, phone, source, status, notes, now),
        )
        return int(cursor.lastrowid)


def update_lead_status(owner_phone: str, lead_id: int, new_status: str) -> bool:
    with get_connection() as conn:
        cursor = conn.execute(
            _q(
                """
                UPDATE leads
                SET status = %s
                WHERE id = %s AND owner_phone = %s
                """
            ),
            (new_status, lead_id, owner_phone),
        )
        return cursor.rowcount > 0


def append_lead_note(owner_phone: str, lead_id: int, note_line: str) -> bool:
    lead = fetch_lead_by_id(owner_phone, lead_id)
    if lead is None:
        return False

    existing = lead.get("notes") or ""
    updated_notes = f"{existing}\n{note_line}" if existing else note_line

    with get_connection() as conn:
        cursor = conn.execute(
            _q(
                """
                UPDATE leads
                SET notes = %s
                WHERE id = %s AND owner_phone = %s
                """
            ),
            (updated_notes, lead_id, owner_phone),
        )
        return cursor.rowcount > 0


def update_last_contacted_at(owner_phone: str, lead_id: int) -> bool:
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        cursor = conn.execute(
            _q(
                """
                UPDATE leads
                SET last_contacted_at = %s
                WHERE id = %s AND owner_phone = %s
                """
            ),
            (now, lead_id, owner_phone),
        )
        return cursor.rowcount > 0


def log_action(owner_phone: str, action: str, details: str) -> int:
    with get_connection() as conn:
        if _use_postgres():
            row = conn.execute(
                _q(
                    """
                    INSERT INTO action_log (owner_phone, action, details)
                    VALUES (%s, %s, %s)
                    RETURNING id
                    """
                ),
                (owner_phone, action, details),
            ).fetchone()
            return int(row["id"])

        cursor = conn.execute(
            _q(
                """
                INSERT INTO action_log (owner_phone, action, details)
                VALUES (%s, %s, %s)
                """
            ),
            (owner_phone, action, details),
        )
        return int(cursor.lastrowid)


def fetch_action_log(owner_phone: str, limit: int | None = None) -> list[dict]:
    query = _q(
        """
        SELECT id, owner_phone, action, details, timestamp
        FROM action_log
        WHERE owner_phone = %s
        ORDER BY timestamp DESC
        """
    )
    if limit is not None:
        query += _q(" LIMIT %s")
        params: tuple[Any, ...] = (owner_phone, limit)
    else:
        params = (owner_phone,)

    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
    items = [_row_to_dict(row) for row in rows]
    if limit is None:
        items.reverse()
    return items


def fetch_lead_stats(owner_phone: str) -> dict[str, Any]:
    with get_connection() as conn:
        total_row = conn.execute(
            _q("SELECT COUNT(*) AS c FROM leads WHERE owner_phone = %s"),
            (owner_phone,),
        ).fetchone()
        status_rows = conn.execute(
            _q(
                """
                SELECT status, COUNT(*) AS c
                FROM leads
                WHERE owner_phone = %s
                GROUP BY status
                """
            ),
            (owner_phone,),
        ).fetchall()

    total = int(total_row["c"] if isinstance(total_row, dict) else total_row[0])
    by_status = {str(r["status"]): int(r["c"]) for r in status_rows}
    return {"total": total, "by_status": by_status}


def upsert_pending_action(owner_phone: str, action_dict: dict[str, Any]) -> None:
    import json

    payload = json.dumps(action_dict)
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        if _use_postgres():
            conn.execute(
                _q(
                    """
                    INSERT INTO pending_actions (owner_phone, action_json, updated_at)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (owner_phone)
                    DO UPDATE SET action_json = EXCLUDED.action_json, updated_at = EXCLUDED.updated_at
                    """
                ),
                (owner_phone, payload, now),
            )
        else:
            conn.execute(
                _q(
                    """
                    INSERT INTO pending_actions (owner_phone, action_json, updated_at)
                    VALUES (%s, %s, %s)
                    ON CONFLICT(owner_phone) DO UPDATE SET
                        action_json = excluded.action_json,
                        updated_at = excluded.updated_at
                    """
                ),
                (owner_phone, payload, now),
            )


def fetch_pending_action(owner_phone: str) -> Optional[dict[str, Any]]:
    import json

    with get_connection() as conn:
        row = conn.execute(
            _q("SELECT action_json FROM pending_actions WHERE owner_phone = %s"),
            (owner_phone,),
        ).fetchone()
    if not row:
        return None
    raw = row["action_json"] if isinstance(row, dict) else row[0]
    return json.loads(raw)


def delete_pending_action(owner_phone: str) -> None:
    with get_connection() as conn:
        conn.execute(
            _q("DELETE FROM pending_actions WHERE owner_phone = %s"),
            (owner_phone,),
        )
