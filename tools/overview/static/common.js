// 見取り図の共通部品：配色の切り替え・要素の組み立て・絞り込みと並べ替えのできる表・ECharts の図。
"use strict";

const DATA = JSON.parse(document.getElementById("data").textContent);
const APP = document.getElementById("app");

// ── 配色（自動 → ライト → ダーク）。選んだ物だけをこの閲覧者のブラウザに覚える ──
const THEMES = ["auto", "light", "dark"];
const THEME_LABEL = { auto: "自動", light: "ライト", dark: "ダーク" };

function storedTheme() {
  try { return localStorage.getItem("overview-theme") || "auto"; } catch (e) { return "auto"; }
}

function applyTheme(t) {
  if (t === "auto") delete document.documentElement.dataset.theme;
  else document.documentElement.dataset.theme = t;
  document.querySelector(".theme").textContent = "配色：" + THEME_LABEL[t];
  window.dispatchEvent(new Event("themechange"));
}

function isDark() {
  const t = document.documentElement.dataset.theme;
  if (t) return t === "dark";
  return matchMedia("(prefers-color-scheme: dark)").matches;
}

function cssVar(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

document.querySelector(".theme").addEventListener("click", () => {
  const next = THEMES[(THEMES.indexOf(storedTheme()) + 1) % THEMES.length];
  try { localStorage.setItem("overview-theme", next); } catch (e) { /* 覚えられなくても切り替えは効く */ }
  applyTheme(next);
});
matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => window.dispatchEvent(new Event("themechange")));
applyTheme(storedTheme());

// ── 要素の組み立て ──
function h(tag, attrs, ...children) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === null || v === undefined || v === false) continue;
    if (k === "class") el.className = v;
    else if (k === "html") el.innerHTML = v;
    else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else el.setAttribute(k, v === true ? "" : v);
  }
  for (const c of children.flat()) {
    if (c === null || c === undefined || c === false) continue;
    el.append(c instanceof Node ? c : document.createTextNode(String(c)));
  }
  return el;
}

// 文書から取った文の **太字** と `コード` だけを整える（ほかの記法はそのまま文字で出す）
function md(text) {
  const esc = String(text || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  return h("span", { html: esc.replace(/\*\*(.+?)\*\*/g, "<b>$1</b>").replace(/`([^`]+)`/g, "<code>$1</code>") });
}

function section(title, ...children) {
  return h("section", {}, h("h2", {}, title), ...children);
}

function pill(text, kind) {
  return h("span", { class: "pill" + (kind ? " " + kind : "") }, text);
}

function src(doc, line) {
  return h("span", { class: "src" }, line ? `${doc}:${line}` : doc);
}

function short(text, n) {
  text = String(text || "");
  return text.length > n ? text.slice(0, n) + "…" : text;
}

// ── 表：上に絞り込みの入力欄、見出しを押すと並べ替え ──
// columns: [{ key, label, num?, render?(row) → Node|string, text?(row) → 絞り込み・並べ替えに使う文字 }]
function table(columns, rows, opts = {}) {
  const wrap = h("div", {});
  const input = h("input", { type: "search", placeholder: opts.placeholder || "絞り込み（どの列の文字でも）" });
  const count = h("span", { class: "count" });
  const extra = opts.select ? h("select", {}, h("option", { value: "" }, opts.select.label),
    ...opts.select.values.map(v => h("option", { value: v }, v))) : null;
  const tbody = h("tbody");
  const ths = columns.map(c => h("th", { "data-key": c.key }, c.label));
  let sortKey = null, dir = 1;
  const text = (c, r) => c.text ? c.text(r) : (r[c.key] === undefined || r[c.key] === null ? "" : String(r[c.key]));

  function draw() {
    const q = input.value.trim().toLowerCase();
    const sel = extra ? extra.value : "";
    let list = rows.filter(r => (!q || columns.some(c => text(c, r).toLowerCase().includes(q))) &&
      (!sel || text(columns.find(c => c.key === opts.select.key), r) === sel));
    if (sortKey) {
      const c = columns.find(x => x.key === sortKey);
      list = list.slice().sort((a, b) => {
        const x = text(c, a), y = text(c, b);
        const r = c.num ? (Number(x) || 0) - (Number(y) || 0) : x.localeCompare(y, "ja", { numeric: true });
        return r * dir;
      });
    }
    tbody.replaceChildren(...list.map(r => h("tr", {}, ...columns.map(c =>
      h("td", { class: c.num ? "num" : null }, c.render ? c.render(r) : text(c, r))))));
    count.textContent = `${list.length} / ${rows.length} 行`;
  }
  ths.forEach(th => th.addEventListener("click", () => {
    const k = th.dataset.key;
    dir = sortKey === k ? -dir : 1;
    sortKey = k;
    ths.forEach(x => x.removeAttribute("data-dir"));
    th.dataset.dir = dir > 0 ? "asc" : "desc";
    draw();
  }));
  input.addEventListener("input", draw);
  if (extra) extra.addEventListener("change", draw);
  wrap.append(h("div", { class: "tools" }, input, extra, count),
    h("div", { class: "tablewrap" }, h("table", {}, h("thead", {}, h("tr", {}, ...ths)), tbody)));
  draw();
  return wrap;
}

// ── ECharts：配色を変えたら作り直す ──
const PALETTE_LIGHT = ["#3f6fb5", "#2f8a57", "#b7791f", "#c0463a", "#7b5ea7", "#2a8c96", "#8a6d3b", "#5d6b7a"];
const PALETTE_DARK = ["#7aa2f7", "#5cc28a", "#e0a84a", "#ef7a6c", "#b39ddb", "#5fc3cc", "#c9a86a", "#9aa7b5"];

function palette() { return isDark() ? PALETTE_DARK : PALETTE_LIGHT; }

function chart(el, build) {
  let inst = null;
  function render() {
    if (inst) inst.dispose();
    inst = echarts.init(el, isDark() ? "dark" : null, { renderer: "svg" });
    const { after, ...option } = build();
    inst.setOption({
      backgroundColor: "transparent",
      color: palette(),
      textStyle: { fontFamily: "Yu Gothic UI, Meiryo UI, system-ui, sans-serif", color: cssVar("--text") },
      ...option,
    });
    if (after) after(inst);
  }
  render();
  window.addEventListener("themechange", render);
  window.addEventListener("resize", () => inst && inst.resize());
  return () => inst;
}

function chartBox(cls) {
  return h("div", { class: "chart" + (cls ? " " + cls : "") });
}

function fmtDate(iso) {
  return iso ? iso.replace("T", " ").slice(0, 16) : "";
}
