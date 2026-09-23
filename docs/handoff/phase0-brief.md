# Phase 0「抽出」依頼書

作成：2026-09-23（Cowork。主人の依頼で下書き）
**これは面接（G0）の材料であって契約ではない。**契約は面接の後に `goal.md` として主人が承認する。
下の「完了条件・検証方法・やらないことの候補」は叩き台であり、採るかどうかは主人が決める。

**消滅条件**：Phase 0 の検収が PASS し、主人が完了を認めたら、この文書は役目を終える（消してよい）。

---

## 1. 何をするフェーズか

前身 `C:\work5\Kage-Shiki`（影式）から、**「何を作るか」だけを抜き出して**、Utsushimi の足場になる文書にする。
「どう作るか」（コード・LAM 由来の工程・詳細設計）は抜き出さない（`CLAUDE.md` §4）。

前身は **read-only**。書き込まない。

## 2. 一次資料（前身の中の場所）

行数は 2026-09-23 に `wc -l` で測った値。

### 主人の言葉（最優先。ここと食い違ったらこちらが勝つ）

| パス | 行数 | 中身 |
|---|---|---|
| `docs/memos/方向性.md` | 34 | 出発点。やりたいこと・思っていること・名前の由来 |
| `docs/memos/2026-03-03-char.md` | 12 | キャラの作り方への要望（根っこ／書ける部分・書けない部分／ゆらぎ＝唯一無二） |

### 統合設計（コンセプトと基本設計の本体）

| パス | 行数 | 中身 |
|---|---|---|
| `docs/memos/middle-draft/index.md` | 86 | 01〜07 の索引と参照したソース一覧 |
| `docs/memos/middle-draft/04-unified-design.md` | 407 | **統合設計案（SSOT）。**コンセプト、VTuber/AITuber との差、構成、Phase ロードマップ |
| `docs/memos/middle-draft/07-character-design.md` | 594 | **キャラ設計。**凍結核 C1〜C11 ／凍結殻 S1〜S7 ／可変層 L1〜L6、権限マトリクス、ゆらぎ |
| `docs/memos/middle-draft/01-memory-system.md` | 133 | 記憶（Hot/Warm/Cold の3層、忘却曲線、シャットダウン耐性） |
| `docs/memos/middle-draft/02-personality-system.md` | 164 | 人格5原則、欲求システム、自律行動 |
| `docs/memos/middle-draft/06-gui-and-body.md` | 289 | GUI とボディ（ヘリ反応、PNGTuber 方式、表示の抽象） |
| `docs/memos/middle-draft/05-agentic-search.md` | 208 | 好奇心から自分で調べる仕組み |
| `docs/memos/middle-draft/03-architecture.md` | 183 | 技術スタック（**前身の選定として記録するだけ。採用は決め直す**） |

### 判断の経緯（必要なときだけ）

| パス | 行数 | 中身 |
|---|---|---|
| `docs/memos/2026-03-02-uthink-unified-design.md` | 214 | 6つの論点の検討と結論（GUI 抽象・記憶方式・シャットダウン・モデル配分・人格生成・MVP 範囲） |
| `docs/memos/2026-03-03-design-review.md` | 190 | 簡素化レビュー（削った5件） |
| `docs/memos/personalized-ai-agent-reference.md` | 808 | 参考文献集（Letta/MemGPT、familiar-ai、MemoryBank など） |

### 振る舞い（受入の物差しの元）

| パス | 行数 | 中身 |
|---|---|---|
| `docs/specs/phase1-mvp/requirements.md` | 651 | US-1〜US-7 と FR（対話・記憶・人格・常駐・シャットダウン） |
| `docs/specs/phase2a-foundation/requirements.md` | 341 | US-8〜US-13（基盤強化。多くは開発者向け） |
| `docs/specs/phase2b-autonomy/requirements.md` | 376 | US-14〜US-19（自発的に話しかける・うるさくない・自分で調べる・入力で即座に引く） |

### 教訓（前身で実際に踏んだもの）

| パス | 行数 | 中身 |
|---|---|---|
| `docs/memos/hotfix-runtime-bugs-phase1.md` | 131 | **649 テスト全通過・カバレッジ 97% で、実起動したら不具合7件。**原因は「テスト環境と実行環境の乖離」 |
| `docs/memos/phase2-backlog.md` | 40 | 上の教訓から出た宿題（マルチスレッド、既存 DB での起動、シャットダウン全経路、スモーク、GUI 目視） |
| `docs/memos/feedback-smoketest-2026-03-07.md` | 60 | 主人が実際に触った感想 |
| `docs/memos/retro-phase-1.md` | 176 | Phase 1 の振り返り |

### 読まないもの

- `data/` ── 主人の既存キャラと記憶。**Phase 0 の範囲外**（引っ越しは後のフェーズ）
- `.env` ── 秘密情報
- `.claude/`、`docs/specs/lam/`、`docs/artifacts/`、`docs/internal/`、`docs/memos/LivingArchitectModel-*` ── LAM の工程資産
- `src/`・`tests/` ── **読んでよいが写さない。**前身で実装済みか未統合かを確かめる用途に限る

### 前身の状態について（読み違えないために）

`README.md` は「Phase 2a BUILDING 中」、`SESSION_STATE.md` は「Phase 2b Wave 3 完了、Wave 5（main.py 統合）未着手」と書いており、
**食い違っている。**実装状況は git log と `src/` を正とする。最終コミットは 2026-07-20。

## 3. 成果物の案

1. **`docs/concept.md`** ── コンセプト、完成形（1対1の相棒。AITuber は拡張口）、前身の Phase 1〜4 を相棒として整理し直した道のり
2. **`docs/behaviors.md`** ── **振る舞いカタログ。**前身の US と FR を「主人から見えるふるまい」単位に組み直す。
   各項目に、出典（パスと行）・優先度（Must / Should / Could）・前身での状況（実装済み／未統合／未着手）
3. **`docs/lessons.md`** ── 持ち越す教訓。前身で踏んだ失敗を、**以後のフェーズの完了条件に書ける形**に翻訳する
   （例：「テストが通った」ではなく「実起動して〜できた」）
4. `CLAUDE.md` に直すべき所があれば、**変更案を文章で**報告に書く（書き換えは G2。主人が承認して別コミット）

C1〜C11 ／ S1〜S7 ／ L1〜L6 のキャラ体系と権限マトリクスは、前身の設計でいちばん価値が高い部分である。
**要約して落とさない。**どちらかの文書に全項目を残す。

## 4. 完了条件・検証方法・やらないことの候補（面接の叩き台）

**完了条件の候補**

- 上の3文書がある。**すべての記述に出典（前身のパスと行）が付く**
- 前身の Must の US（US-1〜US-7、US-14、US-15、US-17）が `behaviors.md` に**全件**ある
- C1〜C11・S1〜S7・L1〜L6 が**全項目**、どちらかの文書にある
- `lessons.md` に hotfix の7件と、その宿題（backlog の B-7〜B-11）が完了条件の形で入っている
- 技術選定を確定していない（前身の選定は「前身ではこうした」として記録するだけ）

**検証方法の候補**（検収役が機械で見られる形。時間で壊れない形）

- 評価器が出典を任意に3件以上選び、前身の実ファイルの該当行を引いて一致を確かめる
- 上の US 番号・C/S/L 番号の全件が成果物に現れることを grep で数える
- `git ls-files` にコード（`.py` など）が0件
- 前身（`C:\work5\Kage-Shiki`）に書き込んでいない：HEAD が `39b030f` のままで、`git status --porcelain` の出力が着手前に取った控えと一致する
  （前身の作業ツリーは元から空ではない。2026-09-23 時点で変更ありの行が多数ある。「空であること」を物差しにしない）
- 成果物に制御文字（`[\x00-\x08\x0b\x0c\x0e-\x1f]`）が無い

**やらないことの候補**

- このフェーズではやらない：技術選定・ADR・コードを書くこと・GitHub の設定を変えること
- 起きてはならない：前身への書込、`data/` と `.env` の読込、`goal.md` の承認後の書き換え、自分で検収を採点すること、
  成果コミットの amend（検収の指摘は訂正コミットで直す）

## 5. モデル

Opus 5.5（既定 effort の medium で始める）。読む量が多いだけで、判断の難所は少ない。
同じ所で2回つまずいたら effort を上げ、それでも駄目なら主人に言う。
