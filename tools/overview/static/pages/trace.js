// (c) 追跡：BH → 段 → タスク → 済み。保護指定・禁則・lessons の届き先
"use strict";
{
  const D = DATA;
  const flowBox = chartBox("tall");
  APP.append(section("流れ：章 → 段 → タスク → 済み／まだ",
    h("p", { class: "note" }, "線の太さは BH の数（1つの BH が複数のタスクに分かれるときは等分）。requirements.md の「段」と「タスク」、tasks.md の ☑ から作る。"),
    h("div", { class: "panel" }, flowBox)));
  chart(flowBox, () => {
    const names = [...new Set(D.links.flatMap(l => [l.source, l.target]))];
    const col = n => n === "済み" ? cssVar("--ok") : n === "まだ" ? cssVar("--warn") : n.startsWith("（") ? cssVar("--muted") : null;
    return {
      tooltip: { trigger: "item" },
      series: [{
        type: "sankey", left: 10, right: 90, top: 10, bottom: 10, nodeGap: 10, emphasis: { focus: "adjacency" },
        data: names.map(n => ({ name: n, itemStyle: col(n) ? { color: col(n) } : undefined })),
        links: D.links, lineStyle: { color: "gradient", opacity: 0.35 },
        label: { color: cssVar("--text"), fontSize: 12 },
      }],
    };
  });

  // BH × タスク の行列（段1 の BH だけ）
  const stage1 = D.rows.filter(r => r.stage === "段1");
  const taskIds = D.tasks.map(t => t.id);
  const done = Object.fromEntries(D.tasks.map(t => [t.id, t.done]));
  const inCond = Object.fromEntries(D.tasks.map(t => [t.id, new Set(t.bh)]));
  const matBox = chartBox("tall");
  APP.append(section("行列：段1 の BH × タスク",
    h("p", { class: "note" }, "濃い色＝requirements のタスク欄にあり、そのタスクの完了条件にも出る。薄い色＝タスク欄にだけある。緑はタスクが ☑。"),
    h("div", { class: "panel" }, matBox)));
  chart(matBox, () => {
    const cells = [];
    stage1.forEach((r, y) => taskIds.forEach((t, x) => {
      if (!r.tasks.includes(t)) return;
      cells.push([x, y, (inCond[t].has(r.id) ? 2 : 1) + (done[t] ? 10 : 0)]);
    }));
    const base = v => v >= 10 ? cssVar("--ok") : cssVar("--accent");
    return {
      tooltip: { formatter: p => `${stage1[p.value[1]].id} × ${taskIds[p.value[0]]}<br>${short(stage1[p.value[1]].text, 60)}<br>` +
        ((p.value[2] % 10) === 2 ? "完了条件に出る" : "タスク欄にだけある") + (p.value[2] >= 10 ? "（☑）" : "") },
      grid: { left: 70, right: 20, top: 30, bottom: 20 },
      xAxis: { type: "category", data: taskIds, position: "top", splitLine: { show: true } },
      yAxis: { type: "category", data: stage1.map(r => r.id), inverse: true, splitLine: { show: true } },
      series: [{
        type: "scatter", symbol: "roundRect", symbolSize: [26, 12],
        data: cells.map(v => ({ value: v, itemStyle: { color: base(v[2]), opacity: (v[2] % 10) === 2 ? 0.95 : 0.35 } })),
      }],
    };
  });

  APP.append(section("振る舞い BH の一覧", table([
    { key: "id", label: "BH" },
    { key: "chapter", label: "章" },
    { key: "text", label: "ふるまい", text: r => r.text, render: r => short(r.text, 90) },
    { key: "priority", label: "優先度" },
    { key: "stage", label: "段", render: r => pill(r.stage, r.stage === "段1" ? "accent" : "") },
    { key: "tasks", label: "タスク", text: r => r.tasks.join(" ") },
    { key: "state", label: "状態", render: r => pill(r.state, r.state === "済み" ? "ok" : r.state === "まだ" ? "warn" : "") },
    { key: "design", label: "design の節", text: r => r.design.join(" ／ "), render: r => short(r.design.join(" ／ "), 60) },
    { key: "predecessor", label: "前身での状況", render: r => short(r.predecessor, 30), text: r => r.predecessor },
  ], D.rows, { select: { key: "state", label: "状態：すべて", values: ["済み", "まだ", "送った"] } })));

  const reachCols = [
    { key: "design", label: "design の行", text: r => r.reach.design.join(", "), render: r => r.reach.design.length ? r.reach.design.join(", ") : pill("無し", "warn") },
    { key: "tasks", label: "タスク（完了条件・説明）", text: r => r.reach.tasks_by_id.join(" "), render: r => r.reach.tasks_by_id.length ? r.reach.tasks_by_id.join(" ") : pill("無し", "warn") },
    { key: "req", label: "requirements の行", text: r => r.reach.requirements.join(", ") },
  ];
  APP.append(section("保護指定（CLAUDE.md §0）の届き先", table([{ key: "id", label: "保護指定" }, { key: "text", label: "中身" }, ...reachCols], D.protected)));
  APP.append(section("禁則（design.md §6 の4つ）の届き先", table([{ key: "text", label: "禁則" }, { key: "guarantee", label: "設計での担保", render: r => short(r.guarantee, 80) }, ...reachCols], D.rules)));
  APP.append(section("lessons の項目の届き先", table([{ key: "id", label: "項目" }, { key: "title", label: "題" }, ...reachCols], D.lessons)));
  APP.append(section("タスク（tasks.md）", table([
    { key: "id", label: "タスク" }, { key: "title", label: "題" },
    { key: "done", label: "☑", render: r => pill(r.done ? "済み" : "まだ", r.done ? "ok" : ""), text: r => r.done ? "済み" : "まだ" },
    { key: "conditions", label: "完了条件の数", num: true, text: r => String(r.conditions.length) },
    { key: "bh", label: "完了条件に出る BH", text: r => r.bh.join(" ") },
    { key: "lessons", label: "完了条件に出る lessons", text: r => r.lessons.join(" ") },
    { key: "smoke", label: "手順書の項目", text: r => D.smoke.filter(s => s.tasks.includes(r.id)).map(s => s.id).join(" ") },
  ], D.tasks)));
}
