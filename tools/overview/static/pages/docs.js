// (f) 文書の地図：文書どうしの参照（力学配置）・大きさ・最終更新
"use strict";
{
  const D = DATA;
  const group = id => id.endsWith("/") ? "ディレクトリ" : !id.endsWith(".md") ? "コードと設定" :
    id.startsWith("docs/adr/") ? "ADR" : id.startsWith("docs/specs/") ? "仕様" : id.startsWith("docs/research/") ? "研究" :
    id.startsWith("docs/") ? "docs" : "直下の文書";
  const cats = ["直下の文書", "docs", "仕様", "ADR", "研究", "コードと設定", "ディレクトリ"];
  const lines = Object.fromEntries(D.nodes.map(n => [n.id, n.lines]));
  const inDeg = {}, outDeg = {};
  D.edges.forEach(e => { outDeg[e.source] = (outDeg[e.source] || 0) + e.count; inDeg[e.target] = (inDeg[e.target] || 0) + e.count; });

  const box = chartBox("tall");
  const mode = h("select", {}, h("option", { value: "force" }, "配置：力学（つながりの強さ）"), h("option", { value: "dagre" }, "配置：階層（参照する側 → される側）"));
  APP.append(section("参照のグラフ",
    h("div", { class: "tools" }, mode),
    h("p", { class: "note" }, "丸の大きさは行数、線の太さは参照の回数。凡例を押すと種類ごとに出し入れできる。ドラッグとホイールで動かせる。"),
    h("div", { class: "panel" }, box)));
  mode.addEventListener("change", () => window.dispatchEvent(new Event("themechange")));

  chart(box, () => {
    const ids = [...D.nodes.map(n => n.id), ...D.others];
    let pos = null;
    if (mode.value === "dagre") {
      const g = new dagre.graphlib.Graph();
      g.setGraph({ rankdir: "LR", nodesep: 14, ranksep: 120 });
      g.setDefaultEdgeLabel(() => ({}));
      ids.forEach(id => g.setNode(id, { width: 180, height: 26 }));
      D.edges.forEach(e => g.setEdge(e.source, e.target));
      dagre.layout(g);
      pos = Object.fromEntries(ids.map(id => [id, g.node(id)]));
    }
    return {
      tooltip: { formatter: p => p.dataType === "edge" ? `${p.data.source} → ${p.data.target}（${p.data.value} 回）` :
        `${p.data.name}<br>${lines[p.data.name] ? lines[p.data.name] + " 行・" : ""}参照される ${inDeg[p.data.name] || 0}・参照する ${outDeg[p.data.name] || 0}` },
      legend: { data: cats, top: 0, textStyle: { color: cssVar("--text") } },
      series: [{
        type: "graph", layout: pos ? "none" : "force", roam: true, draggable: true,
        force: { repulsion: 260, edgeLength: [60, 180], gravity: 0.06 },
        categories: cats.map(c => ({ name: c })),
        edgeSymbol: ["none", "arrow"], edgeSymbolSize: 6,
        emphasis: { focus: "adjacency", lineStyle: { width: 3 } },
        label: { show: true, fontSize: 11, color: cssVar("--text"), formatter: p => p.data.name.split("/").filter(Boolean).pop() },
        lineStyle: { color: "source", opacity: 0.4, curveness: 0.15 },
        data: ids.map(id => ({
          name: id, category: cats.indexOf(group(id)),
          symbolSize: lines[id] ? 8 + Math.sqrt(lines[id]) * 1.3 : 8,
          ...(pos ? { x: pos[id].x, y: pos[id].y } : {}),
        })),
        links: D.edges.map(e => ({ source: e.source, target: e.target, value: e.count, lineStyle: { width: 0.6 + Math.log2(e.count + 1) } })),
      }],
    };
  });

  APP.append(section("文書", table([
    { key: "id", label: "文書" }, { key: "title", label: "1行目", render: r => short(r.title, 50), text: r => r.title },
    { key: "lines", label: "行数", num: true },
    { key: "updated", label: "最終更新", text: r => fmtDate(r.updated) },
    { key: "in", label: "参照される", num: true, text: r => String(inDeg[r.id] || 0) },
    { key: "out", label: "参照する", num: true, text: r => String(outDeg[r.id] || 0) },
  ], D.nodes)));
  APP.append(section("参照先の無い参照（気がかりにも出る）", table([
    { key: "doc", label: "文書" }, { key: "line", label: "行", num: true }, { key: "ref", label: "参照", render: r => h("code", {}, r.ref) },
  ], D.dangling)));
}
