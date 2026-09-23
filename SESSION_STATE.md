# SESSION_STATE.md — 索引

**索引であって本体ではない。**詳細は各文書にある。上限200行。様式の置き場は `CLAUDE.local.md`。
最終更新：2026-09-23（Phase 0「抽出」検収 PASS。Claude Code）

## これは何か

人格を持ち、記憶を引き継ぐ、1対1の常駐デスクトップの相棒。
前身「影式（Kage-Shiki）」の作り直しで、前身からはコンセプト・基本設計・完成形だけを引き継ぐ。
運営は3ゲート（G0 ゴール合意／G1 不可逆操作／G2 統治自己改変）に従う。

## 読む順序

| 順 | 文書 | 何のために |
|---|---|---|
| 1 | `CLAUDE.md` | 目的・禁則・保護指定・作法・運営 |
| 2 | 本ファイル | 索引 |
| 3 | `goal.md`（58行） | 直近フェーズの契約。今は Phase 0「抽出」（検収 PASS 済み） |
| 4 | `docs/concept.md`（681行） | 何を作るか。完成形・道のり・基本設計・キャラ体系 C/S/L と権限マトリクス |
| 5 | `docs/behaviors.md`（140行） | 振る舞いカタログ BH-01〜42。US-1〜19・保護指定の紐付け・前身での状況 |
| 6 | `docs/lessons.md`（236行） | 前身の失敗を「実起動で確かめる完了条件」に直したもの。以後の goal.md に写す元 |
| 7 | `docs/research/2026-09-23-model-practices.md` | Opus 5.5 / Fable 5.1 の使い方。必要なときだけ |

## 現在地

**動いている物**

- git リポジトリ（`main`）。remote は `origin` = https://github.com/sougetuOte/Utsushimi（public）
- G2 フック：`core.hooksPath` を設定済み。止めることと、承認変数で通ることを実測した
- Phase 0 の抽出物：`docs/concept.md`／`docs/behaviors.md`／`docs/lessons.md`（検収 PASS）
- 初期ファイル：`CLAUDE.md`／本ファイル／`README.md`／`LICENSE`／`.gitignore`／`.gitattributes`／
  `.githooks/pre-commit`／`.claude/settings.json`／`docs/research/2026-09-23-model-practices.md`

**まだ無い物**

- 技術選定、ADR、コード

**clone したら要る物**（リポジトリに載らない）

- `git config core.hooksPath .githooks`
- `CLAUDE.local.md`（主人のローカルにだけある）

## これまで

| コミット | 出来事 |
|---|---|
| `ed524b2` | 2026-09-23 初回コミット。Cowork が配置した初期ファイルを、公開前の点検を経て載せた。同日 GitHub に public で作成・push |
| `3789fca` | Phase 0「抽出」の G0。依頼書の Must 一覧が実物と違った（US-6 は Must でなく、2a の US-8/9/11/12 が Must）ため、US-1〜19 全件＋保護指定の紐付けに改めて承認 |
| `e68ff23` | Phase 0 の成果3本。columba 検収で V1〜V11 すべて PASS（1回目） |
| （本コミット） | 主人が Phase 0 の完了を認め、依頼書 `docs/handoff/phase0-brief.md` を消滅条件どおり消した |

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

## 採らなかった案

| 案 | 理由 |
|---|---|
| 前身リポジトリを上書きして作り直す | 前身の履歴と公開物を壊す |
| 名前 Katashiro | GitHub に AI 系の同名が2件（npm パッケージ含む）。TRPG シナリオ「カタシロ」（VTuber に広く遊ばれ、舞台・映画化）との連想が強い |
| 名前 Yorishiro | GitHub に同名21件。AI キャラの人格・記憶を扱うものを含む |

## 未決（主人の判断待ち）

- 前身 Kage-Shiki（public）の README に後継の一行を入れる時期（Utsushimi が形になってから）

## 未決（実測・作業待ち）

（なし）

## 次の一手

**Phase 1（設計）の面接（G0）。**材料は `docs/concept.md`・`docs/behaviors.md`・`docs/lessons.md`。モデルは Opus 5.5 high（D8）。

## 作業の作法

- **Cowork の Linux 側から、このリポジトリで git の書込系コマンドを打たない。**
  接続フォルダでは削除が許可制のため、`git status` でさえ `.git/index.lock` を消せずに残した（2026-09-23 実測。消して復旧済み）。
  読むだけなら `git --no-optional-locks` を付ける。
