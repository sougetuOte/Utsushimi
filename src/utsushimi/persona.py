"""人格：`data/persona/` のテキストファイル（ADR 0002・design.md §2）。核のスレッドだけが読み書きする。

根っこ（core.md）と口調の見本（style.md）を読んで検査し、ハッシュを出す。
書く口は確定の `seal` の1つだけで、固めた後は書かずに拒む（BH-19）。
"""
import hashlib
from pathlib import Path

# docs/concept.md §8.2・§8.4 の見出し
CORE = [("C1", "名前"), ("C2", "一人称"), ("C3", "二人称"), ("C4", "人格核文"), ("C5", "性格軸"),
        ("C6", "口調パターン"), ("C7", "口癖"), ("C8", "年齢感"), ("C9", "価値観"), ("C10", "禁忌"),
        ("C11", "知識の自己認識")]
STYLE = [("S1", "日常会話"), ("S2", "感情表現（喜）"), ("S3", "感情表現（怒／不快）"), ("S4", "感情表現（悲／寂）"),
         ("S5", "困惑／不知"), ("S6", "ユーモア"), ("S7", "沈黙破り")]

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


def render(headings: list[tuple[str, str]], bodies: dict[str, str]) -> str:
    """見出し `## C1 名前` と中身を順に並べる。中身の無い見出しは出さない。"""
    return "\n".join(f"## {key} {title}\n{bodies[key].strip()}\n"
                     for key, title in headings if bodies.get(key, "").strip())


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

    @property
    def absent(self) -> bool:
        """人格のファイルが1つも無い（キャラ作りから始める状態。design.md §4.1 の 3）。"""
        return all(heading == "-" for _, heading, _ in self.problems) and len(self.problems) == len(REQUIRED)

    @property
    def name(self) -> str:
        """C1 の最初の行。会話の欄でキャラの発言に付ける。"""
        return _sections(self.texts["core.md"])["C1"].splitlines()[0].strip()


def hashes(directory: Path) -> dict[str, str]:
    """今のファイルのハッシュ（終了のときにログへ残す）。"""
    return {name: hashlib.sha256((directory / name).read_bytes()).hexdigest()
            for name in REQUIRED if (directory / name).exists()}


def seal(directory: Path, files: dict[str, str], memory) -> dict[str, str]:
    """確定の口（design.md §2・§4.3）。固める前だけ、core.md・style.md・origin.md を書いてから persona_seal に1行足す。

    persona_seal に行があれば（固めた後）、ファイルに触れずに拒む。凍結後に根っこを変えられるのは主人の手だけ（BH-19）。
    """
    if memory.last_seal() is not None:
        raise PermissionError("persona is already sealed")
    directory.mkdir(parents=True, exist_ok=True)
    for name in ("core.md", "style.md", "origin.md"):
        (directory / name).write_text(files[name], encoding="utf-8", newline="\n")
    sealed = hashes(directory)
    memory.add_seal(sealed)
    return sealed
