"""人格：`data/persona/` のテキストファイル（ADR 0002・design.md §2）。核のスレッドだけが読む。

根っこ（core.md）と口調の見本（style.md）を読んで検査し、ハッシュを出す。書く口は持たない（BH-19）。
"""
import hashlib
from pathlib import Path

# docs/concept.md §8.2・§8.4 の「必須」。C7・C8・C10 は任意
REQUIRED = {
    "core.md": ["C1", "C2", "C3", "C4", "C5", "C6", "C9", "C11"],
    "style.md": ["S1", "S2", "S3", "S4", "S5", "S6", "S7"],
}


def _sections(text: str) -> dict[str, str]:
    """見出し `## C1 名前` の `C1` をキーに、次の見出しまでの中身を返す。"""
    sections, key, lines = {}, None, []
    for line in text.splitlines():
        if line.startswith("## "):
            if key:
                sections[key] = "\n".join(lines).strip()
            parts = line[3:].split()
            key, lines = (parts[0] if parts else ""), []
        elif key:
            lines.append(line)
    if key:
        sections[key] = "\n".join(lines).strip()
    return sections


class Persona:
    def __init__(self, directory: Path):
        self.texts = {}
        self.hashes = {}
        self.problems = []  # (ファイル名, 見出し, missing|empty)
        for name, required in REQUIRED.items():
            path = directory / name
            if not path.exists():
                self.problems.append((name, "-", "missing"))
                continue
            data = path.read_bytes()
            self.hashes[name] = hashlib.sha256(data).hexdigest()
            self.texts[name] = data.decode("utf-8")
            sections = _sections(self.texts[name])
            for heading in required:
                if heading not in sections:
                    self.problems.append((name, heading, "missing"))
                elif not sections[heading]:
                    self.problems.append((name, heading, "empty"))


def hashes(directory: Path) -> dict[str, str]:
    """今のファイルのハッシュ（終了のときにログへ残す）。"""
    return {name: hashlib.sha256((directory / name).read_bytes()).hexdigest()
            for name in REQUIRED if (directory / name).exists()}
