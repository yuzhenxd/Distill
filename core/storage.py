import json
import shutil
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

DB_NAME = "meetings.db"


def relocate(old_dir: str, new_dir: str) -> bool:
    """把数据库从旧文件夹移到新文件夹。新文件夹里已有数据库时不移动、直接沿用它，返回 True。"""
    src, dst = Path(old_dir) / DB_NAME, Path(new_dir) / DB_NAME
    if dst.exists():
        return True
    if src.exists():
        shutil.move(src, dst)  # 跨磁盘时先复制再删除
    return False


class MeetingStore:
    """会议记录的 SQLite 持久化。只在主线程使用。"""

    def __init__(self, folder: str):
        self.conn = sqlite3.connect(str(Path(folder) / DB_NAME))
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
