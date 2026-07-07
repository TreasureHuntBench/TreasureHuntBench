"""SQLite database artifacts."""

import os
import sqlite3
from typing import Any, Dict, List, Sequence


def write_sqlite(path: str, table: str, columns: Sequence[str],
                 rows: Sequence[Sequence[Any]]) -> str:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    if os.path.exists(path):
        os.remove(path)
    conn = sqlite3.connect(path)
    try:
        col_defs = ", ".join('"%s" TEXT' % c for c in columns)
        conn.execute('CREATE TABLE "%s" (%s)' % (table, col_defs))
        placeholders = ", ".join("?" for _ in columns)
        conn.executemany(
            'INSERT INTO "%s" VALUES (%s)' % (table, placeholders),
            [[str(v) for v in row] for row in rows])
        conn.commit()
    finally:
        conn.close()
    return path


def query_sqlite(path: str, sql: str, params: Sequence[Any] = ()
                 ) -> List[Dict[str, Any]]:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()
