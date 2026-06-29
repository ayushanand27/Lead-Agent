"""Database layer — Postgres (Supabase) in production, SQLite for local tests."""

from __future__ import annotations

import os
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator, Optional

from dotenv import load_dotenv

from app.config import get_owner_scope
from app.text_normalize import latin_tokens, search_query_variants

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
    consent_source TEXT,
    consent_at TIMESTAMPTZ,
    tags TEXT,
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
    consent_source TEXT,
    consent_at TEXT,
    tags TEXT,
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
            _apply_schema_migrations(conn)
        else:
            conn.executescript(script)
            _apply_schema_migrations(conn)


def _apply_schema_migrations(conn: Any) -> None:
    """Add columns safely on existing databases."""
    if _use_postgres():
        conn.execute("ALTER TABLE leads ADD COLUMN IF NOT EXISTS consent_source TEXT")
        conn.execute("ALTER TABLE leads ADD COLUMN IF NOT EXISTS consent_at TIMESTAMPTZ")
        conn.execute("ALTER TABLE leads ADD COLUMN IF NOT EXISTS tags TEXT")
        return

    columns = {
        row[1] if not isinstance(row, dict) else row["name"]
        for row in conn.execute("PRAGMA table_info(leads)").fetchall()
    }
    if "consent_source" not in columns:
        conn.execute("ALTER TABLE leads ADD COLUMN consent_source TEXT")
    if "consent_at" not in columns:
        conn.execute("ALTER TABLE leads ADD COLUMN consent_at TEXT")
    if "tags" not in columns:
        conn.execute("ALTER TABLE leads ADD COLUMN tags TEXT")


def _scope_sql(acting_phone: str, column: str = "owner_phone") -> tuple[str, list[str]]:
    scope = get_owner_scope(acting_phone)
    if len(scope) == 1:
        return f"{column} = %s", scope
    placeholders = ", ".join("%s" for _ in scope)
    return f"{column} IN ({placeholders})", scope


_LEAD_COLUMNS = (
    "id, owner_phone, name, phone, source, status, notes, tags, "
    "last_contacted_at, consent_source, consent_at, created_at"
)


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
    source_filter: Optional[str] = None,
) -> list[dict]:
    scope_clause, scope_params = _scope_sql(owner_phone)
    query = f"""
        SELECT {_LEAD_COLUMNS}
        FROM leads
        WHERE {scope_clause}
    """
    params: list[Any] = list(scope_params)

    if status_filter is not None:
        query += " AND status = %s"
        params.append(status_filter)

    if source_filter is not None:
        query += " AND source = %s"
        params.append(source_filter)

    query += " ORDER BY created_at DESC"

    with get_connection() as conn:
        rows = conn.execute(_q(query), params).fetchall()
    return [_row_to_dict(row) for row in rows]


def fetch_stale_leads(owner_phone: str, days_since_contact: int) -> list[dict]:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days_since_contact)).isoformat()
    scope_clause, scope_params = _scope_sql(owner_phone)
    query = _q(
        f"""
        SELECT {_LEAD_COLUMNS}
        FROM leads
        WHERE {scope_clause}
          AND status NOT IN ('converted', 'lost')
          AND (
                last_contacted_at IS NULL
                OR last_contacted_at <= %s
              )
        ORDER BY COALESCE(last_contacted_at, created_at) ASC
        """
    )
    with get_connection() as conn:
        rows = conn.execute(query, (*scope_params, cutoff)).fetchall()
    return [_row_to_dict(row) for row in rows]


def search_leads_for_owner(owner_phone: str, query_text: str) -> list[dict]:
    query = query_text.strip()
    if not query:
        return []

    for variant in search_query_variants(query):
        hits = _sql_search_phrase(owner_phone, variant)
        if hits:
            return hits

    tokens = latin_tokens(query)
    if tokens:
        hits = _sql_search_name_tokens(owner_phone, tokens)
        if hits:
            return hits

    return _fuzzy_scan_leads(owner_phone, tokens or [query])


def _sql_search_phrase(owner_phone: str, phrase: str) -> list[dict]:
    pattern = f"%{phrase.strip()}%"
    like_op = "ILIKE" if _use_postgres() else "LIKE"
    if _use_postgres():
        notes_expr = "COALESCE(notes, '')"
        tags_expr = "COALESCE(tags, '')"
    else:
        notes_expr = "IFNULL(notes, '')"
        tags_expr = "IFNULL(tags, '')"

    scope_clause, scope_params = _scope_sql(owner_phone)
    query = _q(
        f"""
        SELECT {_LEAD_COLUMNS}
        FROM leads
        WHERE {scope_clause}
          AND (
                name {like_op} %s
                OR phone {like_op} %s
                OR source {like_op} %s
                OR {notes_expr} {like_op} %s
                OR {tags_expr} {like_op} %s
              )
        ORDER BY created_at DESC
        """
    )
    params = (*scope_params, pattern, pattern, pattern, pattern, pattern)
    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
    return [_row_to_dict(row) for row in rows]


def _sql_search_name_tokens(owner_phone: str, tokens: list[str]) -> list[dict]:
    if not tokens:
        return []

    like_op = "ILIKE" if _use_postgres() else "LIKE"
    scope_clause, scope_params = _scope_sql(owner_phone)
    name_checks = " AND ".join(f"name {like_op} %s" for _ in tokens)
    params: list[Any] = list(scope_params)
    for token in tokens:
        params.append(f"%{token}%")

    query = _q(
        f"""
        SELECT {_LEAD_COLUMNS}
        FROM leads
        WHERE {scope_clause}
          AND ({name_checks})
        ORDER BY created_at DESC
        """
    )
    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
    return [_row_to_dict(row) for row in rows]


def _fuzzy_scan_leads(owner_phone: str, tokens: list[str]) -> list[dict]:
    """Last resort — scan scoped leads when script or encoding breaks SQL match."""
    if not tokens:
        return []

    leads = fetch_leads_for_owner(owner_phone)
    matches: list[dict] = []
    for lead in leads:
        name_lower = str(lead.get("name", "")).lower()
        name_parts = re.findall(r"[a-z]{2,}", name_lower)
        hits = 0
        for token in tokens:
            token = token.lower()
            if token in name_lower:
                hits += 1
                continue
            for part in name_parts:
                if part.startswith(token[:3]) or token.startswith(part[:3]):
                    hits += 1
                    break
        if hits >= 1 and hits >= min(len(tokens), 1):
            matches.append(lead)
    return matches


def fetch_lead_by_id(owner_phone: str, lead_id: int) -> Optional[dict]:
    scope_clause, scope_params = _scope_sql(owner_phone)
    query = _q(
        f"""
        SELECT {_LEAD_COLUMNS}
        FROM leads
        WHERE id = %s AND {scope_clause}
        """
    )
    with get_connection() as conn:
        row = conn.execute(query, (lead_id, *scope_params)).fetchone()
    return _row_to_dict(row) if row else None


def insert_lead(
    owner_phone: str,
    name: str,
    phone: str,
    source: str,
    notes: Optional[str] = None,
    status: str = "new",
    consent_source: Optional[str] = None,
    tags: Optional[str] = None,
) -> int:
    now = datetime.now(timezone.utc).isoformat()
    consent_at = now if consent_source else None
    normalized_tags = _normalize_tags(tags) if tags else None
    with get_connection() as conn:
        if _use_postgres():
            row = conn.execute(
                _q(
                    """
                    INSERT INTO leads (
                        owner_phone, name, phone, source, status, notes, tags,
                        last_contacted_at, consent_source, consent_at, created_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, NULL, %s, %s, %s)
                    RETURNING id
                    """
                ),
                (
                    owner_phone,
                    name,
                    phone,
                    source,
                    status,
                    notes,
                    normalized_tags,
                    consent_source,
                    consent_at,
                    now,
                ),
            ).fetchone()
            return int(row["id"])

        cursor = conn.execute(
            _q(
                """
                INSERT INTO leads (
                    owner_phone, name, phone, source, status, notes, tags,
                    last_contacted_at, consent_source, consent_at, created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, NULL, %s, %s, %s)
                """
            ),
            (
                owner_phone,
                name,
                phone,
                source,
                status,
                notes,
                normalized_tags,
                consent_source,
                consent_at,
                now,
            ),
        )
        return int(cursor.lastrowid)


def _normalize_tags(raw: str) -> str:
    parts = [t.strip().lower() for t in raw.split(",") if t.strip()]
    return ", ".join(dict.fromkeys(parts))


def update_lead_status(owner_phone: str, lead_id: int, new_status: str) -> bool:
    scope_clause, scope_params = _scope_sql(owner_phone)
    with get_connection() as conn:
        cursor = conn.execute(
            _q(
                f"""
                UPDATE leads
                SET status = %s
                WHERE id = %s AND {scope_clause}
                """
            ),
            (new_status, lead_id, *scope_params),
        )
        return cursor.rowcount > 0


def update_lead_fields(
    owner_phone: str,
    lead_id: int,
    *,
    status: Optional[str] = None,
    notes: Optional[str] = None,
    tags: Optional[str] = None,
) -> bool:
    lead = fetch_lead_by_id(owner_phone, lead_id)
    if lead is None:
        return False

    fields: list[str] = []
    values: list[Any] = []
    if status is not None:
        fields.append("status = %s")
        values.append(status)
    if notes is not None:
        fields.append("notes = %s")
        values.append(notes)
    if tags is not None:
        fields.append("tags = %s")
        values.append(_normalize_tags(tags) if tags else None)

    if not fields:
        return True

    scope_clause, scope_params = _scope_sql(owner_phone)
    values.extend([lead_id, *scope_params])
    with get_connection() as conn:
        cursor = conn.execute(
            _q(f"UPDATE leads SET {', '.join(fields)} WHERE id = %s AND {scope_clause}"),
            values,
        )
        return cursor.rowcount > 0


def append_lead_tags(owner_phone: str, lead_id: int, new_tags: str) -> bool:
    lead = fetch_lead_by_id(owner_phone, lead_id)
    if lead is None:
        return False

    existing = lead.get("tags") or ""
    merged = _normalize_tags(f"{existing}, {new_tags}" if existing else new_tags)
    return update_lead_fields(owner_phone, lead_id, tags=merged)


def append_lead_note(owner_phone: str, lead_id: int, note_line: str) -> bool:
    lead = fetch_lead_by_id(owner_phone, lead_id)
    if lead is None:
        return False

    existing = lead.get("notes") or ""
    updated_notes = f"{existing}\n{note_line}" if existing else note_line

    scope_clause, scope_params = _scope_sql(owner_phone)
    with get_connection() as conn:
        cursor = conn.execute(
            _q(
                f"""
                UPDATE leads
                SET notes = %s
                WHERE id = %s AND {scope_clause}
                """
            ),
            (updated_notes, lead_id, *scope_params),
        )
        return cursor.rowcount > 0


def update_last_contacted_at(owner_phone: str, lead_id: int) -> bool:
    now = datetime.now(timezone.utc).isoformat()
    scope_clause, scope_params = _scope_sql(owner_phone)
    with get_connection() as conn:
        cursor = conn.execute(
            _q(
                f"""
                UPDATE leads
                SET last_contacted_at = %s
                WHERE id = %s AND {scope_clause}
                """
            ),
            (now, lead_id, *scope_params),
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
    scope_clause, scope_params = _scope_sql(owner_phone)
    query = _q(
        f"""
        SELECT id, owner_phone, action, details, timestamp
        FROM action_log
        WHERE {scope_clause}
        ORDER BY timestamp DESC
        """
    )
    if limit is not None:
        query += _q(" LIMIT %s")
        params: tuple[Any, ...] = (*scope_params, limit)
    else:
        params = tuple(scope_params)

    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
    items = [_row_to_dict(row) for row in rows]
    if limit is None:
        items.reverse()
    return items


def fetch_lead_stats(owner_phone: str) -> dict[str, Any]:
    scope_clause, scope_params = _scope_sql(owner_phone)
    with get_connection() as conn:
        total_row = conn.execute(
            _q(f"SELECT COUNT(*) AS c FROM leads WHERE {scope_clause}"),
            scope_params,
        ).fetchone()
        status_rows = conn.execute(
            _q(
                f"""
                SELECT status, COUNT(*) AS c
                FROM leads
                WHERE {scope_clause}
                GROUP BY status
                """
            ),
            scope_params,
        ).fetchall()

    total = int(total_row["c"] if isinstance(total_row, dict) else total_row[0])
    by_status = {str(r["status"]): int(r["c"]) for r in status_rows}
    return {"total": total, "by_status": by_status}


def fetch_lead_sources(owner_phone: str) -> list[str]:
    scope_clause, scope_params = _scope_sql(owner_phone)
    with get_connection() as conn:
        rows = conn.execute(
            _q(
                f"""
                SELECT DISTINCT source
                FROM leads
                WHERE {scope_clause}
                ORDER BY source ASC
                """
            ),
            scope_params,
        ).fetchall()
    return [str(r["source"]) for r in rows if r["source"]]


def fetch_analytics(owner_phone: str, days: int = 14) -> dict[str, Any]:
    stats = fetch_lead_stats(owner_phone)
    total = stats["total"]
    by_status = stats["by_status"]
    converted = by_status.get("converted", 0)
    lost = by_status.get("lost", 0)
    active = total - converted - lost
    conversion_rate = round((converted / total * 100) if total else 0, 1)

    scope_clause, scope_params = _scope_sql(owner_phone)
    with get_connection() as conn:
        source_rows = conn.execute(
            _q(
                f"""
                SELECT source, COUNT(*) AS c
                FROM leads
                WHERE {scope_clause}
                GROUP BY source
                ORDER BY c DESC
                """
            ),
            scope_params,
        ).fetchall()

        if _use_postgres():
            day_expr = "DATE(created_at)"
        else:
            day_expr = "date(created_at)"

        cutoff = (datetime.now(timezone.utc) - timedelta(days=days - 1)).date().isoformat()
        day_rows = conn.execute(
            _q(
                f"""
                SELECT {day_expr} AS day, COUNT(*) AS c
                FROM leads
                WHERE {scope_clause}
                  AND {day_expr} >= %s
                GROUP BY {day_expr}
                ORDER BY day ASC
                """
            ),
            (*scope_params, cutoff),
        ).fetchall()

    by_source = {str(r["source"]): int(r["c"]) for r in source_rows}
    leads_by_day = [
        {"day": str(r["day"]), "count": int(r["c"])}
        for r in day_rows
    ]

    return {
        "total": total,
        "active": active,
        "converted": converted,
        "lost": lost,
        "conversion_rate": conversion_rate,
        "by_status": by_status,
        "by_source": by_source,
        "leads_by_day": leads_by_day,
        "days": days,
    }


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
