// (b) 年表：コミット・フェーズ・検収・決定を時間の軸に
"use strict";
{
  const D = DATA;
  const kinds = [...new Set(D.commits.map(c => c.kind))].sort();
  const lanes = ["決定（D の初出）", "検収", ...kinds];
  const box = chartBox("tall");
  APP.append(
    h("p", { class: "note" }, "帯はフェーズ（goal.md の版の題）。点を押すと下の表で探せる。マウスのホイールで拡大、下の帯で範囲を選ぶ。"),
    h("div", { class: "panel" }, box));

  chart(box, () => {
    const pal = palette();
    const bands = D.phases.map((p, i) => [{ name: p.title, xAxis: p.start, itemStyle: { color: pal[i % pal.length], opacity: 0.08 } }, { xAxis: p.end }]);
    return {
      tooltip: {
        formatter: p => {
          const d = p.data.meta || {};
          return [`<b>${d.title || ""}</b>`, fmtDate(d.date), ...(d.lines || [])].join("<br>");
        },
      },
      grid: { left: 150, right: 30, top: 40, bottom: 80 },
      dataZoom: [{ type: "inside" }, { type: "slider", bottom: 20 }],
      xAxis: { type: "time" },
      yAxis: { type: "category", data: lanes, inverse: true },
      legend: { top: 0, data: ["コミット", "検収 PASS", "検収 FAIL", "決定"] },
      series: [
        {
          name: "コミット", type: "scatter",
          data: D.commits.map(c => ({
            value: [c.date, c.kind], symbolSize: 8 + Math.min(c.files, 30) / 2,
            meta: { title: `${c.short} ${c.subject}`, date: c.date, lines: [`種類：${c.kind}・ファイル ${c.files}`, ...c.notes.map(n => "解釈：" + short(n, 80))] },
          })),
          markArea: { silent: true, label: { position: "insideTop", color: cssVar("--muted"), fontSize: 11 }, data: bands },
        },
        {
          name: "検収 PASS", type: "scatter", symbol: "diamond", symbolSize: 16, itemStyle: { color: cssVar("--ok") },
          data: D.reviews.filter(r => r.result === "PASS").map(r => ({ value: [r.date, "検収"], meta: { title: `${r.commit} 検収 PASS`, date: r.date, lines: [short(r.text, 100)] } })),
        },
        {
          name: "検収 FAIL", type: "scatter", symbol: "diamond", symbolSize: 16, itemStyle: { color: cssVar("--bad") },
          data: D.reviews.filter(r => r.result === "FAIL").map(r => ({ value: [r.date, "検収"], meta: { title: `${r.commit} 検収 FAIL`, date: r.date, lines: [short(r.text, 100)] } })),
        },
        {
          name: "決定", type: "scatter", symbol: "pin", symbolSize: 22, itemStyle: { color: cssVar("--warn") },
          label: { show: false },
          data: D.decisions.map((d, i) => ({ value: [d.date, "決定（D の初出）"], meta: { id: d.id, title: `${d.id}（${d.commit} で初出）`, date: d.date, lines: [short(d.text, 100)] } })),
        },
      ],
      after: inst => inst.on("click", p => {
        const q = document.querySelector("#commits input");
        if (q && p.data.meta) { q.value = (p.data.meta.title || "").split(" ")[0]; q.dispatchEvent(new Event("input")); }
      }),
    };
  });

  APP.append(section("フェーズ", table(
    [{ key: "title", label: "フェーズ" }, { key: "start", label: "始まり", text: r => fmtDate(r.start) },
     { key: "end", label: "終わり（次の版まで）", text: r => fmtDate(r.end) }, { key: "commit", label: "G0 のコミット" }], D.phases)));

  APP.append(h("section", { id: "commits" }, h("h2", {}, "コミット（古い順）"), table(
    [{ key: "date", label: "日時", text: r => fmtDate(r.date) }, { key: "short", label: "ID", render: r => h("code", {}, r.short) },
     { key: "kind", label: "種類", render: r => pill(r.kind, "accent") }, { key: "subject", label: "件名" },
     { key: "files", label: "ファイル", num: true },
     { key: "notes", label: "SESSION_STATE の解釈", text: r => r.notes.join(" ／ ") }],
    D.commits, { select: { key: "kind", label: "種類：すべて", values: kinds } })));

  APP.append(section("検収", table(
    [{ key: "date", label: "日時", text: r => fmtDate(r.date) }, { key: "commit", label: "コミット" },
     { key: "result", label: "結果", render: r => pill(r.result, r.result === "PASS" ? "ok" : "bad") }, { key: "text", label: "コミットメッセージの文" }],
    D.reviews)));
}
