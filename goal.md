# goal.md — 段1 T1「骨格」

**状態：承認済み（2026-09-23 主人）**
種別：feature（G0 あり）。材料は `docs/specs/stage1/`（tasks の T1・design・requirements）と ADR 0001〜0004。モデルは Opus 5.5（D8）。
基準コミット（着手前）= `b286075`。前身 = `C:\work5\Kage-Shiki`（以下 `K/`）。

範囲：**窓が出て、1往復話せて、それが残る本体**を作る。以後のタスク（T2〜T8）はこの本体に足す。
中身は `tasks.md` の T1 の記述どおり：uv のプロジェクト（Python 3.14・PySide6・anthropic）、パッケージ `utsushimi`、
画面と核の2スレッド、枠なしの窓（上の帯でドラッグ・欄・入力）、トレイ（表示・隠す・終了）、`utterances` への1発言1コミット、
`claude-opus-5-5` の呼び出し（人格はまだ無く、固定の指示だけで話す）、ログ、主人の起動用ショートカット、
`docs/smoke-test.md` と画面の目視チェックリストの初版、`spikes/` の削除。

## 完了条件

1. **起動（Bug-1）**：`README.md` に主人向けの起動手順があり、その手順どおりに、スタートメニューのショートカット
   `Utsushimi.lnk`（`.venv\Scripts\pythonw.exe -m utsushimi` を指す）から実起動して、ウィンドウが表示され、コンソールの窓は出なかった。
2. **3往復（BH-01・Bug-2）**：実起動して3往復話し、3回とも返事が来て、主人の発言と返事が欄に順に並び、
   そのあいだ保存と LLM の呼び出しは核のスレッドで動き、その起動のあいだのログにエラーが1件も無かった。
3. **強制終了でも残る（BH-13）**：実起動して1往復話した直後に `taskkill /F` で強制終了し、次に実起動するとその発言と返事が欄に残っていた。
4. **トレイと終了（BH-03・Bug-6）**：実起動して「×」で隠れ、トレイの「表示」で戻り、「隠す」で隠れ、「終了」で終わり、
   5秒以内にウィンドウとトレイアイコンの両方が消え、本アプリのプロセスが1つも残っていなかった。次の実起動で、前回は正しく終わったと記録された。
5. **窓を動かせる（BH-02 の前半）**：実起動して上の帯をドラッグすると窓が動いた。タスクバーに窓が出なかった。
6. **核だけが資源を触る（ADR 0004・Bug-2）**：SQLite の接続と Anthropic のクライアントを作るコードが、それぞれ `memory` と `llm` の中にだけある。
7. **手順書（B-10・共通）**：`docs/smoke-test.md` に、1〜5 のそれぞれの確かめ方と、画面の目視チェックリストの初版がある。
   その全項目を実起動で通した日付と結果が報告に書かれている。
8. **目視（L-5・共通）**：実起動して会話の窓を目で確かめ、はみ出し・重なり・操作できない部分が無かったことが報告に書かれ、その窓のスクリーンショットがある。
9. **スパイクの消滅**：`spikes/` が消えていて、`docs/research/2026-09-23-phase1-spike.md` にそのことが1行書かれている。
10. **秘密が漏れない**：API キーがコミットにもログにも出ていない。

### ログの語（検収はこの語で数える）

`data/logs/utsushimi.log`、1行1出来事、各行に時刻・プロセス番号・スレッド名を含む。本体は少なくとも次の語を出す。

| 出来事 | 語 |
|---|---|
| 起動 | `start` の行に `console=none\|present`・`prev_shutdown=clean\|unclean\|none`・`loaded=<読んだ発言の数>` |
| 主人の発言の保存 | `send id=<番号>`（本文は出さない） |
| 返事の保存 | `reply id=<番号>`（本文は出さない） |
| 隠す・出す | `hide via=close\|tray`・`show via=tray` |
| 終了 | `shutdown begin via=<経路> call=<何回目>`・`shutdown done` |
| エラー | `ERROR` |

## 検証方法

検収役が見る。採点範囲は**本フェーズの成果コミット**（`b286075` より後で、報告に列挙したもの）に限る。
実起動の証拠は git の外にある：ログ `data/logs/utsushimi.log`、発言 `data/utsushimi.db`、スクリーンショット `data/smoke/t1/`。
**報告に、各完了条件を確かめた起動のプロセス番号と時刻を書く。**検収役はその番号でログを引き、`data/utsushimi.db` を読み取り専用で開いて突き合わせる。

| # | 完了条件 | 確かめ方 |
|---|---|---|
| V1 | 1 | `README.md` に起動手順の節がある。スタートメニューの `Utsushimi.lnk` を PowerShell（`WScript.Shell` の `CreateShortcut(...).TargetPath`／`Arguments`）で読むと `pythonw.exe` と `-m utsushimi`。報告の起動のログの `start` 行が `console=none`。スクリーンショットに窓が写っている |
| V2 | 2 | 報告の起動のプロセス番号で、`send id=` と `reply id=` がそれぞれ3行以上、交互に並び、そのスレッド名がどれも核のスレッド（画面のスレッドと違う名前）。同じプロセス番号の `ERROR` が0行。`data/utsushimi.db` の `utterances` にその番号の行が主人・返事の順である |
| V3 | 3 | 報告の強制終了した起動に `send id=N`・`reply id=N+1` があり `shutdown begin` が無い。その次の起動の `start` 行が `prev_shutdown=unclean` で `loaded=` が N+1 以上。`utterances` に N と N+1 がある。次の起動のスクリーンショットの欄にその発言が写っている |
| V4 | 4 | 報告の起動に `hide via=close`・`show via=tray`・`hide via=tray`・`shutdown begin via=tray call=1`・`shutdown done` がこの順にあり、`shutdown begin` から `shutdown done` までが5秒以内、`shutdown begin` はその起動で1行だけ。その次の起動の `start` 行が `prev_shutdown=clean`。報告に終了直後の `tasklist` の出力（本アプリの `pythonw.exe` が無い）がある |
| V5 | 5 | ドラッグの前後のスクリーンショット（または報告に前後の窓の座標）がある。design の「タスクバーに出さない」がコードにある（Qt のツール窓の指定） |
| V6 | 6 | `grep -rn "sqlite3.connect" src/` が `memory` の下だけ、`grep -rnE "Anthropic\(\|AsyncAnthropic\(" src/` が `llm` の下だけ |
| V7 | 7 | `docs/smoke-test.md` があり、1〜5 の各項目と、目視チェックリストの節がある。報告に全項目の実施日と結果（可／不可）がある |
| V8 | 8 | 報告に目視の結果が書かれ、`data/smoke/t1/` に会話の窓のスクリーンショットが1枚以上ある（検収役が画像を見て、はみ出し・重なりが無いことを確かめる） |
| V9 | 9 | `test ! -e spikes`。`git ls-files spikes` が0件。研究文書に `spikes/` を消した旨の行がある |
| V10 | 10 | `git log -p b286075..<最後の成果コミット>` に `sk-ant` が0件。`data/logs/utsushimi.log` に `sk-ant` が0件。成果コミットに `.env`・`data/`・`.venv/` のパスが無い |
| V11 | 範囲 | `git diff --name-only b286075..<最後の成果コミット>` が、`goal.md`・`pyproject.toml`・`uv.lock`・`.python-version`・`config.default.toml`・`src/`・`docs/`・`spikes/`（削除）・`README.md`・`.gitignore` の下だけ |
| V12 | やらないこと | 前身に書き込んでいない：`git -C C:\work5\Kage-Shiki rev-parse --short HEAD` が `39b030f` |
| V13 | 品質 | 成果の Markdown に制御文字 `[\x00-\x08\x0b\x0c\x0e-\x1f]` が無い |

時間で壊れないように、証拠は**足すだけの物**（ログ・`utterances`）と、報告に書き写した値で見る。
「今プロセスが無いこと」のような、検収の時点で変わる値は物差しにしない（主人が後で本体を起動していてよい）。

## G1 の事前承認（この goal の承認に含む）

- `uv sync` で、PyPI から PySide6・anthropic などをリポジトリ直下の `.venv` に入れること（uv のユーザーキャッシュへの書込を含む）。
- スタートメニュー（`%APPDATA%\Microsoft\Windows\Start Menu\Programs\`）に `Utsushimi.lnk` を1つ作ること。
  **デスクトップには置かない**（主人のデスクトップは OneDrive の下にあり、置けば外へ同期される。置くなら主人が写す）。
- Anthropic API を実際に呼ぶこと（`.env` のキー。`claude-opus-5-5`。確かめに要る分だけ、目安30回以内）。
- `spikes/` を消すこと（git に載っていない `.venv`・`run*` などの使い捨ても含めて）。
- 確かめの間、合成入力で主人の PC のマウスとキーボードを動かすこと。スクリーンショットは本アプリの窓の範囲だけを撮る。

## やらないこと

**このフェーズではやらない**

- 人格（`data/persona/`・`persona_seal`・文脈の組み方。T2）、キャラ作り（T3）、日記・検索・メインループの行動予定（T4）、
  2重起動の防止・終了の全経路（T5）、突っつき・最前面・窓の位置の記憶（T7）
- キャラの手触り（固定の指示の文面は動けば足りる。作り込まない）
- 自動テストを書くこと（完了は実起動で数える。確かめ用の使い捨てスクリプトはスクラッチに置き、コミットしない）
- `CLAUDE.md`・`SESSION_STATE.md` の書き換え（`SESSION_STATE.md` の更新は検収後に別コミット）
- push（検収 PASS 後、主人の指示で行う）
- T1 の確かめで溜まった `data/` の中身を消すこと（消すかは主人が決める）

**起きてはならない**

- 前身（`C:\work5\Kage-Shiki`）への書込。前身の `data/` と `.env` の読込（**機構なし**。検収でも見えない）
- API キー・`.env`・`data/`・`.venv/` のコミット。キーをログや報告に書くこと
- 主人に求めずに行うグローバル導入・処理系のインストール
- 承認後の `goal.md` の書き換え
- 自分で検収を採点すること
- 成果コミットの amend・force push（検収の指摘は訂正コミットで直す）
