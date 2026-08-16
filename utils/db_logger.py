"""
SQLite logger for user–assistant interactions (PEcf09 metrics).

Stores anonymized metrics for /stats and CSV export. Do not log secrets or PII.
"""

from __future__ import annotations

import csv
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from config import BASE_DIR, DATA_DIR


class DatabaseLogger:
    """Persist interactions for metrics: latency, cache hits, query volume."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        DATA_DIR.mkdir(exist_ok=True)
        self.db_path = Path(db_path or DATA_DIR / "logs.db")
        self._init_database()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init_database(self) -> None:
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                user_id TEXT,
                username TEXT,
                source TEXT NOT NULL,
                query TEXT NOT NULL,
                response TEXT NOT NULL,
                from_cache INTEGER DEFAULT 0,
                response_time_ms INTEGER,
                mode TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_user_id ON logs(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_source ON logs(source)")
        conn.commit()
        conn.close()

    @staticmethod
    def _clip(text: str, max_len: int = 2000) -> str:
        value = (text or "").strip()
        if len(value) <= max_len:
            return value
        return value[: max_len - 1] + "…"

    def log_interaction(
        self,
        query: str,
        response: str,
        source: str = "telegram",
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        from_cache: bool = False,
        response_time_ms: Optional[int] = None,
        mode: Optional[str] = None,
    ) -> None:
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO logs (
                timestamp, user_id, username, source, query, response,
                from_cache, response_time_ms, mode
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now().isoformat(timespec="seconds"),
                str(user_id) if user_id is not None else None,
                self._clip(username or "", 64) or None,
                source,
                self._clip(query),
                self._clip(response),
                1 if from_cache else 0,
                response_time_ms,
                mode,
            ),
        )
        conn.commit()
        conn.close()

    def get_stats(self, hours: int = 24) -> dict[str, Any]:
        conn = self._connect()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM logs")
        total = int(cursor.fetchone()[0] or 0)

        cursor.execute("SELECT COUNT(*) FROM logs WHERE from_cache = 1")
        cached = int(cursor.fetchone()[0] or 0)

        cursor.execute(
            "SELECT AVG(response_time_ms) FROM logs WHERE response_time_ms IS NOT NULL"
        )
        avg_row = cursor.fetchone()[0]
        avg_ms = int(round(avg_row)) if avg_row is not None else None

        cursor.execute(
            """
            SELECT response_time_ms FROM logs
            WHERE response_time_ms IS NOT NULL
            ORDER BY response_time_ms
            """
        )
        times = [int(row[0]) for row in cursor.fetchall()]
        median_ms = None
        if times:
            mid = len(times) // 2
            if len(times) % 2:
                median_ms = times[mid]
            else:
                median_ms = int(round((times[mid - 1] + times[mid]) / 2))

        since = (datetime.now() - timedelta(hours=hours)).isoformat(timespec="seconds")
        cursor.execute("SELECT COUNT(*) FROM logs WHERE timestamp >= ?", (since,))
        last_period = int(cursor.fetchone()[0] or 0)

        conn.close()

        cache_rate = round((cached / total) * 100, 1) if total else 0.0
        return {
            "total_requests": total,
            "cached_requests": cached,
            "cache_hit_rate_pct": cache_rate,
            "avg_response_time_ms": avg_ms,
            "median_response_time_ms": median_ms,
            "requests_last_hours": last_period,
            "hours_window": hours,
            "db_path": str(self.db_path),
        }

    def export_csv(self, output_path: Optional[Path] = None) -> Path:
        path = Path(output_path or BASE_DIR / "logs_export.csv")
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, timestamp, user_id, source, mode, from_cache,
                   response_time_ms, query, response
            FROM logs
            ORDER BY id
            """
        )
        rows = cursor.fetchall()
        conn.close()

        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(
                [
                    "id",
                    "timestamp",
                    "user_id",
                    "source",
                    "mode",
                    "from_cache",
                    "response_time_ms",
                    "query",
                    "response",
                ]
            )
            writer.writerows(rows)
        return path


db_logger = DatabaseLogger()
