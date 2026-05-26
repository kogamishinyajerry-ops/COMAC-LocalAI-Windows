import sqlite3
from datetime import datetime
from dataclasses import dataclass
from typing import List

@dataclass
class TaskRecord:
    task_id: str
    input_path: str
    output_path: str
    operation: str
    status: str
    duration: float
    created_at: str

class TaskHistory:
    def __init__(self, db_path: str = "task_history.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS task_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT,
                input_path TEXT,
                output_path TEXT,
                operation TEXT,
                status TEXT,
                duration REAL,
                created_at TEXT
            )
        """)
        conn.commit()
        conn.close()

    def add_record(self, task):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT INTO task_history
            (task_id, input_path, output_path, operation, status, duration, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            task.task_id,
            task.input_path,
            task.output_path,
            "document_processing",
            task.status.value,
            (task.end_time - task.start_time) if task.end_time and task.start_time else 0,
            datetime.now().isoformat()
        ))
        conn.commit()
        conn.close()

    def get_recent(self, limit: int = 50) -> list:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "SELECT * FROM task_history ORDER BY created_at DESC LIMIT ?",
            (limit,)
        )
        records = [dict(zip([col[0] for col in cursor.description], row)) for row in cursor]
        conn.close()
        return records
