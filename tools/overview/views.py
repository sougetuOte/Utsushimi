"""見取り図の各ページのデータを組む。値はすべて source.py が読んだ物から数える（手で書いた値を持たない）。"""
import re
from collections import Counter, defaultdict
from pathlib import PurePosixPath

from . import source as S

BH = re.compile(r"BH-(\d+)")
LESSON = re.compile(r"\b(Bug-\d+|L-\d+|B-\d+)\b")
TASK = re.compile(r"\bT(\d+)\b")
EXTS = (".md", ".py", ".toml", ".ps1", ".json", ".lock", ".txt", ".html", ".css", ".js", ".sh", ".cs", ".rs",
        ".yml", ".yaml", ".ico")
LONG_FUNCTION = 40   # 行。これを超える関数を気がかりに出す
BIG_FILE = 300       # 行。これを超えるファイルを気がかりに出す


def bh_key(s: str) -> int:
    return int(BH.search(s).group(1))


class Repo:
    """1回の生成で読む物をまとめて持つ。"""

    def __init__(self):
        self.commits = S.commits()
        self.md_paths = S.tracked("*.md")
        self.docs = {p: S.read(p) for p in self.md_paths}
        self.modules = S.modules()
        self.goals = S.goal_titles()
        self.tracked = S.tracked()
        ever = S.git("log", "--format=", "--name-only").splitlines()
        self.ever_tracked = sorted(set(x for x in ever if x) | set(self.tracked))

    def doc(self, path):
        return self.docs[path]


# ── 共通の読み取り ──

def behaviors(r: Repo) -> list[dict]:
    doc = r.doc("docs/behaviors.md")
    out = []
    for t in S.tables(doc):
        if not t["header"] or t["header"][0] != "行":
            continue
        h = t["header"]
        for row in t["rows"]:
            c = dict(zip(h, row["cells"]))
            if not BH.fullmatch(c.get("行", "")):
                continue
            out.append({"id": c["行"], "chapter": t["heading"], "text": S.strip_md(c.get("ふるまい", "")),
                        "origin": c.get("元", ""), "priority": c.get("優先度", ""),
                        "predecessor": S.strip_md(c.get("前身での状況", "")),
                        "note": S.strip_md(c.get("紐付け・備考", "")), "line": row["line"],
                        "protected": sorted(set(re.findall(r"保護指定\s*(\d)", c.get("紐付け・備考", ""))))})
    return sorted(out, key=lambda b: bh_key(b["id"]))


def requirements(r: Repo) -> dict:
    doc = r.doc("docs/specs/stage1/requirements.md")
    out = {}
    for t in S.tables(doc):
        if not t["header"] or t["header"][0] != "BH":
            continue
        for row in t["rows"]:
            c = dict(zip(t["header"], row["cells"]))
            m = BH.fullmatch(c.get("BH", ""))
            if not m:
                continue
            stage = "段1" if c.get("段", "").startswith("段1") else "段2以降"
            out[c["BH"]] = {"stage": stage, "condition": S.strip_md(c.get("完了条件／送る理由", "")),
                            "tasks": sorted(set(f"T{n}" for n in TASK.findall(c.get("タスク", "")))),
                            "line": row["line"]}
    return out


def tasks(r: Repo) -> list[dict]:
    doc = r.doc("docs/specs/stage1/tasks.md")
    out, cur = [], None
    for i, line in enumerate(doc.lines, 1):
        m = re.match(r"^- \[( |x)\] \*\*T(\d+)\s+(.*?)\*\*", line)
        if m:
            cur = {"id": f"T{m.group(2)}", "done": m.group(1) == "x", "title": m.group(3).strip(), "line": i,
                   "description": [], "conditions": []}
            out.append(cur)
        elif cur and line.startswith("  "):
            text = line.strip()
            if text.startswith("- 完了条件："):
                cur["conditions"].append({"line": i, "text": text.removeprefix("- ")})
            elif text:
                cur["description"].append(text)
        elif line.startswith("#"):
            cur = None
    for t in out:
        body = " ".join(c["text"] for c in t["conditions"])
        t["bh"] = sorted(set(f"BH-{n}" for n in BH.findall(body)), key=bh_key)
        t["lessons"] = sorted(set(LESSON.findall(body)))
        t["description"] = " ".join(t["description"])
    return out


def smoke_items(r: Repo) -> list[dict]:
    if "docs/smoke-test.md" not in r.docs:
        return []
    doc = r.doc("docs/smoke-test.md")
    out = []
    for s in S.sections(doc):
        m = re.match(r"(S-\d+)\s+(.*?)（(.*?)）", s["title"])
        if m:
            out.append({"id": m.group(1), "title": m.group(2), "refs": m.group(3), "line": s["line"],
                        "tasks": sorted(set(f"T{n}" for n in TASK.findall(m.group(3))))})
    return out


def lesson_items(r: Repo) -> list[dict]:
    doc = r.doc("docs/lessons.md")
    out = []
    for s in S.sections(doc):
        if s["level"] != 3:
            continue
        m = re.match(r"(Bug-\d+|L-\d+|B-\d+)：(.*)", s["title"])
        if m:
            out.append({"id": m.group(1), "title": m.group(2), "line": s["line"]})
        elif S.section_of(doc, s["line"] - 1).startswith("4.") or "4." in _parent(doc, s["line"]):
            out.append({"id": f"§4 {s['title']}", "title": s["title"], "line": s["line"]})
    return out


def _parent(doc, line):
    parent = ""
    for s in S.sections(doc):
        if s["level"] == 2 and s["line"] < line:
            parent = s["title"]
    return parent


def session_state(r: Repo) -> dict:
    doc = r.doc("SESSION_STATE.md")
    secs = {s["title"]: s for s in S.sections(doc)}

    def bullets(title):
        s = secs.get(title)
        if not s:
            return []
        out = []
        for i in range(s["line"], s["end"]):
            line = doc.lines[i]
            if line.startswith("- "):
                out.append({"line": i + 1, "text": S.strip_md(line[2:])})
            elif line.startswith("  ") and out:
                out[-1]["text"] += " " + S.strip_md(line.strip())
        return out

    def body(title):
        s = secs.get(title)
        return "\n".join(doc.lines[s["line"]:s["end"]]).strip() if s else ""

    tabs = {t["heading"]: t for t in S.tables(doc)}
    decisions = []
    for row in tabs.get("決定（蒸し返さない）", {"rows": []})["rows"]:
        num, text = row["cells"][0], row["cells"][1]
        date = re.search(r"(\d{4}-\d{2}-\d{2})", text)
        decisions.append({"id": num, "text": S.strip_md(text), "line": row["line"],
                          "date": date.group(1) if date else ""})
    rejected = [{"idea": S.strip_md(row["cells"][0]), "reason": S.strip_md(row["cells"][1]), "line": row["line"]}
                for row in tabs.get("採らなかった案", {"rows": []})["rows"]]
    history = [{"commits": re.findall(r"`([0-9a-f]{7,})`", row["cells"][0]), "text": S.strip_md(row["cells"][1]),
                "line": row["line"]} for row in tabs.get("これまで", {"rows": []})["rows"]]
    reading = [{"order": row["cells"][0], "doc": row["cells"][1], "why": S.strip_md(row["cells"][2]),
                "line": row["line"]} for row in tabs.get("読む順序", {"rows": []})["rows"]]
    return {"decisions": decisions, "rejected": rejected, "history": history, "reading": reading,
            "pending_master": [b for b in bullets("未決（主人の判断待ち）")],
            "pending_work": [b for b in bullets("未決（実測・作業待ち）")],
            "next": body("次の一手"), "now": body("現在地"), "what": body("これは何か")}


def adrs(r: Repo) -> list[dict]:
    out = []
    for path in r.md_paths:
        m = re.match(r"docs/adr/(\d{4})-.*\.md$", path)
        if not m or m.group(1) == "0000":
            continue
        doc = r.doc(path)
        meta = {}
        for line in doc.lines[:10]:
            mm = re.match(r"^- (日付|状態|決めた人)：(.*)", line)
            if mm:
                meta[mm.group(1)] = mm.group(2).strip()
        secs = {s["title"]: s for s in S.sections(doc)}
        rejected = []
        for t in S.tables(doc):
            if t["heading"] == "却下した案":
                rejected += [{"idea": S.strip_md(row["cells"][0]), "reason": S.strip_md(row["cells"][1]),
                              "line": row["line"]} for row in t["rows"]]

        def items(title, start=None):
            s = secs.get(title)
            if not s:
                return []
            res = []
            for i in range(s["line"], s["end"]):
                line = doc.lines[i]
                if line.startswith("- "):
                    res.append({"line": i + 1, "text": S.strip_md(line[2:])})
                elif line.startswith("  ") and res:
                    res[-1]["text"] += " " + S.strip_md(line.strip())
            return res

        accepted = []
        s = secs.get("結果")
        if s:
            inside = False
            for i in range(s["line"], s["end"]):
                line = doc.lines[i]
                if line.startswith("- "):
                    inside = line.startswith("- 引き受けるもの")
                elif inside and line.startswith("  - "):
                    accepted.append({"line": i + 1, "text": S.strip_md(line.strip()[2:])})
                elif inside and line.startswith("    ") and accepted:
                    accepted[-1]["text"] += " " + S.strip_md(line.strip())
        title = doc.lines[0].lstrip("# ").strip()
        out.append({"id": m.group(1), "path": path, "title": re.sub(r"^\d{4}\.\s*", "", title),
                    "date": meta.get("日付", ""), "status": meta.get("状態", ""), "by": meta.get("決めた人", ""),
                    "rejected": rejected, "sunset": items("消滅条件"), "accepted": accepted})
    return out


def stages(r: Repo) -> list[dict]:
    doc = r.doc("docs/concept.md")
    out = []
    for s in S.sections(doc):
        m = re.match(r"(段\d)「(.*?)」── 前身 (Phase \d)（(.*?)）", s["title"])
        if m:
            out.append({"stage": m.group(1), "title": m.group(2), "predecessor": m.group(3),
                        "predecessor_title": m.group(4), "line": s["line"]})
    return out


def claude_md(r: Repo) -> dict:
    doc = r.doc("CLAUDE.md")
    secs = S.sections(doc)
    protected, rules = [], []
    for s in secs:
        if s["title"].startswith("保護指定"):
            for i in range(s["line"], s["end"]):
                m = re.match(r"^(\d)\.\s+(.*)", doc.lines[i])
                if m:
                    protected.append({"id": f"保護指定{m.group(1)}", "text": m.group(2), "line": i + 1})
        if s["title"] == "目的から導かれる禁則":
            for i in range(s["line"], s["end"]):
                m = re.match(r"^- \*\*(.*?)\*\*", doc.lines[i])
                if m:
                    rules.append({"text": m.group(1).rstrip("。"), "line": i + 1})
    not_carried = []
    for t in S.tables(doc):
        if t["heading"].startswith("4.") and t["header"][:1] == ["前身"]:
            not_carried = [{"item": S.strip_md(row["cells"][0]), "reason": S.strip_md(row["cells"][1]),
                            "line": row["line"]} for row in t["rows"]]
    return {"protected": protected, "rules": rules, "not_carried": not_carried}


def commit_kind(c: S.Commit) -> str:
    files = c.files
    if any(f == "goal.md" for f in files) and ("G0" in c.subject or "goal.md" in c.subject):
        return "G0・契約"
    if any(f.startswith("src/") for f in files):
        return "本体"
    if any(f.startswith("tools/") for f in files):
        return "道具"
    if any(f.startswith("spikes/") for f in files):
        return "スパイク"
    if all(f in ("SESSION_STATE.md", "docs/specs/stage1/tasks.md") for f in files):
        return "索引"
    if any(f.startswith("docs/") for f in files):
        return "文書"
    return "運営・その他"


# ── ページ ──

def page_timeline(r: Repo) -> dict:
    st = session_state(r)
    notes = defaultdict(list)
    for h in st["history"]:
        for c in h["commits"]:
            notes[c[:7]].append(h["text"])
    # 各コミットの時点で SESSION_STATE にあった D 番号（番号だけを読む）
    seen, decided = set(), []
    for c in r.commits:
        if "SESSION_STATE.md" not in c.files:
            continue
        try:
            text = S.git("show", f"{c.short}:SESSION_STATE.md")
        except Exception:
            continue
        for n in re.findall(r"^\| (D\d+) \|", text, re.M):
            if n not in seen:
                seen.add(n)
                decided.append({"id": n, "commit": c.short, "date": c.date})
    dtext = {d["id"]: d["text"] for d in st["decisions"]}
    for d in decided:
        d["text"] = dtext.get(d["id"], "（今の SESSION_STATE には無い）")
    reviews = []
    for c in r.commits:
        msg = c.subject + "\n" + c.body
        if "検収" in msg and ("PASS" in msg or "FAIL" in msg):
            for m in re.finditer(r"[^。\n]*?(PASS|FAIL)[^。\n]*", msg):
                reviews.append({"commit": c.short, "date": c.date, "result": m.group(1), "text": m.group(0).strip()})
    phases = []
    for i, g in enumerate(r.goals):
        end = r.goals[i + 1]["date"] if i + 1 < len(r.goals) else r.commits[-1].date
        if phases and phases[-1]["title"] == g["title"]:
            phases[-1]["end"] = end
            continue
        phases.append({"title": g["title"], "start": g["date"], "end": end, "commit": g["commit"]})
    return {"commits": [{"short": c.short, "date": c.date, "subject": c.subject, "kind": commit_kind(c),
                         "files": len(c.files), "notes": notes.get(c.short, [])} for c in r.commits],
            "phases": phases, "decisions": decided, "reviews": reviews}


def page_trace(r: Repo) -> dict:
    bhs, req, ts = behaviors(r), requirements(r), tasks(r)
    done = {t["id"]: t["done"] for t in ts}
    design = r.doc("docs/specs/stage1/design.md")
    design_refs = defaultdict(set)
    for i, line in enumerate(design.lines, 1):
        for n in BH.findall(line):
            design_refs[f"BH-{n}"].add(S.section_of(design, i))
    rows = []
    for b in bhs:
        q = req.get(b["id"], {})
        tlist = q.get("tasks", [])
        if q.get("stage") == "段1":
            state = "済み" if tlist and all(done.get(t) for t in tlist) else "まだ"
        else:
            state = "送った"
        rows.append({**b, "stage": q.get("stage", "（requirements に無い）"), "tasks": tlist, "state": state,
                     "condition": q.get("condition", ""), "design": sorted(design_refs.get(b["id"], []))})
    # 保護指定・禁則・lessons がどこに届いているか
    cm = claude_md(r)
    task_text = {t["id"]: " ".join(c["text"] for c in t["conditions"]) + " " + t["description"] for t in ts}
    places = {"requirements": r.doc("docs/specs/stage1/requirements.md"), "design": design,
              "tasks": r.doc("docs/specs/stage1/tasks.md")}

    def reach(needle, pattern=None):
        res = {}
        for name, doc in places.items():
            hits = [i for i, line in enumerate(doc.lines, 1)
                    if (re.search(pattern, line) if pattern else needle in line)]
            res[name] = hits
        res["tasks_by_id"] = sorted(t for t, txt in task_text.items()
                                    if (re.search(pattern, txt) if pattern else needle in txt))
        return res

    protected = [{**p, "reach": reach(p["id"], rf"{p['id']}(?!\d)")} for p in cm["protected"]]
    # 禁則は design §6 の表の4つ（CLAUDE.md §0 の禁則を設計の言葉にした物）で追う
    rules = []
    for t in S.tables(design):
        if t["heading"].startswith("6."):
            for row in t["rows"]:
                m = re.search(r"\*\*(.*?)\*\*", row["cells"][0])
                phrase = m.group(1) if m else S.strip_md(row["cells"][0])
                rules.append({"text": phrase, "line": row["line"], "guarantee": S.strip_md(row["cells"][1]),
                              "reach": reach(phrase)})
    lessons = [{**l, "reach": reach(l["id"], rf"(?<![\w-]){re.escape(l['id'])}(?!\d)")}
               if not l["id"].startswith("§4") else {**l, "reach": reach(l["title"][:6])}
               for l in lesson_items(r)]
    flow = Counter()
    for row in rows:
        ch = row["chapter"]
        flow[(ch, row["stage"])] += 1
        targets = row["tasks"] or ["（タスクなし）"]
        for t in targets:
            flow[(row["stage"], t)] += 1 / len(targets)
            flow[(t, "済み" if done.get(t) else "まだ" if t in done else "（なし）")] += 1 / len(targets)
    links = [{"source": a, "target": b, "value": round(v, 3)} for (a, b), v in sorted(flow.items())]
    return {"rows": rows, "tasks": ts, "smoke": smoke_items(r), "protected": protected, "rules": rules,
            "lessons": lessons, "links": links}


def page_decisions(r: Repo) -> dict:
    st = session_state(r)
    return {"decisions": st["decisions"], "adrs": adrs(r), "rejected": st["rejected"]}


def page_structure(r: Repo) -> dict:
    mods = r.modules
    names = {m.name for m in mods}
    edges, external = [], Counter()
    for m in mods:
        for imp in m.imports:
            if imp in names and imp != m.name:
                edges.append({"source": m.name, "target": imp})
            elif imp not in names:
                external[imp.split(".")[0]] += 1
                edges.append({"source": m.name, "target": "ext:" + imp.split(".")[0], "external": True})
    edges = [dict(t) for t in sorted({tuple(sorted(e.items())) for e in edges})]
    signals = [{**s, "module": m.name} for m in mods for s in m.signals]
    connects = [{**c, "module": m.name} for m in mods for c in m.connects]
    calls = [{**c, "module": m.name} for m in mods for c in m.threadsafe_calls]
    threads = [{**t, "module": m.name} for m in mods for t in m.threads]
    tables = [{**t, "module": m.name} for m in mods for t in m.tables]
    return {"modules": [{"name": m.name, "path": m.path, "lines": m.lines, "imports": m.imports,
                         "functions": m.functions, "classes": m.classes} for m in mods],
            "edges": edges, "external": sorted(external), "signals": signals, "connects": connects,
            "calls": calls, "threads": threads, "tables": tables}


def _refs(r: Repo, doc: S.Doc):
    """文書の中の、リポジトリのファイルを指していそうな字句（行番号つき）。"""
    top = sorted({p.split("/")[0] + "/" for p in r.ever_tracked if "/" in p})
    basenames = defaultdict(set)
    for p in r.ever_tracked:
        basenames[PurePosixPath(p).name].add(p)
    for i, line in enumerate(doc.lines, 1):
        tokens = re.findall(r"`([^`\s]+)`", line) + re.findall(r"\]\(([^)\s]+)\)", line)
        for tok in tokens:
            t = re.sub(r":\d+(-\d+)?$", "", tok.strip().rstrip("。、"))
            if (not t or t.startswith(("K/", "http", "C:", "D:", "%", "data/", ".env", ".venv", ".git/", "build/", "~",
                                       "/"))
                    or any(ch in t for ch in "<>*{}[]$")):
                continue
            if "/" in t:
                if not (t.startswith(tuple(top)) or t.endswith(EXTS)):
                    continue
            elif not (t.endswith(EXTS) and t in basenames):
                continue
            yield i, t


def _resolve(r: Repo, doc_path: str, t: str):
    """参照先のパス（ファイルか、`/` で終わるディレクトリ）。見つからなければ None。"""
    tracked = r.tracked
    if "/" not in t:
        hits = sorted(p for p in tracked if PurePosixPath(p).name == t)
        if not hits:
            return None
        near = [p for p in hits if PurePosixPath(p).parent == PurePosixPath(doc_path).parent]
        return (near or hits)[0]
    for c in (t, (PurePosixPath(doc_path).parent / t).as_posix()):
        c = c.rstrip("/")
        if c in tracked:
            return c
        if any(p.startswith(c + "/") for p in tracked):
            return c + "/"
        if any(p.startswith(c) for p in tracked):   # `docs/adr/0001` のような前方一致
            return next(p for p in tracked if p.startswith(c))
    return None


def page_docs(r: Repo) -> dict:
    nodes, edges, dangling = [], Counter(), []
    for p in r.md_paths:
        doc = r.doc(p)
        nodes.append({"id": p, "lines": len(doc.lines), "updated": S.last_change(p),
                      "title": doc.lines[0].lstrip("# ").strip() if doc.lines else p})
        for line, t in _refs(r, doc):
            target = _resolve(r, p, t)
            if target is None:
                dangling.append({"doc": p, "line": line, "ref": t})
            elif target != p:
                edges[(p, target)] += 1
    others = sorted({b for (_, b) in edges if b not in r.docs})
    return {"nodes": nodes, "others": others,
            "edges": [{"source": a, "target": b, "count": n} for (a, b), n in sorted(edges.items())],
            "dangling": dangling}


def page_predecessor(r: Repo) -> dict:
    refs, cache = [], {}
    pat = re.compile(r"K/([A-Za-z0-9_./\-]+?)(?::(\d+)(?:-(\d+))?)?(?=[\s`、，,）)\]。：]|$)")
    for p in r.md_paths:
        doc = r.doc(p)
        for i, line in enumerate(doc.lines, 1):
            for m in pat.finditer(line):
                rel = m.group(1).rstrip(".")
                if rel not in cache:
                    cache[rel] = S.predecessor_file(rel)
                info = cache[rel]
                end = int(m.group(3) or m.group(2) or 0)
                refs.append({"doc": p, "line": i, "section": S.section_of(doc, i), "path": rel,
                             "from": int(m.group(2)) if m.group(2) else None, "to": end or None,
                             "exists": info["exists"], "k_lines": info["lines"],
                             "range_ok": None if not end or info["lines"] is None else end <= info["lines"]})
    bhs, req, ts = behaviors(r), requirements(r), tasks(r)
    done = {t["id"]: t["done"] for t in ts}
    status = Counter()
    for b in bhs:
        q = req.get(b["id"], {})
        now = q.get("stage", "？")
        if now == "段1":
            now = "段1・済み" if q["tasks"] and all(done.get(t) for t in q["tasks"]) else "段1・まだ"
        base = re.match(r"(実装済み|未統合|未着手)", b["predecessor"])
        status[(base.group(1) if base else b["predecessor"] or "？", now)] += 1
    return {"found": S.PREDECESSOR.exists(), "refs": refs,
            "files": sorted({x["path"] for x in refs}),
            "status": [{"predecessor": a, "now": b, "count": n} for (a, b), n in sorted(status.items())],
            "stages": stages(r), "not_carried": claude_md(r)["not_carried"],
            "behaviors": [{"id": b["id"], "predecessor": b["predecessor"], "priority": b["priority"],
                           "stage": req.get(b["id"], {}).get("stage", "？"), "text": b["text"]} for b in bhs]}


def page_concerns(r: Repo) -> dict:
    items = []

    def add(kind, doc, line, text):
        items.append({"kind": kind, "doc": doc, "line": line, "text": text})

    # 文書の匂い
    for d in page_docs(r)["dangling"]:
        add("参照先の無い参照", d["doc"], d["line"], f"`{d['ref']}` が見つからない")
    st = session_state(r)
    for row in st["reading"]:
        cell = row["doc"]
        for m in re.finditer(r"`([^`]+)`（(\d+)行）", cell):
            path, n = m.group(1), int(m.group(2))
            if path in r.docs and len(r.doc(path).lines) != n:
                add("行数のずれ", "SESSION_STATE.md", row["line"],
                    f"{path}：書いてある {n} 行、実際は {len(r.doc(path).lines)} 行")
        m = re.search(r"`([^`]+/)`（(.*?)行）", cell)
        if m:
            for name, n in re.findall(r"(\w+)\s+(\d+)", m.group(2)):
                path = f"{m.group(1)}{name}.md"
                if path in r.docs and len(r.doc(path).lines) != int(n):
                    add("行数のずれ", "SESSION_STATE.md", row["line"],
                        f"{path}：書いてある {n} 行、実際は {len(r.doc(path).lines)} 行")
    req, ts = requirements(r), tasks(r)
    in_tasks = {b for t in ts for b in t["bh"]}
    for bh, q in sorted(req.items(), key=lambda x: bh_key(x[0])):
        if q["stage"] == "段1" and bh not in in_tasks:
            add("段1 の BH がタスクの完了条件に無い", "docs/specs/stage1/requirements.md", q["line"],
                f"{bh}（タスク欄：{'・'.join(q['tasks']) or 'なし'}）")
    smoke = {t for s in smoke_items(r) for t in s["tasks"]}
    for t in ts:
        if t["done"] and t["id"] not in smoke:
            add("☑ なのに手順書に項目が無いタスク", "docs/specs/stage1/tasks.md", t["line"], f"{t['id']} {t['title']}")
    # 書いてある懸念
    for b in st["pending_master"]:
        add("未決（主人の判断待ち）", "SESSION_STATE.md", b["line"], b["text"])
    for b in st["pending_work"]:
        if b["text"] != "（なし）":
            add("未決（作業待ち）", "SESSION_STATE.md", b["line"], b["text"])
    words = {"後で": "「後で」", "未測": "「未測」", "機構なし": "「機構なし」", "機構: なし": "「機構なし」"}
    for p in r.md_paths:
        doc = r.doc(p)
        for i, line in enumerate(doc.lines, 1):
            plain = re.sub(r"「[^」]*」|`[^`]*`", "", line)
            for w, kind in words.items():
                if w in plain:
                    add(kind, p, i, S.strip_md(line.strip().lstrip("-|# ").strip())[:200])
                    break
    for a in adrs(r):
        for x in a["accepted"]:
            add("ADR の引き受けるもの", a["path"], x["line"], x["text"])
    for c in r.commits:
        msg = c.subject + "\n" + c.body
        for m in re.finditer(r"[^。\n]*FAIL[^。\n]*", msg):
            add("検収 FAIL の履歴", f"commit {c.short}", None, m.group(0).strip())
    # コードの匂い
    for m in r.modules:
        if m.lines > BIG_FILE:
            add("大きいファイル", m.path, 1, f"{m.lines} 行（目安 {BIG_FILE} 行）")
        for f in m.functions:
            if f["length"] > LONG_FUNCTION:
                add("長い関数", m.path, f["line"], f"{f['name']}：{f['length']} 行（目安 {LONG_FUNCTION} 行）")
        for line in m.broad_excepts:
            add("except Exception", m.path, line, "広い例外の受け止め")
        for t in m.todos:
            add("TODO", m.path, t["line"], t["text"])
    kinds = ["参照先の無い参照", "行数のずれ", "段1 の BH がタスクの完了条件に無い", "☑ なのに手順書に項目が無いタスク",
             "未決（主人の判断待ち）", "未決（作業待ち）", "「後で」", "「未測」", "「機構なし」", "ADR の引き受けるもの",
             "検収 FAIL の履歴", "大きいファイル", "長い関数", "except Exception", "TODO"]
    groups = {"文書の匂い": kinds[:4], "書いてある懸念": kinds[4:11], "コードの匂い": kinds[11:]}
    tree = [{"name": m.path, "children": [{"name": f["name"], "value": f["length"], "line": f["line"]}
                                          for f in m.functions if f["length"] > 0] or [{"name": "（関数なし）", "value": m.lines}]}
            for m in r.modules]
    return {"items": items, "kinds": kinds, "groups": groups, "counts": dict(Counter(x["kind"] for x in items)),
            "code_tree": tree, "thresholds": {"long_function": LONG_FUNCTION, "big_file": BIG_FILE}}


def page_branches(r: Repo) -> dict:
    st = session_state(r)
    ads = adrs(r)

    def short(text, n=60):
        text = re.sub(r"\s+", " ", text)
        return text if len(text) <= n else text[:n] + "…"

    decisions = []
    for d in st["decisions"]:
        linked = sorted(set(re.findall(r"ADR (\d{4})", d["text"])) |
                        {f"{int(a):04d}" for a in re.findall(r"ADR\s*0*(\d+)〜0*\d+", d["text"])})
        m = re.search(r"ADR\s*0*(\d+)〜0*(\d+)", d["text"])
        if m:
            linked = sorted(set(linked) | {f"{n:04d}" for n in range(int(m.group(1)), int(m.group(2)) + 1)})
        decisions.append({"id": d["id"], "label": short(d["text"]), "text": d["text"], "adrs": linked})
    adr_nodes = [{"id": a["id"], "label": short(a["title"]), "status": a["status"],
                  "chosen": a["title"], "rejected": a["rejected"], "sunset": a["sunset"]} for a in ads]
    open_ = [{"label": short(b["text"]), "text": b["text"], "kind": "主人の判断待ち", "line": b["line"]}
             for b in st["pending_master"]]
    open_ += [{"label": short(b["text"]), "text": b["text"], "kind": "作業待ち", "line": b["line"]}
              for b in st["pending_work"] if b["text"] != "（なし）"]
    return {"decisions": decisions, "adrs": adr_nodes, "rejected": st["rejected"], "open": open_}


def page_index(r: Repo, pages: dict) -> dict:
    st = session_state(r)
    ts = tasks(r)
    tr = pages["trace"]
    per_hour = Counter(c.date[:13].replace("T", " ") + "時" for c in r.commits)
    return {"what": st["what"], "now": st["now"], "next": st["next"],
            "phase": r.goals[-1]["title"] if r.goals else "",
            "head": {"short": r.commits[-1].short, "date": r.commits[-1].date, "subject": r.commits[-1].subject},
            "numbers": [[k, v] for k, v in {
                "コミット": len(r.commits),
                "フェーズ（goal.md の版の題）": len(pages["timeline"]["phases"]),
                "振る舞い BH": len(tr["rows"]),
                "段1 の BH": sum(1 for x in tr["rows"] if x["stage"] == "段1"),
                "タスク ☑": f"{sum(t['done'] for t in ts)} / {len(ts)}",
                "決定 D": len(st["decisions"]),
                "ADR": len(pages["decisions"]["adrs"]),
                "気がかり": len(pages["concerns"]["items"]),
                "文書（Markdown）": len(r.md_paths),
                "本体のモジュール": len(r.modules),
                "本体の行数": sum(m.lines for m in r.modules),
            }.items()],
            "tasks": [{"id": t["id"], "title": t["title"], "done": t["done"]} for t in ts],
            "per_hour": sorted(per_hour.items()),
            "concern_counts": pages["concerns"]["counts"]}
