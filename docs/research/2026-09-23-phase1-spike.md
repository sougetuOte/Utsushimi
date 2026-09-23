# Phase 1 スパイク：常駐 GUI の核を3候補で測る（2026-09-23）

**証拠であって決定ではない。**決定は `docs/adr/0001`〜`0004`。
**消滅条件**：段1の最初のタスクで本体が実起動したら、`spikes/` ごと消す。本書は ADR の根拠として残し、
ADR が置き換えられたら本書も消す。

調べ方：3候補を `spikes/` に同じ約束（`spikes/README.md`）で書き、`spikes/tools/check.py` で合成したマウス・キー入力と
UI オートメーションで動かして測った（Claude Code、Opus 5.5）。**見た目の出来は測っていない**（窓が動く・隠れる・出るの事実だけ）。

環境：Windows 11 Pro 10.0.26200.9550。画面 2560×1440 が2枚、拡大率 125%。Python 3.11.9、Rust 1.97.0（stable-msvc）、
Node 24.13.0、.NET SDK 10.0.401（本フェーズで主人の許可を得て winget で導入）、
Python 3.14.7（同じく許可を得て uv を 0.12.18 に上げ、uv 管理で導入）、WebView2 153.0、PowerShell 7.6.6。

## 候補

| 候補 | 中身 | 版 |
|---|---|---|
| **pyside6** | Python ＋ Qt。トレイは `QSystemTrayIcon`、裏の待ちは `threading` ＋ Qt のシグナル | PySide6 6.11.2、sqlite3（標準）。Python 3.11.9（SQLite 3.45.1）で測り、ADR 0001 の版選定の後に 3.14.7（SQLite 3.53.1）で測り直した |
| **tauri** | Rust ＋ WebView2。画面は HTML/JS、トレイは `tray-icon` 機能、裏の待ちは Rust のスレッド ＋ イベント | tauri 2.11.6、tauri-cli 2.11.5、rusqlite 0.40.2（bundled） |
| **wpf** | C# ＋ WPF。トレイは WinForms の `NotifyIcon`（WPF 単体にトレイは無い）、裏の待ちは `Task.Run` | .NET 10、Microsoft.Data.Sqlite 10.0.12 |

## 結果（S1〜S7）

最終の計測は3候補とも同じ `check.py` で、2026-09-23 16:24 前後に続けて行った。**3候補とも7項目すべて「可」。**
pyside6 は Python 3.14.7 に作り直した venv でもう一度測り、7項目すべて「可」だった（S5 の打つ回の最大間隔 23ms、ドラッグを含む回 198ms）。

| 項目 | pyside6 | tauri | wpf | 手段 |
|---|---|---|---|---|
| S1 枠なしの窓をドラッグで動かせる | 可 | 可 | 可 | 帯を +120,+80 ドラッグ → 見えている窓の範囲（`DwmGetWindowAttribute` の EXTENDED_FRAME_BOUNDS）がちょうど +120,+80 動いた |
| S2 ヘリと内側を区別して受ける | 可 | 可 | 可 | 左縁から 2px を1回・中央を1回クリック → ログに `poke edge` 1件・`click inner` 1件 |
| S3 閉じるとトレイに隠れ、トレイから表示・終了できる | 可 | 可 | 可 | 「×」→ `IsWindowVisible=False` でプロセスは生存。トレイのアイコンを左クリック → `IsWindowVisible=True`。右クリック →「終了」→ `shutdown count=1` が1行、3秒後にプロセスが消えた（`spikes/tools/tray.ps1`） |
| S4 1発言ごとの記録が強制終了の直後にも残る | 可 | 可 | 可 | 自動送信の `send id=1` がログに出た直後に `taskkill /F` → DB を開くと「一言目」が1行 |
| S5 裏の待ちの最中も打てて、窓を動かせる | 可 | 可 | 可 | 4秒の待ちの 0.6 秒目に「abc」を打つ → 待ちの終わりに入力欄が「abc」。UI タイマー（20ms 刻み）の最大間隔 pyside6 29ms・tauri 22ms・wpf 50ms。次の待ちの最中に帯を -60,-40 ドラッグ → その分動いた |
| S6 2回目の起動で前回の記録を読む | 可 | 可 | 可 | S4 の後にもう一度起動 → `start … loaded=1` |
| S7 日常の起動方法で、コンソール窓を出さずに起動 | 可 | 可 | 可 | ショートカット（.lnk）を作って `explorer.exe` で開く（ダブルクリックと同じシェル経路）→ `start … console=none`。pyside6 は `pythonw.exe` を指す |

### S4 と S6 の再現手順

```
python spikes/tools/check.py <候補>     # 用意は spikes/README.md
cat spikes/<候補>/run-check/result.txt  # S4 と S6 の行
```

`check.py` は `spikes/<候補>/run-check/` を消して作り直してから、(1) `--auto-send 一言目 --bg-seconds 5` で起動 →
ログに `send id=` が出たら、ログの `pid=` を `taskkill /F` → `spike.db` の `messages` で「一言目」を数える（S4）、
(2) 同じ `--run-dir` で起動し直して `start` 行の `loaded=` を読む（S6）。

### 途中で「不可」になったもの（原因と直し方）

- **tauri の S1・S2（初回は不可）**
  - S1：`capabilities` の `core:default` に、窓を動かす `core:window:allow-start-dragging` が入っていない。足して可になった。
  - S2：**計測側の誤り。**影つきの枠なし窓は `GetWindowRect` が見えないリサイズ用の縁（左右に約9px）を含む。
    「左縁から2px」が窓の外に当たっていた。見えている範囲（DWM）で測るよう `check.py` を直し、3候補とも測り直した。
- **wpf の S5（初回は不可、207ms）**：最初は「打つ」と「ドラッグ」を同じ待ちの中で行い、間隔の閾値を 200ms にしていた。
  pyside6 も 191ms で、どちらもドラッグ中の値だった。Windows の移動ループが UI スレッドを占める分が、裏の待ちの影響と混ざる。
  打つ回とドラッグする回を分け、**閾値は分けた後の値を見てから 100ms に置いた**（後付けである）。
  ドラッグを含む回の最大間隔は pyside6 199ms・tauri 21ms・wpf 221ms。
- **tauri の間隔は、他の2つと同じ物を測っていない。**タイマーは WebView の JS で刻んでおり、描画は別プロセスである。
  Rust 側のメインスレッドの詰まりは見えない（ドラッグ中も 21ms なのはそのため）。

## 参考：起動時間とメモリ（`spikes/tools/footprint.py`）

起動の指示から `start` 行までの時間と、10秒放置した後のメモリ（子プロセス込み）。3回とも揃ったので中央の値を書く。

| 候補 | 起動 | プロセス数 | 作業セット | private |
|---|---|---|---|---|
| pyside6（Python 3.11.9） | 約 510ms | 1 | 85MB | 32MB |
| pyside6（Python 3.14.7） | 約 665ms | 1 | 89MB | 38MB |
| tauri | 約 565ms | 7（WebView2 の子を含む） | 393MB | 169MB |
| wpf | 約 865ms | 1 | 149MB | 81MB |

## S1〜S7 の外の事実

- Anthropic の公式 SDK があるのは Python・TypeScript・Java・Go・Ruby・C#・PHP。**Rust には無い**（claude-api スキル、2026-09-23 確認）。
  tauri で LLM を呼ぶには、Rust から生の HTTP で呼ぶか、TypeScript の SDK を WebView か Node の副プロセスで動かすことになる。
  WebView で動かすと API キーが画面側のプロセスに入る。
- Python の標準 `sqlite3` で FTS5 の trigram 分割が使え、日本語の部分一致（「話の続」→「昨日の話の続き」）が引けた。
  3.11.9（SQLite 3.45.1）と 3.14.7（SQLite 3.53.1）の両方で実行した（2026-09-23）。
- pyside6 の窓はタスクバーにボタンを出していた（UI オートメーションの一覧に「Python - 1 の実行中ウィンドウ」。他の2候補は見ていない）。
  常駐する相棒がタスクバーに出るかは、段1の設計で決める。
- Windows 11 は新しいトレイのアイコンを「隠れているインジケーター」に入れる。主人がタスクバーに出すまで、アイコンは1段奥にある。

## 未測

- トレイの表示・終了を、主人の手で行うこと（本書は UI オートメーションで押した）
- 画像ボディ用の半透明の窓（拡張口。段1の外）
- 実際の Anthropic API 呼び出し（本フェーズではやらない。`goal.md`）
