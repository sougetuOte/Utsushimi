"""記憶：SQLite（ADR 0002）。接続は核のスレッドだけが持つ（ADR 0004）。

会話の記録は「足す」口だけを持ち、書き換える口を持たない（design.md §2）。
"""
import sqlite3
from datetime import datetime
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS utterances(
    id INTEGER PRIMARY KEY,
    at TEXT NOT NULL,
    speaker TEXT NOT NULL,   -- master / companion
    body TEXT NOT NULL,
    kind TEXT NOT NULL       -- dialogue（段1の後のタスクで poke / trial を足す）
);
CREATE TABLE IF NOT EXISTS lifecycle(
    id INTEGER PRIMARY KEY,
    pid INTEGER NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    via TEXT
);
"""


def _now():
    return datetime.now().isoformat(timespec="milliseconds")


class Memory:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.executescript(SCHEMA)
        self.db.commit()
        self.session = None

    def begin_session(self, pid: int) -> str:
        """起動を記録し、前回の終わり方（clean / unclean / none）を返す。"""
        row = self.db.execute("SELECT ended_at FROM lifecycle ORDER BY id DESC LIMIT 1").fetchone()
        prev = "none" if row is None else ("clean" if row[0] else "unclean")
        cur = self.db.execute("INSERT INTO lifecycle(pid, started_at) VALUES(?, ?)", (pid, _now()))
        self.db.commit()
        self.session = cur.lastrowid
        return prev

    def end_session(self, via: str):
        self.db.execute("UPDATE lifecycle SET ended_at = ?, via = ? WHERE id = ?", (_now(), via, self.session))
        self.db.commit()

    def add_utterance(self, speaker: str, body: str, kind: str = "dialogue") -> int:
        """1発言を足して、その場でコミットする（記憶を失わない）。"""
        cur = self.db.execute(
            "INSERT INTO utterances(at, speaker, body, kind) VALUES(?, ?, ?, ?)", (_now(), speaker, body, kind))
        self.db.commit()
        return cur.lastrowid

    def utterances(self, limit: int | None = None) -> list[tuple[str, str]]:
        """古い順の (speaker, body)。limit を渡すと直近の limit 件。"""
        if limit is None:
            rows = self.db.execute("SELECT speaker, body FROM utterances ORDER BY id").fetchall()
        else:
            rows = self.db.execute(
                "SELECT speaker, body FROM utterances ORDER BY id DESC LIMIT ?", (limit,)).fetchall()[::-1]
        return rows

    def close(self):
        self.db.close()
