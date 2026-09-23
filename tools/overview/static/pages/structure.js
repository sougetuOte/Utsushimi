// (e) 本体の構造：モジュールの依存（dagre で階層に並べ、ECharts で描く）・スレッドと渡し口（Mermaid）・SQLite の表
"use strict";
{
  const D = DATA;

  // dagre で階層の座標を出す。外部のパッケージは右端の段にまとめて小さく出す
  function layout(nodes, edges, rankdir) {
    const g = new dagre.graphlib.Graph();
    g.setGraph({ rankdir, nodesep: 24, ranksep: 90, marginx: 20, marginy: 20 });
    g.setDefaultEdgeLabel(() => ({}));
    nodes.forEach(n => g.setNode(n.id, { width: n.w || 150, height: n.h || 34 }));
    edges.forEach(e => g.setEdge(e.source, e.target));
    dagre.layout(g);
    return Object.fromEntries(nodes.map(n => [n.id, g.node(n.id)]));
  }

  const depBox = chartBox("tall");
  const showExternal = h("input", { type: "checkbox", id: "ext", checked: true });
  APP.append(section("モジュールの依存（import）",
    h("div", { class: "tools" }, h("label", {}, showExternal, " 外部のパッケージも出す")),
    h("p", { class: "note" }, "矢印は「import する側 → される側」。丸の大きさは行数。src/ のコードを ast で読んで作る。"),
    h("div", { class: "panel" }, depBox)));

  const lines = Object.fromEntries(D.modules.map(m => [m.name, m.lines]));
  chart(depBox, () => {
    const ext = showExternal.checked;
    const edges = D.edges.filter(e => ext || !e.external);
    const ids = [...new Set([...D.modules.map(m => m.name), ...edges.flatMap(e => [e.source, e.target])])];
    const nodes = ids.map(id => ({ id, w: id.startsWith("ext:") ? 110 : 170 }));
    const pos = layout(nodes, edges, "LR");
    const pal = palette();
    return {
      tooltip: { formatter: p => p.dataType === "edge" ? `${p.data.source} → ${p.data.target}` :
        (p.data.name.startsWith("ext:") ? `外部：${p.data.name.slice(4)}` : `${p.data.name}（${lines[p.data.name]} 行）`) },
      series: [{
        type: "graph", layout: "none", roam: true, draggable: true,
        edgeSymbol: ["none", "arrow"], edgeSymbolSize: 8,
        label: { show: true, color: cssVar("--text"), formatter: p => p.data.name.replace(/^ext:/, "") },
        lineStyle: { color: cssVar("--muted"), opacity: 0.6, curveness: 0.1 },
        emphasis: { focus: "adjacency" },
        data: ids.map(id => ({
          name: id, x: pos[id].x, y: pos[id].y,
          symbolSize: id.startsWith("ext:") ? 12 : 18 + Math.sqrt(lines[id] || 1) * 2,
          itemStyle: { color: id.startsWith("ext:") ? cssVar("--muted") : pal[0] },
          label: { position: id.startsWith("ext:") ? "right" : "bottom" },
        })),
        links: edges.map(e => ({ source: e.source, target: e.target, lineStyle: e.external ? { type: "dashed", opacity: 0.35 } : {} })),
      }],
    };
  });
  showExternal.addEventListener("change", () => window.dispatchEvent(new Event("themechange")));

  // スレッドと渡し口：画面 → 核 は call_soon_threadsafe、核 → 画面 は Qt のシグナル
  function enclosing(module, line) {
    const m = D.modules.find(x => x.name === module);
    const fs = (m ? m.functions : []).filter(f => f.line <= line && line < f.line + f.length);
    return fs.sort((a, b) => a.length - b.length)[0];
  }
  function sequence() {
    const threads = D.threads.map(t => `${t.name}（${t.module}:${t.line}）`).join("・");
    const out = ["sequenceDiagram", "  participant UI as 画面のスレッド（Qt）", "  participant CORE as 核のスレッド（asyncio）"];
    for (const c of D.calls) {
      const f = enclosing(c.module, c.line);
      out.push(`  UI->>CORE: ${f ? f.name + "()" : "?"} → call_soon_threadsafe(${c.target.replace(/^self\./, "")})`);
    }
    for (const s of D.signals) {
      const slots = D.connects.filter(c => c.signal.endsWith("." + s.name)).map(c => c.slot.replace(/^(self|win|app|core)\./, ""));
      out.push(`  CORE-->>UI: ${s.name}(${s.args.join(", ")}) → ${slots.join(", ") || "（つなぎ先なし）"}`);
    }
    return { text: out.join("\n"), threads };
  }
  const seq = sequence();
  const seqBox = h("div", { class: "mermaid" });
  APP.append(section("スレッドと渡し口",
    h("p", { class: "note" }, "スレッド：", seq.threads, "。実線は画面 → 核（値だけを渡す）、点線は核 → 画面（Qt のシグナル、キュー接続）。"),
    seqBox, h("details", {}, h("summary", {}, "図の元（Mermaid）"), h("pre", { class: "pre" }, seq.text))));
  let seqCount = 0;
  async function drawSeq() {
    if (!window.mermaid) return;
    window.mermaid.initialize({ startOnLoad: false, theme: isDark() ? "dark" : "default", securityLevel: "strict" });
    const { svg } = await window.mermaid.render("seq" + (++seqCount), seq.text);
    seqBox.innerHTML = svg;
  }
  window.addEventListener("mermaid-ready", drawSeq);
  window.addEventListener("themechange", drawSeq);
  drawSeq();

  APP.append(section("SQLite の表（コードの CREATE TABLE から）", table([
    { key: "name", label: "表" }, { key: "columns", label: "列", text: r => r.columns.join(", ") },
    { key: "module", label: "モジュール" }, { key: "line", label: "行", num: true },
  ], D.tables)));
  APP.append(section("シグナル（核 → 画面）", table([
    { key: "name", label: "シグナル" }, { key: "args", label: "運ぶ値", text: r => r.args.join(", ") },
    { key: "class", label: "クラス" }, { key: "module", label: "モジュール" }, { key: "line", label: "行", num: true },
    { key: "slots", label: "つなぎ先", text: r => D.connects.filter(c => c.signal.endsWith("." + r.name)).map(c => `${c.module}:${c.line} ${c.slot}`).join(" ／ ") },
  ], D.signals)));
  const funcs = D.modules.flatMap(m => m.functions.map(f => ({ ...f, module: m.name })));
  APP.append(section("関数", table([
    { key: "module", label: "モジュール" }, { key: "name", label: "関数" },
    { key: "async", label: "async", text: r => r.async ? "async" : "" },
    { key: "length", label: "行数", num: true }, { key: "line", label: "行", num: true },
  ], funcs)));
  APP.append(section("モジュール", table([
    { key: "name", label: "モジュール" }, { key: "path", label: "ファイル" }, { key: "lines", label: "行数", num: true },
    { key: "classes", label: "クラス", text: r => r.classes.map(c => c.name).join(", ") },
    { key: "imports", label: "import", text: r => r.imports.join(", ") },
  ], D.modules)));
}
