// (i) 分岐：選んだ道・捨てた道・戻る条件・これからの分かれ道
"use strict";
{
  const D = DATA;
  const adr = Object.fromEntries(D.adrs.map(a => [a.id, a]));
  const box = chartBox("tall");
  const depth = h("select", {}, ...[2, 3, 4].map(n => h("option", { value: n, selected: n === 3 }, `開く深さ：${n}`)));
  APP.append(
    h("div", { class: "tools" }, depth, h("span", { class: "legend" },
      h("span", {}, h("i", { style: "background:var(--accent)" }), "選んだ道"),
      h("span", {}, h("i", { style: "background:var(--muted)" }), "捨てた道（理由）"),
      h("span", {}, h("i", { style: "background:var(--warn)" }), "戻る条件（消滅条件）"),
      h("span", {}, h("i", { style: "background:var(--bad)" }), "これからの分かれ道（未決）"))),
    h("p", { class: "note" }, "丸を押すと枝を開け閉めできる。ホイールで拡大、ドラッグで移動。"),
    h("div", { class: "panel" }, box));
  depth.addEventListener("change", () => window.dispatchEvent(new Event("themechange")));

  chart(box, () => {
    const c = { chosen: cssVar("--accent"), rejected: cssVar("--muted"), sunset: cssVar("--warn"), open: cssVar("--bad") };
    const leaf = (name, kind, tip) => ({ name: short(name, 20), tip: tip || name, itemStyle: { color: c[kind], borderColor: c[kind] },
      label: { color: kind === "rejected" ? cssVar("--muted") : cssVar("--text") }, lineStyle: kind === "rejected" ? { type: "dashed" } : undefined });
    const adrNode = a => ({
      name: `ADR ${a.id}`, tip: `${a.title}（${a.status}）`, itemStyle: { color: c.chosen },
      children: [
        { ...leaf("選んだ：" + a.chosen, "chosen") },
        { name: `捨てた道（${a.rejected.length}）`, itemStyle: { color: c.rejected }, lineStyle: { type: "dashed" },
          children: a.rejected.map(x => leaf(x.idea, "rejected", `${x.idea}<br>理由：${x.reason}`)) },
        { name: `戻る条件（${a.sunset.length}）`, itemStyle: { color: c.sunset },
          children: a.sunset.map(x => leaf(x.text, "sunset")) },
      ],
    });
    const root = {
      name: "Utsushimi", itemStyle: { color: c.chosen },
      children: [
        { name: `決定（${D.decisions.length}）`, itemStyle: { color: c.chosen },
          children: D.decisions.map(d => ({ ...leaf(`${d.id} ${d.label}`, "chosen",
            d.text + (d.adrs.length ? `<br>→ ADR ${d.adrs.join("・")}（「ADR」の枝）` : "")) })) },
        { name: `ADR（${D.adrs.length}）`, itemStyle: { color: c.chosen }, children: D.adrs.map(adrNode) },
        { name: `採らなかった案（${D.rejected.length}）`, itemStyle: { color: c.rejected }, lineStyle: { type: "dashed" },
          children: D.rejected.map(x => leaf(x.idea, "rejected", `${x.idea}<br>理由：${x.reason}`)) },
        { name: `これからの分かれ道（${D.open.length}）`, itemStyle: { color: c.open },
          children: D.open.map(x => leaf(`［${x.kind}］${x.label}`, "open", x.text)) },
      ],
    };
    return {
      tooltip: { formatter: p => (p.data.tip || p.data.name) },
      series: [{
        type: "tree", data: [root], orient: "LR", roam: true, initialTreeDepth: Number(depth.value),
        top: 20, bottom: 20, left: 90, right: 320, symbolSize: 9, expandAndCollapse: true,
        label: { position: "left", verticalAlign: "middle", align: "right", fontSize: 12, color: cssVar("--text") },
        leaves: { label: { position: "right", align: "left" } },
        lineStyle: { color: cssVar("--line"), width: 1.4 },
        emphasis: { focus: "descendant" }, animationDuration: 300,
      }],
    };
  });

  const rows = [
    ...D.adrs.flatMap(a => a.rejected.map(x => ({ where: `ADR ${a.id}`, chosen: a.chosen, idea: x.idea, reason: x.reason, back: a.sunset.map(s => s.text).join(" ／ ") }))),
    ...D.rejected.map(x => ({ where: "採らなかった案", chosen: "", idea: x.idea, reason: x.reason, back: "（再提案には新しい根拠が要る）" })),
  ];
  APP.append(section("捨てた道と、戻る条件", table([
    { key: "where", label: "どこで" }, { key: "chosen", label: "選んだ道", render: r => short(r.chosen, 40), text: r => r.chosen },
    { key: "idea", label: "捨てた道" }, { key: "reason", label: "理由" }, { key: "back", label: "戻る条件", render: r => short(r.back, 80), text: r => r.back },
  ], rows)));
  APP.append(section("これからの分かれ道（SESSION_STATE の未決）", table([
    { key: "kind", label: "種類" }, { key: "text", label: "中身" }, { key: "line", label: "出どころ", render: r => src("SESSION_STATE.md", r.line), text: r => String(r.line) },
  ], D.open)));
}
