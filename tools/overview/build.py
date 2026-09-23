"""見取り図：リポジトリの今の中身から、プロジェクトを俯瞰する HTML 群を作り直す。

    uv run python tools/overview/build.py        # → build/overview/index.html を開く

材料は git の履歴と、git に載った文書・コードだけ（source.py）。生成物は git に載せない。
調べた候補と採否は docs/research/2026-09-23-overview-tools.md。
"""
import html
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from overview import source as S  # noqa: E402
from overview import views as V  # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = S.REPO / "build" / "overview"

# ブラウザで読む JS ライブラリ（CDN・版を固定。許諾は研究文書）
ECHARTS = "https://cdn.jsdelivr.net/npm/echarts@6.1.0/dist/echarts.min.js"
DAGRE = "https://cdn.jsdelivr.net/npm/@dagrejs/dagre@3.1.1/dist/dagre.min.js"
MERMAID = "https://cdn.jsdelivr.net/npm/mermaid@11.17.2/dist/mermaid.esm.min.mjs"

PAGES = [
    # (ファイル名, 題, 一行の説明, 使うライブラリ)
    ("index", "入口", "今どこにいるか・主な数・各ページへの道", [ECHARTS]),
    ("timeline", "年表", "コミット・フェーズ・検収・決定を時間の軸に", [ECHARTS]),
    ("trace", "追跡", "振る舞い BH → 段 → タスク → 済み。保護指定・禁則・lessons の届き先", [ECHARTS]),
    ("decisions", "決定", "D 番号・ADR・採らなかった案", []),
    ("structure", "本体の構造", "モジュールの依存・スレッドと渡し口・SQLite の表", [ECHARTS, DAGRE]),
    ("docs", "文書の地図", "文書どうしの参照・大きさ・最終更新", [ECHARTS, DAGRE]),
    ("predecessor", "前身とのずれ", "前身から引き継いだ物と、今の設計・実装の対応", [ECHARTS]),
    ("concerns", "気がかり", "機械で見つけた匂いと、文書に書いてある懸念（判定は主人）", [ECHARTS]),
    ("branches", "分岐", "選んだ道・捨てた道・戻る条件・これからの分かれ道", [ECHARTS]),
]


def page_html(name, title, lead, libs, data, meta):
    nav = "\n".join(
        f'<a href="{n}.html"{" aria-current=\"page\"" if n == name else ""}>{html.escape(t)}</a>'
        for n, t, _, _ in PAGES)
    scripts = "\n".join(f'<script src="{u}"></script>' for u in libs)
    payload = json.dumps(data, ensure_ascii=False, sort_keys=True).replace("</", "<\\/")
    mermaid = f'<script type="module">import mermaid from "{MERMAID}"; window.mermaid = mermaid; ' \
              f'window.dispatchEvent(new Event("mermaid-ready"));</script>' if name == "structure" else ""
    dirty = "（作業ツリーに未コミットの変更あり）" if meta["dirty"] else ""
    return f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)} — 見取り図</title>
<link rel="stylesheet" href="assets/style.css">
{scripts}
{mermaid}
</head>
<body data-page="{name}">
<header class="top">
  <div class="brand"><a href="index.html">見取り図</a><span>Utsushimi</span></div>
  <nav class="tabs">
{nav}
  </nav>
  <button class="theme" type="button" aria-label="配色を切り替える">配色：自動</button>
</header>
<main>
  <h1>{html.escape(title)}</h1>
  <p class="lead">{html.escape(lead)}</p>
  <div id="app"></div>
</main>
<footer>
  <p>材料：コミット <code>{meta["head"]}</code>（{html.escape(meta["head_date"])}）{dirty}。git に載った文書・コードだけから作った。</p>
<p class="generated">生成：{meta["generated"]}</p>
</footer>
<script type="application/json" id="data">{payload}</script>
<script src="assets/common.js"></script>
<script src="assets/pages/{name}.js"></script>
</body>
</html>
"""


def main():
    repo = V.Repo()
    pages = {
        "timeline": V.page_timeline(repo),
        "trace": V.page_trace(repo),
        "decisions": V.page_decisions(repo),
        "structure": V.page_structure(repo),
        "docs": V.page_docs(repo),
        "predecessor": V.page_predecessor(repo),
        "concerns": V.page_concerns(repo),
        "branches": V.page_branches(repo),
    }
    pages["index"] = V.page_index(repo, pages)
    pages["index"]["pages"] = [{"name": n, "title": t, "lead": lead} for n, t, lead, _ in PAGES if n != "index"]
    head = repo.commits[-1]
    meta = {"head": head.short, "head_date": head.date,
            "dirty": bool(S.git("status", "--porcelain").strip()),
            "generated": datetime.now().isoformat(timespec="seconds")}
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(HERE / "static", OUT / "assets")
    for name, title, lead, libs in PAGES:
        (OUT / f"{name}.html").write_text(page_html(name, title, lead, libs, pages[name], meta),
                                          encoding="utf-8", newline="\n")
    print(OUT / "index.html")


if __name__ == "__main__":
    main()
