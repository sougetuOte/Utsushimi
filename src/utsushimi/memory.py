"""記憶：SQLite（ADR 0002）。接続は核のスレッドだけが持つ（ADR 0004）。

会話の記録と日記は「足す」口だけを持ち、書き換える口を持たない（design.md §2）。
時刻は `_now()` と同じ ISO 形式の文字列で渡し、文字列のまま比べる。
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
    kind TEXT NOT NULL       -- dialogue / trial（キャラ作りのお試し）。突っつき poke は T7 で足す
);
CREATE TABLE IF NOT EXISTS lifecycle(
    id INTEGER PRIMARY KEY,
    pid INTEGER NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    via TEXT
);
CREATE TABLE IF NOT EXISTS diaries(
    id INTEGER PRIMARY KEY,
    date TEXT NOT NULL UNIQUE,  -- 同じ日を2度作らない（Bug-5）
    body TEXT NOT NULL,
    at TEXT NOT NULL
);
CREATE VIRTUAL TABLE IF NOT EXISTS utterances_fts USING fts5(
    body, content='utterances', content_rowid='id', tokenize='trigram');
CREATE TRIGGER IF NOT EXISTS utterances_fts_add AFTER INSERT ON utterances BEGIN
    INSERT INTO utterances_fts(rowid, body) VALUES (new.id, new.body);
END;
CREATE TABLE IF NOT EXISTS persona_seal(
    id INTEGER PRIMARY KEY,
    at TEXT NOT NULL,
    core_sha TEXT NOT NULL,
    style_sha TEXT NOT NULL
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
        indexed = self.db.execute("SELECT 1 FROM sqlite_master WHERE name = 'utterances_fts'").fetchone()
        self.db.executescript(SCHEMA)
        if not indexed:  # T4 より前に作った DB：それまでの発言も検索に入れる
            self.db.execute("INSERT INTO utterances_fts(utterances_fts) VALUES('rebuild')")
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

    def utterances(self, limit: int | None = None, kind: str = "dialogue", after: int = 0) -> list[tuple[str, str]]:
        """古い順の (speaker, body)。種類が kind で、番号が after より後のものだけ。limit を渡すと直近の limit 件。"""
        if limit is None:
            rows = self.db.execute("SELECT speaker, body FROM utterances WHERE kind = ? AND id > ? ORDER BY id",
                                   (kind, after)).fetchall()
        else:
            rows = self.db.execute(
                "SELECT speaker, body FROM utterances WHERE kind = ? AND id > ? ORDER BY id DESC LIMIT ?",
                (kind, after, limit)).fetchall()[::-1]
        return rows

    def since(self, start: str, end: str | None = None) -> list[tuple[int, str, str]]:
        """時刻が start 以降（end があれば end より前）の dialogue の発言。古い順の (番号, speaker, body)。"""
        return self.db.execute(
            "SELECT id, speaker, body FROM utterances WHERE kind = 'dialogue' AND at >= ? AND at < ? ORDER BY id",
            (start, end or "9999")).fetchall()

    def recall(self, query: str, before: str, limit: int) -> list[tuple[int, str, str, str]]:
        """FTS5 で、時刻が before より前の dialogue の発言を bm25 の上位 limit 件引く。番号の古い順の (番号, at, speaker, body)。"""
        rows = self.db.execute(
            "SELECT u.id, u.at, u.speaker, u.body FROM utterances_fts JOIN utterances u ON u.id = utterances_fts.rowid"
            " WHERE utterances_fts MATCH ? AND u.kind = 'dialogue' AND u.at < ? ORDER BY utterances_fts.rank LIMIT ?",
            (query, before, limit)).fetchall()
        return sorted(rows)

    def missing_diary(self, shift: str, before: str) -> str | None:
        """時刻が before より前の dialogue の発言があって、日記の無い日のうち最も古い日付。

        shift は発言の時刻から1日の区切りを引く SQLite の修飾子（例 '-0 minutes'）。
        """
        row = self.db.execute(
            "SELECT DISTINCT date(at, ?) AS d FROM utterances WHERE kind = 'dialogue' AND at < ?"
            " AND d NOT IN (SELECT date FROM diaries) ORDER BY d LIMIT 1", (shift, before)).fetchone()
        return row and row[0]

    def add_diary(self, date: str, body: str) -> bool:
        """日記を1日分足す。その日の日記がすでにあれば足さずに False を返す。"""
        cur = self.db.execute("INSERT OR IGNORE INTO diaries(date, body, at) VALUES(?, ?, ?)", (date, body, _now()))
        self.db.commit()
        return cur.rowcount == 1

    def has_diary(self, date: str) -> bool:
        return self.db.execute("SELECT 1 FROM diaries WHERE date = ?", (date,)).fetchone() is not None

    def diaries(self, before: str, limit: int) -> list[tuple[str, str]]:
        """日付が before より前の日記の直近 limit 件。日付の古い順の (date, body)。"""
        rows = self.db.execute("SELECT date, body FROM diaries WHERE date < ? ORDER BY date DESC LIMIT ?",
                               (before, limit)).fetchall()
        return rows[::-1]

    def last_id(self) -> int:
        return self.db.execute("SELECT COALESCE(MAX(id), 0) FROM utterances").fetchone()[0]

    def last_seal(self) -> dict[str, str] | None:
        """最後に固めたときのハッシュ。まだ固めていなければ None。"""
        row = self.db.execute("SELECT core_sha, style_sha FROM persona_seal ORDER BY id DESC LIMIT 1").fetchone()
        return None if row is None else {"core.md": row[0], "style.md": row[1]}

    def add_seal(self, hashes: dict[str, str]):
        """固め直しは行を足すだけ（前の封は残る）。"""
        self.db.execute("INSERT INTO persona_seal(at, core_sha, style_sha) VALUES(?, ?, ?)",
                        (_now(), hashes["core.md"], hashes["style.md"]))
        self.db.commit()

    def close(self):
        self.db.close()
