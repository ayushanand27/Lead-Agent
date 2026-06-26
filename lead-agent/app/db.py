import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator, Optional

from dotenv import load_dotenv

load_dotenv()

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "leads.db"


def get_db_path() -> Path:
    configured = os.getenv("DATABASE_PATH")
    if configured:
        return Path(configured)
    return DEFAULT_DB_PATH


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    conn = _connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript(
            """
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

            CREATE INDEX IF NOT EXISTS idx_leads_owner_phone
                ON leads(owner_phone);

            CREATE INDEX IF NOT EXISTS idx_leads_owner_status
                ON leads(owner_phone, status);

            CREATE TABLE IF NOT EXISTS action_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_phone TEXT NOT NULL,
                action TEXT NOT NULL,
                details TEXT NOT NULL,
                timestamp TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_action_log_owner_phone
                ON action_log(owner_phone);
            """
        )


def _row_to_dict(row: sqlite3.Row) -> dict:
    return dict(row)


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
    with get_connection() as conn:
        for lead in samples:
            cursor = conn.execute(
                """
                INSERT INTO leads (
                    owner_phone, name, phone, source, status, notes,
                    last_contacted_at, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
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
        WHERE owner_phone = ?
    """
    params: list = [owner_phone]

    if status_filter is not None:
        query += " AND status = ?"
        params.append(status_filter)

    query += " ORDER BY created_at DESC"

    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
    return [_row_to_dict(row) for row in rows]


def fetch_stale_leads(owner_phone: str, days_since_contact: int) -> list[dict]:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days_since_contact)).isoformat()
    query = """
        SELECT id, owner_phone, name, phone, source, status, notes,
               last_contacted_at, created_at
        FROM leads
        WHERE owner_phone = ?
          AND status NOT IN ('converted', 'lost')
          AND (
                last_contacted_at IS NULL
                OR last_contacted_at <= ?
              )
        ORDER BY COALESCE(last_contacted_at, created_at) ASC
    """
    with get_connection() as conn:
        rows = conn.execute(query, (owner_phone, cutoff)).fetchall()
    return [_row_to_dict(row) for row in rows]


def search_leads_for_owner(owner_phone: str, query_text: str) -> list[dict]:
    pattern = f"%{query_text.strip()}%"
    query = """
        SELECT id, owner_phone, name, phone, source, status, notes,
               last_contacted_at, created_at
        FROM leads
        WHERE owner_phone = ?
          AND (
                name LIKE ?
                OR phone LIKE ?
                OR source LIKE ?
                OR IFNULL(notes, '') LIKE ?
              )
        ORDER BY created_at DESC
    """
    params = (owner_phone, pattern, pattern, pattern, pattern)
    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
    return [_row_to_dict(row) for row in rows]


def fetch_lead_by_id(owner_phone: str, lead_id: int) -> Optional[dict]:
    query = """
        SELECT id, owner_phone, name, phone, source, status, notes,
               last_contacted_at, created_at
        FROM leads
        WHERE id = ? AND owner_phone = ?
    """
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
        cursor = conn.execute(
            """
            INSERT INTO leads (
                owner_phone, name, phone, source, status, notes,
                last_contacted_at, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, NULL, ?)
            """,
            (owner_phone, name, phone, source, status, notes, now),
        )
        return int(cursor.lastrowid)


def update_lead_status(owner_phone: str, lead_id: int, new_status: str) -> bool:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE leads
            SET status = ?
            WHERE id = ? AND owner_phone = ?
            """,
            (new_status, lead_id, owner_phone),
        )
        return cursor.rowcount > 0


def append_lead_note(owner_phone: str, lead_id: int, note_line: str) -> bool:
    lead = fetch_lead_by_id(owner_phone, lead_id)
    if lead is None:
        return False

    existing = lead.get("notes") or ""
    if existing:
        updated_notes = f"{existing}\n{note_line}"
    else:
        updated_notes = note_line

    with get_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE leads
            SET notes = ?
            WHERE id = ? AND owner_phone = ?
            """,
            (updated_notes, lead_id, owner_phone),
        )
        return cursor.rowcount > 0


def update_last_contacted_at(owner_phone: str, lead_id: int) -> bool:
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE leads
            SET last_contacted_at = ?
            WHERE id = ? AND owner_phone = ?
            """,
            (now, lead_id, owner_phone),
        )
        return cursor.rowcount > 0


def log_action(owner_phone: str, action: str, details: str) -> int:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO action_log (owner_phone, action, details)
            VALUES (?, ?, ?)
            """,
            (owner_phone, action, details),
        )
        return int(cursor.lastrowid)


def fetch_action_log(owner_phone: str) -> list[dict]:
    query = """
        SELECT id, owner_phone, action, details, timestamp
        FROM action_log
        WHERE owner_phone = ?
        ORDER BY timestamp ASC
    """
    with get_connection() as conn:
        rows = conn.execute(query, (owner_phone,)).fetchall()
    return [_row_to_dict(row) for row in rows]
