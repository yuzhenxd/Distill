import json
import sqlite3
import uuid
from datetime import datetime

from .paths import data_dir

DB_FILE = data_dir() / "meetings.db"


class MeetingStore:
    """会议记录的 SQLite 持久化。只在主线程使用。"""

    def __init__(self, path=DB_FILE):
        self.conn = sqlite3.connect(str(path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS meetings (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                source TEXT,
                created_at TEXT NOT NULL,
                transcript TEXT,
                result TEXT NOT NULL
            )"""
        )
        self.conn.commit()

    def create(self, title: str, source: str, transcript: str, result: dict) -> dict:
        meeting = {
            "id": uuid.uuid4().hex,
            "title": title,
            "source": source,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "transcript": transcript,
            "result": result,
        }
        self.conn.execute(
            "INSERT INTO meetings (id, title, source, created_at, transcript, result) VALUES (?, ?, ?, ?, ?, ?)",
            (
                meeting["id"],
                title,
                source,
                meeting["created_at"],
                transcript,
                json.dumps(result, ensure_ascii=False),
            ),
        )
        self.conn.commit()
        return meeting

    def update(self, meeting: dict) -> None:
        self.conn.execute(
            "UPDATE meetings SET title = ?, transcript = ?, result = ? WHERE id = ?",
            (
                meeting["title"],
                meeting["transcript"],
                json.dumps(meeting["result"], ensure_ascii=False),
                meeting["id"],
            ),
        )
        self.conn.commit()

    def get(self, meeting_id: str) -> dict | None:
        row = self.conn.execute("SELECT * FROM meetings WHERE id = ?", (meeting_id,)).fetchone()
        if row is None:
            return None
        meeting = dict(row)
        meeting["result"] = json.loads(meeting["result"])
        return meeting

    def list(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT id, title, created_at FROM meetings ORDER BY created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    def delete(self, meeting_id: str) -> None:
        self.conn.execute("DELETE FROM meetings WHERE id = ?", (meeting_id,))
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()
