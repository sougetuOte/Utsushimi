# SESSION_STATE.md — 索引

**索引であって本体ではない。**詳細は各文書にある。上限200行。様式の置き場は `CLAUDE.local.md`。
最終更新：2026-09-23（俯瞰ツール「見取り図」検収 PASS。Claude Code）

## これは何か

人格を持ち、記憶を引き継ぐ、1対1の常駐デスクトップの相棒。
前身「影式（Kage-Shiki）」の作り直しで、前身からはコンセプト・基本設計・完成形だけを引き継ぐ。
運営は3ゲート（G0 ゴール合意／G1 不可逆操作／G2 統治自己改変）に従う。

## 読む順序

| 順 | 文書 | 何のために |
|---|---|---|
| 1 | `CLAUDE.md` | 目的・禁則・保護指定・作法・運営 |
| 2 | 本ファイル | 索引 |
| 3 | `goal.md`（86行） | 直近フェーズの契約。今は俯瞰ツール「見取り図」（検収 PASS 済み） |
| 4 | `docs/concept.md`（681行） | 何を作るか。完成形・道のり・基本設計・キャラ体系 C/S/L と権限マトリクス |
| 5 | `docs/behaviors.md`（140行） | 振る舞いカタログ BH-01〜42。US-1〜19・保護指定の紐付け・前身での状況 |
| 6 | `docs/lessons.md`（236行） | 前身の失敗を「実起動で確かめる完了条件」に直したもの。以後の goal.md に写す元 |
| 7 | `docs/adr/0001`〜`0004`（各 44〜61行） | 技術選定：Python 3.14 ＋ PySide6／SQLite とテキストファイル／公式 Python SDK と `claude-opus-5-5`／画面と核の2スレッド |
| 8 | `docs/specs/stage1/`（requirements 96・design 214・tasks 86行） | 段1の設計。BH の振り分け・作り方・T1〜T8 |
| 9 | `docs/smoke-test.md`（55行） | 実起動の手順書と画面の目視チェックリスト。タスクごとに足す |
| 10 | `src/utsushimi/`（5本、約480行） | 本体。`ui`（画面）・`core`（核のスレッド）・`memory`（SQLite）・`llm`（API） |
| 11 | `docs/research/2026-09-23-phase1-spike.md`（88行） | ADR 0001 の根拠（3候補の実測）。必要なときだけ |
| 12 | `docs/research/2026-09-23-model-practices.md` | Opus 5.5 / Fable 5.1 の使い方。必要なときだけ |
| 13 | 見取り図 `build/overview/index.html` | 全体を目で見る入口。`uv run python tools/overview/build.py` で作り直す（git に載らない）。道具選びは `docs/research/2026-09-23-overview-tools.md`（65行） |

## 現在地

**動いている物**

- git リポジトリ（`main`）。remote は `origin` = https://github.com/sougetuOte/Utsushimi（public）
- G2 フック：`core.hooksPath` を設定済み。止めることと、承認変数で通ることを実測した
- Phase 0 の抽出物：`docs/concept.md`／`docs/behaviors.md`／`docs/lessons.md`（検収 PASS）
- Phase 1 の設計：ADR 0001〜0004（採用）、`docs/specs/stage1/` の3点（検収 PASS）
- **本体（段1 T1）**：スタートメニューの `Utsushimi.lnk` から起動し、枠なしの窓で `claude-opus-5-5` と話せる。
  発言は1つずつ `data/utsushimi.db` に残り、強制終了のあとも欄に戻る。トレイで表示・隠す・終了。人格はまだ無い（固定の指示だけ）
- **見取り図**（`tools/overview/`）：リポジトリの中身から9ページの HTML（入口・年表・追跡・決定・本体の構造・文書の地図・前身とのずれ・気がかり・分岐）を1コマンドで作り直す
- 初期ファイル：`CLAUDE.md`／本ファイル／`README.md`／`LICENSE`／`.gitignore`／`.gitattributes`／
  `.githooks/pre-commit`／`.claude/settings.json`／`docs/research/2026-09-23-model-practices.md`

**まだ無い物**

- 人格・キャラ作り・日記と検索・2重起動の防止・突っつき・最前面（T2〜T7）
- `spikes/`（T1 で消した。コードは `b286075` 以前の履歴にある）

**clone したら要る物**（リポジトリに載らない）

- `git config core.hooksPath .githooks`
- `CLAUDE.local.md`（主人のローカルにだけある）
- 本体を動かすには `.env`（`ANTHROPIC_API_KEY`）・`uv sync`・スタートメニューのショートカット（手順は `README.md`「起動」）

## これまで

| コミット | 出来事 |
|---|---|
| `ed524b2` | 2026-09-23 初回コミット。Cowork が配置した初期ファイルを、公開前の点検を経て載せた。同日 GitHub に public で作成・push |
| `3789fca` | Phase 0「抽出」の G0。依頼書の Must 一覧が実物と違った（US-6 は Must でなく、2a の US-8/9/11/12 が Must）ため、US-1〜19 全件＋保護指定の紐付けに改めて承認 |
| `e68ff23` | Phase 0 の成果3本。検収役の検収で V1〜V11 すべて PASS（1回目） |
| `5e68db2` | 主人が Phase 0 の完了を認め、依頼書 `docs/handoff/phase0-brief.md` を消滅条件どおり消した |
| `5c010f0` | Phase 1「設計」の G0。範囲は技術 ADR＋段1の設計＋tasks。スパイクで裏付け、ADR は途中で1回諮る。処理系の導入は遠慮なく求めてよい（主人） |
| `8c1ba89` | 3候補（PySide6・Tauri・WPF）を実起動で測り、S1〜S7 は3候補とも可。決め手は常駐の重さと公式 SDK。途中の不可3件は権限・計測側の誤り・ドラッグの混入で、原因を研究文書に残した |
| `e73d056`・`16ffa2d` | 主人の差し戻し：グローバルの 3.11 は古い → 3.14 を選び、uv 管理で入れて測り直した（可）。既定モデルは主人が `claude-opus-5-5` を選んだ |
| `c904a64`・`17a6a9f` | ADR 採用（主人承認）と段1の設計3点。検収役の検収で V1〜V11 すべて PASS（1回目） |
| `6c35087`・`8c98d02` | 段1 T1「骨格」の G0 と本体。確かめは合成入力で6回の実起動（証拠は `data/logs`・`data/smoke/t1`、git の外）。検収1回目は V7・V10 が FAIL |
| `ae63b2e` | V10 の句が goal.md 自身の字面（禁止した文字列）に当たって満たせなかった → 主人承認で句を訂正。V7 は「確かめていないのに可」と書いた報告の誤りで、実起動を足して直した。検収2回目で V1〜V13 すべて PASS |
| `bf744b6`・`da8737a` | 主人の依頼で俯瞰ツール「見取り図」（段1のタスクの外）。道具選びはサブエージェントが調べ、ECharts を主軸にした。検収役の検収で V1〜V11 すべて PASS（1回目） |

## 決定（蒸し返さない）

| # | 決定 |
|---|---|
| D1 | 名前は **Utsushimi（写し身／現し身）**（2026-09-23 主人決定） |
| D2 | **完成形は1対1の相棒。**AITuber は拡張口として残す（2026-09-23 主人決定） |
| D3 | 前身 `C:\work5\Kage-Shiki` は **read-only**。コードと LAM 資産は持ち込まない |
| D4 | 運営は3ゲート。面接の入口と検収役は `CLAUDE.local.md`（git に載せない） |
| D5 | GitHub は **public**（2026-09-23 主人決定）。作成と push は Claude Code に頼む |
| D6 | `data/`（キャラと記憶）と `.env` は git に載せない |
| D7 | ライセンスは MIT（前身に揃えた。**Cowork の仮置き**で、主人が変えてよい） |
| D8 | **モデルの既定は Opus 5.5。Phase 1（設計）も Opus 5.5 の high で行う**（2026-09-23 主人決定）。Fable 5.1 へは high で同じ問題に2回つまずいたときに上げる。根拠は `docs/research/2026-09-23-model-practices.md` |
| D9 | **public 側に private リポジトリの存在を示唆しない。**具体的な参照は `CLAUDE.local.md`（git に載せない）に置く。G2 の承認変数は `UTSUSHIMI_G2`（2026-09-23 主人決定） |
| D10 | **技術選定は ADR 0001〜0004**（2026-09-23 主人承認）。本体は Python 3.14 ＋ PySide6、記憶は SQLite と人格のテキストファイル、LLM は公式 Python SDK で `claude-opus-5-5`、スレッドは画面と核の2本。見直しは各 ADR の消滅条件で |
| D11 | **段1は T1〜T8**（`docs/specs/stage1/tasks.md`）。1タスク＝1フェーズで、各タスクは G0 から入る。T1 で実起動できる本体を作り、以後は足すだけ |
| D12 | **主人の起動用ショートカットはスタートメニューに置く**（デスクトップは OneDrive の下で外へ同期されるため。置くなら主人が写す）（2026-09-23 T1 の G0 で主人承認） |

## 採らなかった案

| 案 | 理由 |
|---|---|
| 前身リポジトリを上書きして作り直す | 前身の履歴と公開物を壊す |
| 名前 Katashiro | GitHub に AI 系の同名が2件（npm パッケージ含む）。TRPG シナリオ「カタシロ」（VTuber に広く遊ばれ、舞台・映画化）との連想が強い |
| 名前 Yorishiro | GitHub に同名21件。AI キャラの人格・記憶を扱うものを含む |
| Tauri・.NET WPF・tkinter | ADR 0001 の却下表（常駐の重さ・公式 SDK・言語の数。tkinter は測っていない） |
| 白紙から育てる（BH-07 の一部・BH-12） | 段1の「確定してから話す」流れと別の道が要る。段2以降へ（requirements） |

## 未決（主人の判断待ち）

- 前身 Kage-Shiki（public）の README に後継の一行を入れる時期（Utsushimi が形になってから）
- BH-39：主人の呼び方（根っこの C3）を、関係の深さで変わる物として根っこの外に出すか（段2以降。requirements）

## 未決（実測・作業待ち）

- T1 の確かめで `data/` に溜まった試しの会話（12発言）・ログ・スクリーンショットを消す（2026-09-23 主人決定「いずれ消す」。本当に使い始める前に。削除の G1 は承認済み）

## 次の一手

**段1 T2「人格の器」の面接（G0）。**材料は `docs/specs/stage1/tasks.md` の T2 と共通の完了条件、design.md §2・§4.1・§4.2、ADR 0002・0003。

## 作業の作法

- **Cowork の Linux 側から、このリポジトリで git の書込系コマンドを打たない。**
  接続フォルダでは削除が許可制のため、`git status` でさえ `.git/index.lock` を消せずに残した（2026-09-23 実測。消して復旧済み）。
  読むだけなら `git --no-optional-locks` を付ける。
- **実起動の確かめを合成入力で回すときは、主人に PC から離れてもらう。**打つ前に前面の窓が本アプリであることを確かめる
  （T1 で1回、クリックがトレイのあふれ領域の小窓に吸われ、打った文字がよその窓に入った可能性がある）。
  トレイを UI オートメーションで探すときは、タスクバー（`Shell_TrayWnd`）とあふれ領域（`TopLevelWindowForOverflowXamlIsland`）の中に限る。
  名前「Utsushimi」は Claude アプリやエクスプローラーにもある。
- **フェーズの終わりに見取り図を作り直す**（`uv run python tools/overview/build.py`。2026-09-23 主人承認）。気がかりのページに出た物は、主人への報告に添える。
- **検証方法に「0件であるべき文字列」を字面で書かない。**G0 のコミットがその字面を含み、自分で満たせなくなる（T1 の V10）。
  当たらない形の正規表現で書く。
- **Windows PowerShell 5 は BOM の無い UTF-8 の .ps1 を読めない。**日本語を含むスクリプトは `pwsh`（7）で走らせる。
- **ネットから取った物を python へパイプで流す形は、主人の安全フックが止める。**いったんファイルに落としてから読む。
