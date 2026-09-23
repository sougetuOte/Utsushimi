// (g) 前身とのずれ：前身から引き継いだ物と、今の設計・実装の対応
"use strict";
{
  const D = DATA;
  if (!D.found) APP.append(h("div", { class: "panel" }, pill("前身が見つからない", "bad"), " 前身の置き場が無いので、参照先の有無は「不明」になる。"));

  const flow = chartBox();
  APP.append(section("前身での状況 → 今の段と状態（BH ごと）",
    h("p", { class: "note" }, "左は behaviors.md の「前身での状況」、右は requirements.md の段と tasks.md の ☑。前身で実装済みだった物が、今どこにあるか。"),
    h("div", { class: "panel" }, flow)));
  chart(flow, () => {
    const L = s => "前身：" + s, R = s => "今：" + s;
    const names = [...new Set(D.status.flatMap(x => [L(x.predecessor), R(x.now)]))];
    const col = n => n.includes("済み") ? cssVar("--ok") : n.includes("まだ") ? cssVar("--warn") : n.includes("以降") ? cssVar("--muted") : null;
    return {
      tooltip: {},
      series: [{
        type: "sankey", left: 10, right: 120, nodeGap: 14, emphasis: { focus: "adjacency" },
        data: names.map(n => ({ name: n, itemStyle: col(n) ? { color: col(n) } : undefined })),
        links: D.status.map(x => ({ source: L(x.predecessor), target: R(x.now), value: x.count })),
        lineStyle: { color: "gradient", opacity: 0.35 }, label: { color: cssVar("--text") },
      }],
    };
  });

  APP.append(section("段と前身のフェーズ（concept.md §3）", table([
    { key: "stage", label: "段" }, { key: "title", label: "段の題" },
    { key: "predecessor", label: "前身" }, { key: "predecessor_title", label: "前身の題" },
    { key: "line", label: "出どころ", render: r => src("docs/concept.md", r.line), text: r => String(r.line) },
  ], D.stages)));

  // 前身の文書への参照：どのファイルが何回引かれているか
  const per = {};
  D.refs.forEach(r => { per[r.path] = (per[r.path] || 0) + 1; });
  const top = Object.entries(per).sort((a, b) => b[1] - a[1]).slice(0, 25);
  const bar = chartBox("tall");
  APP.append(section("よく引かれている前身のファイル（上位25）",
    h("p", { class: "note" }, `前身への参照 ${D.refs.length} 件・ファイル ${D.files.length} 本。赤は前身の置き場に見つからない物。`),
    h("div", { class: "panel" }, bar)));
  const missing = new Set(D.refs.filter(r => r.exists === false).map(r => r.path));
  chart(bar, () => ({
    tooltip: {},
    grid: { left: 360, right: 30, top: 10, bottom: 20 },
    xAxis: { type: "value", minInterval: 1 },
    yAxis: { type: "category", data: top.map(x => x[0]).reverse(), axisLabel: { fontSize: 11 } },
    series: [{ type: "bar", barMaxWidth: 14,
      data: top.map(x => ({ value: x[1], itemStyle: { color: missing.has(x[0]) ? cssVar("--bad") : palette()[0] } })).reverse() }],
  }));

  const state = r => r.exists === null ? "開かない（data・.env）" : r.exists === false ? "無い" : r.range_ok === false ? "行が範囲外" : "ある";
  APP.append(section("前身への参照の一覧", table([
    { key: "doc", label: "今の文書", render: r => src(r.doc, r.line), text: r => `${r.doc}:${r.line}` },
    { key: "section", label: "節", render: r => short(r.section, 30), text: r => r.section },
    { key: "path", label: "前身のファイル", render: r => h("code", {}, r.path) },
    { key: "range", label: "行", text: r => r.from ? (r.to && r.to !== r.from ? `${r.from}-${r.to}` : String(r.from)) : "" },
    { key: "k_lines", label: "前身の行数", num: true, text: r => r.k_lines === null ? "" : String(r.k_lines) },
    { key: "state", label: "有無", text: state, render: r => pill(state(r), state(r) === "ある" ? "ok" : "bad") },
  ], D.refs, { select: { key: "state", label: "有無：すべて", values: ["ある", "無い", "行が範囲外", "開かない（data・.env）"] } })));

  APP.append(section("持ち越さなかったもの（CLAUDE.md §4）", table([
    { key: "item", label: "前身" }, { key: "reason", label: "理由" },
  ], D.not_carried)));
  APP.append(section("振る舞いごとの対応", table([
    { key: "id", label: "BH" }, { key: "text", label: "ふるまい", render: r => short(r.text, 70), text: r => r.text },
    { key: "priority", label: "前身の優先度" }, { key: "predecessor", label: "前身での状況" }, { key: "stage", label: "今の段" },
  ], D.behaviors)));
}
