# SESSION_STATE.md — 索引

**索引であって本体ではない。**詳細は各文書にある。上限200行。様式の置き場は `CLAUDE.local.md`。
最終更新：2026-09-23（初期配置。Cowork が主人の依頼で作成）

## これは何か

人格を持ち、記憶を引き継ぐ、1対1の常駐デスクトップの相棒。
前身「影式（Kage-Shiki）」の作り直しで、前身からはコンセプト・基本設計・完成形だけを引き継ぐ。
運営は3ゲート（G0 ゴール合意／G1 不可逆操作／G2 統治自己改変）に従う。

## 読む順序

| 順 | 文書 | 何のために |
|---|---|---|
| 1 | `CLAUDE.md` | 目的・禁則・保護指定・作法・運営 |
| 2 | 本ファイル | 索引 |
| 3 | `goal.md` | 直近フェーズの契約。**まだ無い**（Phase 0 の面接で作る） |
| 4 | `docs/handoff/phase0-brief.md` | Phase 0「抽出」の依頼書。面接の材料 |
| 5 | `docs/research/2026-09-23-model-practices.md` | Opus 5.5 / Fable 5.1 の使い方。必要なときだけ |

## 現在地

**動いている物**

- git リポジトリ（`main`）。**コミット0本、remote なし**（GitHub に public で作る予定）
- 初期ファイル：`CLAUDE.md`／本ファイル／`README.md`／`LICENSE`／`.gitignore`／`.gitattributes`／
  `.githooks/pre-commit`／`.claude/settings.json`／`docs/handoff/phase0-brief.md`／`docs/research/2026-09-23-model-practices.md`

**まだ無い物**

- `core.hooksPath` の設定（`git config core.hooksPath .githooks`。リポジトリに載らない設定なので clone ごとに要る）
- `goal.md`、抽出物（`docs/concept.md` ほか）、ADR、コード

## これまで

| コミット | 出来事 |
|---|---|
| （初回コミット前） | 2026-09-23 Cowork で初期ファイルを配置。前身を読んだ上で書いた |

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

## 採らなかった案

| 案 | 理由 |
|---|---|
| 前身リポジトリを上書きして作り直す | 前身の履歴と公開物を壊す |
| 名前 Katashiro | GitHub に AI 系の同名が2件（npm パッケージ含む）。TRPG シナリオ「カタシロ」（VTuber に広く遊ばれ、舞台・映画化）との連想が強い |
| 名前 Yorishiro | GitHub に同名21件。AI キャラの人格・記憶を扱うものを含む |

## 未決（主人の判断待ち）

- 前身 Kage-Shiki（public）の README に後継の一行を入れる時期（Utsushimi が形になってから）

## 未決（実測・作業待ち）

- G2 フックが Windows の git で実際に止めるか（初回コミットで確かめる）

## 次の一手

**初回コミットと GitHub の作成。**その次が Phase 0「抽出」の面接（G0）。

## 作業の作法

- **Cowork の Linux 側から、このリポジトリで git の書込系コマンドを打たない。**
  接続フォルダでは削除が許可制のため、`git status` でさえ `.git/index.lock` を消せずに残した（2026-09-23 実測。消して復旧済み）。
  読むだけなら `git --no-optional-locks` を付ける。
