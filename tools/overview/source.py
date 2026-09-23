"""見取り図の材料：git の履歴・git に載った Markdown・Python のソースを読む。

読むのは git に載った物だけ（`git ls-files`）。`*.local.md`・`data/`・`.env` は git に載らないので読まない。
過去の版の中身は、goal.md の題の1行と、SESSION_STATE.md の決定の番号（`D` と数字だけ）のほかは出さない
（履歴の中身は、今の public 側に無い物を含みうる）。
"""
import ast
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
# 前身。CLAUDE.md §1 に書いてある置き場。読むのは文書だけで、ファイルがあるかと行数だけを見る
PREDECESSOR = Path(r"C:\work5\Kage-Shiki")
PREDECESSOR_SKIP = ("data/", ".env")


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, encoding="utf-8",
                          check=True).stdout


# ── git ──

@dataclass
class Commit:
    hash: str
    short: str
    date: str          # ISO 8601
    subject: str
    body: str
    files: list[str] = field(default_factory=list)


def commits() -> list[Commit]:
    """古い順。"""
    out = git("log", "--reverse", "--format=\x1e%H\x1f%h\x1f%aI\x1f%s\x1f%b\x1f", "--name-only")
    result = []
    for rec in out.split("\x1e")[1:]:
        h, short, date, subject, body, rest = rec.split("\x1f")
        files = [x for x in rest.strip().splitlines() if x]
        result.append(Commit(h, short, date, subject, body.strip(), files))
    return result


def tracked(pattern: str = "") -> list[str]:
    args = ["ls-files"] + ([pattern] if pattern else [])
    return sorted(x for x in git(*args).splitlines() if (REPO / x).exists())


def last_change(path: str) -> str:
    return git("log", "-1", "--format=%aI", "--", path).strip()


def goal_titles() -> list[dict]:
    """goal.md の各版の題（1行目）だけ。フェーズの切り替わりの印に使う。"""
    result = []
    for line in git("log", "--reverse", "--format=%h\x1f%aI", "--", "goal.md").splitlines():
        short, date = line.split("\x1f")
        head = git("show", f"{short}:goal.md").splitlines()[:1]
        title = head[0].removeprefix("# goal.md — ").strip() if head else ""
        result.append({"commit": short, "date": date, "title": title})
    return result


# ── Markdown ──

@dataclass
class Doc:
    path: str
    lines: list[str]

    @property
    def text(self):
        return "\n".join(self.lines)


def read(path: str) -> Doc:
    return Doc(path, (REPO / path).read_text(encoding="utf-8").splitlines())


def split_row(line: str) -> list[str]:
    """Markdown の表の1行を升に分ける。`\\|` は升の区切りにしない。"""
    cells = re.split(r"(?<!\\)\|", line.strip())
    return [c.strip().replace("\\|", "|") for c in cells[1:-1]]


def tables(doc: Doc) -> list[dict]:
    """表ごとに、直前の見出し・見出し行・行（行番号つき）を返す。"""
    result, heading, i = [], "", 0
    while i < len(doc.lines):
        line = doc.lines[i]
        if line.startswith("#"):
            heading = line.lstrip("#").strip()
        if line.startswith("|") and i + 1 < len(doc.lines) and re.match(r"^\|[\s:|-]+\|$", doc.lines[i + 1]):
            header = split_row(line)
            rows = []
            i += 2
            while i < len(doc.lines) and doc.lines[i].startswith("|"):
                rows.append({"line": i + 1, "cells": split_row(doc.lines[i])})
                i += 1
            result.append({"heading": heading, "header": header, "rows": rows})
            continue
        i += 1
    return result


def sections(doc: Doc) -> list[dict]:
    """見出しごとの範囲（行番号は1始まり、終わりを含む）。"""
    heads = [(i + 1, len(m.group(1)), m.group(2).strip())
             for i, line in enumerate(doc.lines) if (m := re.match(r"^(#{1,6})\s+(.*)", line))]
    result = []
    for k, (line, level, title) in enumerate(heads):
        end = len(doc.lines)
        for line2, level2, _ in heads[k + 1:]:
            if level2 <= level:
                end = line2 - 1
                break
        result.append({"line": line, "end": end, "level": level, "title": title})
    return result


def section_of(doc: Doc, line: int) -> str:
    best = ""
    for s in sections(doc):
        if s["line"] <= line <= s["end"]:
            best = s["title"]
    return best


def strip_md(s: str) -> str:
    return re.sub(r"\*\*|`", "", s)


# ── Python のソース ──

@dataclass
class Module:
    name: str
    path: str
    lines: int
    imports: list[str]
    functions: list[dict]
    classes: list[dict]
    signals: list[dict]
    connects: list[dict]
    threadsafe_calls: list[dict]
    threads: list[dict]
    tables: list[dict]
    broad_excepts: list[int]
    todos: list[dict]


def _name(node) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{_name(node.value)}.{node.attr}"
    return ""


def modules(package_dir: str = "src/utsushimi") -> list[Module]:
    base = REPO / package_dir
    pkg = base.name
    result = []
    for path in sorted(base.rglob("*.py")):
        rel = path.relative_to(REPO).as_posix()
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text)
        stem = path.relative_to(base).with_suffix("").as_posix().replace("/", ".")
        name = pkg if stem == "__init__" else f"{pkg}.{stem}"
        imports, functions, classes, signals, connects, calls, threads, broad = [], [], [], [], [], [], [], []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports += [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    target = pkg if not node.module else f"{pkg}.{node.module}"
                    if node.module is None:
                        imports += [f"{pkg}.{a.name}" if (base / f"{a.name}.py").exists() else pkg for a in node.names]
                    else:
                        imports.append(target)
                else:
                    imports.append(node.module)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.append({"name": node.name, "line": node.lineno,
                                  "length": node.end_lineno - node.lineno + 1,
                                  "async": isinstance(node, ast.AsyncFunctionDef)})
            elif isinstance(node, ast.ClassDef):
                classes.append({"name": node.name, "line": node.lineno,
                                "bases": [_name(b) for b in node.bases]})
                for item in node.body:
                    if (isinstance(item, ast.Assign) and isinstance(item.value, ast.Call)
                            and _name(item.value.func) == "Signal"):
                        args = [_name(a) or ast.unparse(a) for a in item.value.args]
                        for t in item.targets:
                            signals.append({"class": node.name, "name": _name(t), "args": args, "line": item.lineno})
            elif isinstance(node, ast.Call):
                fn = _name(node.func)
                if fn.endswith(".connect") and node.args:
                    connects.append({"signal": fn.removesuffix(".connect"), "slot": _name(node.args[0]) or "lambda",
                                     "line": node.lineno})
                elif fn.endswith("call_soon_threadsafe") and node.args:
                    calls.append({"target": _name(node.args[0]), "line": node.lineno})
                elif fn.endswith("Thread"):
                    kw = {k.arg: k.value for k in node.keywords}
                    tname = kw["name"].value if isinstance(kw.get("name"), ast.Constant) else ""
                    threads.append({"name": tname, "target": _name(kw["target"]) if "target" in kw else "",
                                    "line": node.lineno})
            elif isinstance(node, ast.ExceptHandler):
                if node.type is None or _name(node.type) in ("Exception", "BaseException"):
                    broad.append(node.lineno)
        # 画面のスレッドの名前は、main のスレッドに付け直す形（`current_thread().name = ...`）で書く
        for node in ast.walk(tree):
            if (isinstance(node, ast.Assign) and any(_name(t).endswith("current_thread().name") or
                                                     (isinstance(t, ast.Attribute) and t.attr == "name" and
                                                      isinstance(t.value, ast.Call) and
                                                      _name(t.value.func).endswith("current_thread"))
                                                     for t in node.targets)
                    and isinstance(node.value, ast.Constant)):
                threads.append({"name": node.value.value, "target": "main", "line": node.lineno})
        found_tables = []
        for m in re.finditer(r"CREATE TABLE IF NOT EXISTS (\w+)\s*\((.*?)\);", text, re.S):
            cols = []
            for raw in m.group(2).splitlines():
                raw = raw.split("--")[0].strip().rstrip(",")
                if raw:
                    cols.append(raw.split()[0])
            found_tables.append({"name": m.group(1), "columns": cols,
                                 "line": text[:m.start()].count("\n") + 1})
        todos = [{"line": i + 1, "text": line.strip()} for i, line in enumerate(text.splitlines())
                 if re.search(r"#\s*(TODO|FIXME|XXX)\b", line)]
        result.append(Module(name, rel, len(text.splitlines()), sorted(set(imports)), functions, classes,
                             signals, connects, calls, threads, found_tables, broad, todos))
    return result


# ── 前身 ──

def predecessor_file(rel: str) -> dict:
    """前身のファイルがあるか・行数（文書と src だけ。data/ と .env は開かない）。"""
    rel = rel.replace("\\", "/")
    if rel.startswith(PREDECESSOR_SKIP) or "/.env" in rel:
        return {"exists": None, "lines": None}
    p = PREDECESSOR / rel
    if not p.is_file():
        return {"exists": p.exists(), "lines": None}
    try:
        return {"exists": True, "lines": len(p.read_text(encoding="utf-8", errors="replace").splitlines())}
    except OSError:
        return {"exists": True, "lines": None}
