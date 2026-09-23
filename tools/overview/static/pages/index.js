// (a) 入口：今どこにいるか・主な数・各ページへの道
"use strict";
{
  const D = DATA;
  APP.append(
    h("div", { class: "cols" },
      h("div", { class: "panel" },
        h("h3", {}, "いまのフェーズ（goal.md の題）"),
        h("p", {}, h("b", {}, D.phase)),
        h("p", { class: "note" }, "最新のコミット ", h("code", {}, D.head.short), `（${fmtDate(D.head.date)}）`, h("br"), D.head.subject),
        h("h3", {}, "次の一手（SESSION_STATE.md）"),
        h("div", { class: "pre" }, md(D.next))),
      h("div", { class: "panel" },
        h("h3", {}, "これは何か"),
        h("div", { class: "pre" }, md(D.what)),
        h("h3", {}, "段1 のタスク"),
        h("div", {}, ...D.tasks.map(t => h("div", {},
          pill(t.done ? "済み" : "まだ", t.done ? "ok" : ""), " ", h("b", {}, t.id), " ", t.title))))),
    section("主な数", h("div", { class: "grid" },
      ...D.numbers.map(([k, v]) => h("div", { class: "stat" }, h("div", { class: "k" }, k), h("div", { class: "v" }, v))))),
    section("ページ", h("div", { class: "grid wide" },
      ...D.pages.map(p => h("a", { class: "card", href: p.name + ".html" }, h("b", {}, p.title), h("span", {}, p.lead))))),
  );

  const charts = h("div", { class: "cols" }, h("div", { class: "panel" }, h("h3", {}, "時間ごとのコミット"), chartBox("short")),
    h("div", { class: "panel" }, h("h3", {}, "気がかりの種類ごとの件数（詳しくは「気がかり」）"), chartBox("short")));
  APP.append(section("動き", charts));
  const [c1, c2] = charts.querySelectorAll(".chart");
  chart(c1, () => ({
    tooltip: { trigger: "axis" },
    grid: { left: 40, right: 16, top: 16, bottom: 30 },
    xAxis: { type: "category", data: D.per_hour.map(x => x[0]) },
    yAxis: { type: "value", minInterval: 1 },
    series: [{ type: "bar", data: D.per_hour.map(x => x[1]), barMaxWidth: 36 }],
  }));
  const cc = Object.entries(D.concern_counts).sort((a, b) => b[1] - a[1]);
  chart(c2, () => ({
    tooltip: {},
    grid: { left: 200, right: 24, top: 8, bottom: 20 },
    xAxis: { type: "value", minInterval: 1 },
    yAxis: { type: "category", data: cc.map(x => x[0]).reverse() },
    series: [{ type: "bar", data: cc.map(x => x[1]).reverse(), itemStyle: { color: palette()[2] }, barMaxWidth: 18 }],
  }));
  APP.append(section("現在地（SESSION_STATE.md）", h("div", { class: "panel pre" }, md(D.now))));
}
