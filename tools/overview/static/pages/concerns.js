// (h) 気がかり：機械で見つけた匂いと、文書に書いてある懸念。判定はしない（判定は主人）
"use strict";
{
  const D = DATA;
  APP.append(h("div", { class: "panel" },
    h("b", {}, "ここに並ぶのは候補であって、問題と決まった物ではない。"),
    " 出どころ（文書と行）を見て、主人が判断する。コードの目安：関数 ", D.thresholds.long_function, " 行・ファイル ", D.thresholds.big_file, " 行を超えたら出す。"));

  const sum = chartBox("short");
  APP.append(section("種類ごとの件数", h("div", { class: "panel" }, sum)));
  const groupOf = k => Object.entries(D.groups).find(([, ks]) => ks.includes(k))[0];
  chart(sum, () => {
    const pal = palette();
    const gcol = { "文書の匂い": pal[3], "書いてある懸念": pal[2], "コードの匂い": pal[4] };
    return {
      tooltip: {},
      grid: { left: 40, right: 16, top: 30, bottom: 90 },
      legend: { top: 0, data: Object.keys(D.groups) },
      xAxis: { type: "category", data: D.kinds, axisLabel: { rotate: 35, fontSize: 11 } },
      yAxis: { type: "value", minInterval: 1 },
      series: Object.keys(D.groups).map(g => ({
        name: g, type: "bar", stack: "all", barMaxWidth: 30, itemStyle: { color: gcol[g] },
        data: D.kinds.map(k => groupOf(k) === g ? (D.counts[k] || 0) : 0),
      })),
    };
  });

  const tm = chartBox();
  APP.append(section("コードの大きさ（ファイル → 関数。面積は行数、赤いほど長い）", h("div", { class: "panel" }, tm)));
  chart(tm, () => {
    const lim = D.thresholds.long_function;
    const color = v => v > lim ? cssVar("--bad") : v > lim / 2 ? cssVar("--warn") : palette()[0];
    return {
      tooltip: { formatter: p => `${p.treePathInfo.map(x => x.name).filter(Boolean).join(" › ")}<br>${p.value} 行` },
      series: [{
        type: "treemap", roam: false, nodeClick: "zoomToNode", breadcrumb: { show: true },
        label: { show: true, formatter: "{b}", fontSize: 11 }, upperLabel: { show: true, height: 20, color: cssVar("--text") },
        levels: [{ itemStyle: { borderColor: cssVar("--panel"), borderWidth: 0, gapWidth: 4 } },
          { itemStyle: { borderColor: cssVar("--panel-2"), borderWidth: 3, gapWidth: 1 } }, { itemStyle: { borderColor: cssVar("--panel"), borderWidth: 1 } }],
        data: D.code_tree.map(f => ({ name: f.name, children: f.children.map(c => ({ ...c, itemStyle: { color: color(c.value) } })) })),
      }],
    };
  });

  for (const [g, kinds] of Object.entries(D.groups)) {
    const rows = D.items.filter(x => kinds.includes(x.kind));
    APP.append(section(`${g}（${rows.length}）`, rows.length ? table([
      { key: "kind", label: "種類", render: r => pill(r.kind, g === "書いてある懸念" ? "warn" : "bad") },
      { key: "where", label: "出どころ", text: r => r.line ? `${r.doc}:${r.line}` : r.doc, render: r => src(r.doc, r.line) },
      { key: "text", label: "中身" },
    ], rows, { select: { key: "kind", label: "種類：すべて", values: kinds.filter(k => D.counts[k]) } }) : h("p", { class: "note" }, "なし")));
  }
}
