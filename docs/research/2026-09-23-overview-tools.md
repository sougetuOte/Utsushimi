# 俯瞰ツール「見取り図」の道具選び（2026-09-23）

**証拠であって決定ではない。**道具は `tools/overview/`、使い方は `README.md`「開発」。
**消滅条件**：見取り図の描画を別の道具に替えたら、または見取り図そのものをやめたら消す。
採った JS ライブラリの版を上げたら、その行だけ直す。

調べ方：2026-09-23 に Claude Code（Opus 5.5）のサブエージェントが、ウェブ検索・Context7・npm レジストリ・jsDelivr・GitHub API・PyPI を引いて調べた。
版は `https://registry.npmjs.org/<名前>/latest` と `https://data.jsdelivr.com/v1/packages/npm/<名前>@<版>`、
許諾は npm の `license` と GitHub の表示で確かめた。
ECharts は Context7 の公式 handbook（v6 の実行中のテーマ切り替え `setTheme`）と echarts-doc（graph の `layout` は `none` / `circular` / `force` だけ）を引いた。
dagre は Node 24 で読み込み、階層レイアウトの座標が出ることまで確かめた。

## 前提

材料は日本語の独自の表（BH・D・T・ADR の各節）である。道具はリポジトリの中身を読み、静的な HTML を作り直す。
リポジトリの規模は `.py` 6本・`.md` 18本・コミット22件（2026-09-23、`git ls-files` と `git log` で数えた）。

## 既存の道具（丸ごと使う候補）

| 名前 | 何をするか | 保守（最終リリース） | 許諾 | 採否 | 理由 |
|---|---|---|---|---|---|
| githubocto/repo-visualizer | ファイル構成を D3 の円で SVG にする GitHub Action | アーカイブ済み（0.9.1、2023-04） | MIT | 採らない | 止まっている。大きさを見せるだけで、文書の中身は読めない |
| Gource | git の履歴をアニメーションにする | 0.56（2026-03） | GPL-3.0 | 採らない | 出力が動画か窓で、静的な HTML に埋め込めない |
| git-truck | git の履歴をツリーマップで見せる | npm 5.0.0（2026-06） | MIT | 採らない（見せ方を参考にした） | ローカルのサーバーで動く形で、静的な書き出しではない。気がかりのツリーマップの見せ方を参考にした |
| emerge | Python などの依存と指標を解析し、D3 の静的 HTML にする | PyPI 2.0.7（2024-08） | MIT | 採らない（形を参考にした） | 「解析結果を静的 HTML に埋める」形は最も近いが、リリースが2年止まっていて、この規模には過剰 |
| pydeps | Python の import 依存を Graphviz で SVG にする | 3.0.8（2026-09） | BSD-2-Clause | 採らない | Graphviz の導入が要る。固定の絵で、配色の切り替えも絞り込みもできない |
| pyan3 | Python の呼び出しグラフ | 2.8.1（2026-08） | GPL-2.0-or-later | 採らない | 呼び出しグラフは9ページに無い。GPL なので組み込みを避けたい |
| code2flow | 呼び出しのフロー図 | 2.5.1（2023-01） | MIT | 採らない | 止まっている |
| Doorstop | 要求を YAML で1件ずつ管理し、追跡を出す | 3.2（2026-07） | LGPLv3 | 採らない | 独自の YAML が前提。日本語の表は読めず、移せば文書が二重になる |
| StrictDoc・sphinx-needs | 要求の追跡（独自の書式か Sphinx の指令） | 0.30.1・8.5.0（2026-09） | Apache-2.0・MIT | 採らない | Doorstop と同じ。文書をその書式で書き直すことになる |
| CodeCharta | 指標を 3D のコード都市やツリーマップにする | 2.5.3（2026-09） | BSD-3-Clause | 採らない | 大きなアプリで、1ページに埋めるには重い |
| MkDocs Material | Markdown から静的サイトを作る | 9.7.7（2026-07） | MIT | 採らない | 文書を並べるだけで、表を図にしない。土台の mkdocs が移行期にある |
| grimp・import-linter | Python の import グラフ／層の規則の検査 | 3.17・2.15（2026-09） | BSD-2-Clause | 今は採らない | 今の規模は標準の `ast` で足りる。大きくなったら grimp が候補 |

**自作にした理由**：要求の追跡の道具は、どれも「その道具の書式で書く」ことが前提で、今の日本語の表をそのまま読める物が無い。
コードの解析も、この規模では標準の `ast` と `subprocess` の `git` で足りる。

## JS ライブラリ（生成した HTML がブラウザで読む物）

CDN は jsDelivr。版を固定して読む（`tools/overview/build.py` の先頭）。

| 名前 | 版 | 許諾 | 読み方 | 使う所 | 採否 |
|---|---|---|---|---|---|
| **Apache ECharts** | **6.1.0**（2026-05-19） | Apache-2.0 | `echarts@6.1.0/dist/echarts.min.js`（UMD、`<script>` 1本） | 年表の時間軸・追跡のサンキーと行列・構造と文書の地図のグラフ・前身のサンキーと棒・気がかりのツリーマップ・分岐の木 | **採る（主軸）** |
| **@dagrejs/dagre** | **3.1.1**（2026-08-08） | MIT | `@dagrejs/dagre@3.1.1/dist/dagre.min.js`（IIFE、graphlib を同梱） | モジュールの依存と文書の地図の、階層の座標を出す（ECharts の graph には階層の配置が無い） | **採る** |
| **Mermaid** | **11.17.2**（2026-08-25） | MIT | `mermaid@11.17.2/dist/mermaid.esm.min.mjs`（ESM。図の種類ごとの部品は要るときだけ読む） | 本体の構造の、スレッドと渡し口のシーケンス図（1ページだけ） | **採る**。12.0.0（2026-09-10）は破壊的な変更を含み出たばかりなので、11 系の最後の版にした |
| Cytoscape.js・cytoscape-dagre | 3.34.3・4.0.1 | MIT | UMD | 本格的なグラフの操作 | 今は採らない（ノードは数十で、ECharts の graph で足りる） |
| elkjs | 0.12.0 | EPL-2.0 OR GPL-3.0-or-later | 1.6MB | 高品質な階層の配置 | 採らない（重い。許諾が面倒） |
| D3・d3-sankey | 7.9.0・0.12.3 | ISC・BSD-3-Clause | UMD | 何でも描けるが全部手で書く | 採らない（ECharts に内蔵。d3-sankey は 2019 年から止まっている） |
| vis-timeline | 8.5.4 | Apache-2.0 OR MIT | UMD と CSS | 年表 | 採らない（22件なら ECharts の時間軸で足りる。テーマが別の系統になる） |
| Tabulator | 6.5.3 | MIT | UMD | 表 | 採らない（数十行の表は、自前の数十行の JS で絞り込みと並べ替えができる。要るとわかったら入れる） |
| Grid.js | 6.2.0 | MIT | UMD | 表 | 採らない（2024-03 から止まっている） |
| MiniSearch・Fuse.js | 7.2.0・7.5.0 | MIT・Apache-2.0 | UMD・ESM | ページをまたぐ検索 | 今は採らない（各表に絞り込みがある。日本語には分割の指定が要る） |

## Python 側

- git の履歴：`subprocess` で `git log` を読む（GitPython・PyDriller は要らない）
- import の依存・関数の長さ・広い例外の受け止め：標準の `ast`（radon は 2023-03 から止まっていて、Python 3.14 で動くかを確かめていない）
- Markdown の表：行単位の自前の読み取り（独自の日本語の表を読むため）
- 依存の追加：無し（`pyproject.toml` は変えていない）

## 確かめていないこと

- cytoscape-dagre を `<script>` で読んだときに自動で登録されるか（採っていないので確かめない）
- Mermaid 12 で、シーケンス図に影響する変更があるか（11.17.2 に固定したので、上げるときに確かめる）
