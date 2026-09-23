// (d) 決定：D 番号・ADR・採らなかった案
"use strict";
{
  const D = DATA;
  APP.append(section("決定（SESSION_STATE.md「決定（蒸し返さない）」）", table([
    { key: "id", label: "番号", text: r => r.id },
    { key: "text", label: "決定" },
    { key: "date", label: "日付（本文から）" },
    { key: "line", label: "出どころ", render: r => src("SESSION_STATE.md", r.line), text: r => String(r.line) },
  ], D.decisions, { placeholder: "決定を絞り込み" })));

  const adrBox = h("div", { class: "grid wide" });
  for (const a of D.adrs) {
    adrBox.append(h("div", { class: "panel" },
      h("h3", {}, `ADR ${a.id}　`, pill(a.status, a.status === "採用" ? "ok" : "warn")),
      h("p", {}, h("b", {}, a.title)),
      h("p", { class: "note" }, `日付：${a.date}　決めた人：${a.by}　`, src(a.path)),
      h("details", {}, h("summary", {}, `却下した案（${a.rejected.length}）`),
        h("ul", {}, ...a.rejected.map(x => h("li", {}, h("b", {}, x.idea), "：", x.reason)))),
      h("details", {}, h("summary", {}, `消滅条件（${a.sunset.length}）`),
        h("ul", {}, ...a.sunset.map(x => h("li", {}, x.text)))),
      h("details", {}, h("summary", {}, `引き受けるもの（${a.accepted.length}）`),
        h("ul", {}, ...a.accepted.map(x => h("li", {}, x.text))))));
  }
  APP.append(section("ADR（docs/adr/）", adrBox));

  const rejected = [
    ...D.adrs.flatMap(a => a.rejected.map(x => ({ from: `ADR ${a.id}`, idea: x.idea, reason: x.reason, where: `${a.path}:${x.line}` }))),
    ...D.rejected.map(x => ({ from: "採らなかった案", idea: x.idea, reason: x.reason, where: `SESSION_STATE.md:${x.line}` })),
  ];
  APP.append(section("捨てた道（ADR の却下した案と、SESSION_STATE の採らなかった案）", table([
    { key: "from", label: "どこで" }, { key: "idea", label: "案" }, { key: "reason", label: "理由" },
    { key: "where", label: "出どころ", render: r => h("span", { class: "src" }, r.where) },
  ], rejected, { select: { key: "from", label: "どこで：すべて", values: [...new Set(rejected.map(r => r.from))] } })));
}
