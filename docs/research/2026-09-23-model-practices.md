# Opus 5.5 / Fable 5.1 の使い方（2026-09-23 調査）

**証拠であって条文ではない。**運営の判断で引くときは、ここではなく一次情報（下の出典）を読み直す。
**消滅条件**：次のモデル世代が出たら読み直し、外れた所を消す。公式の指針が改訂されたら、その節を消す。

調べ方：公式ドキュメントとブログ、実務者の記事を 2026-09-23 に検索・取得した（Cowork）。
**「公式」と書いた項目は一次情報で確かめた。「実務者」は個人の報告で、再現は未確認。**

---

## 1. 事実（公式）

| | Opus 5.5 | Fable 5.1 |
|---|---|---|
| 公開 | 2026-09-22（米国時間） | 2026-09-01 |
| Claude Code での扱い | Pro / Max / Team / Enterprise の既定モデル | どのプランでも既定ではない。`/model fable` で選ぶ |
| effort の既定 | **medium**（Opus 5 は high）。「medium で Opus 5 の high に並ぶか上回る」 | high |
| 向く仕事 | 普段の対話的な作業、実リポジトリでの多段の変更 | 一度に座って終わらない大きさの仕事、曖昧な問題（原因調査・設計判断）、長い自律走行 |
| 料金面 | プランに含まれる | プランと席種によっては usage credits に課金される（Max は週間上限の一部まで） |
| API 単価（100万トークン） | 入力 $4 / 出力 $20 | 入力 $10 / 出力 $50（Opus 5.5 の2.5倍） |

公式発表は Opus 5.5 を「ほとんどの仕事で Fable 5.1 と同じ水準」とし、「実際に使うと点差より差は小さい」と書く（Anthropic 自身の言い分）。

## 2. プロンプトの書き方（公式）

- **手順ではなく成果を渡す**（Fable）。「普段なら分割する仕事を丸ごと渡す」。
- 強調（CRITICAL / MUST）をやめ、**理由を添えて普通の口調で書く。**
- 「推論を書き出せ」「よく考えてから答えよ」は消す。思考は常時オンで、深さは effort で決める。
- **テキストだけで終わったターンは報告であって完了ではない。**やることの一覧を持たせ、未了の項目を名指しして続けさせる。
  同じ作業への自動の継続は2〜3回で止める。
- CLAUDE.md は 200 行未満。必ず守らせたいことは hook にする。
- 古くなった指示は `/claude-api prompt-audit` で洗い出せる。

## 3. 進め方（公式）

- **検証を中心に置く。**強さの順に：プロンプトで指示 → `/goal` → Stop hook → 新しいコンテキストの検証役。
- **`/goal` は検収役（新しいコンテキストの評価器）の代わりにならない。**`/goal` の評価役（既定 Haiku）はファイルを読まずコマンドも打たず、
  会話に出た内容だけで判定する。実装側を止めずに走らせる道具としては使える。
- レビュー役には「正しさと要件に関わる欠落だけ」を指摘させる。そうしないと過剰設計を招く。
- モデルの使い分け：普段の作業は Opus 5.5 の medium。medium で詰まったら high。
  **high で同じ問題に2回つまずいたら Fable 5.1 へ切り替え、解決したら戻す**（3回目を待たない）。
  Fable へ上げるのは「結果がトークン代より重要なとき」── 監督しない長時間走行、コードベースに前例の無い問題、
  多数のサブエージェントを束ねる大きな変更（公式ブログ「What a task costs on Opus 5.5」）。
  **会話の途中で切り替えるとキャッシュと以前の思考が使えなくなる**ので、切り替えはセッション単位で。
- 「ハーネスの各部品は、モデルにできないことについての仮定を抱えている」── 世代ごとに外して確かめる。

## 4. 実務者の報告（未検証）

- Fable 5.1 は古く長い指示で性能が落ちる。手順と強調を削って改善した（note・立花岳、2026-09-02）。
- effort を max にすると単純な指示でも考えすぎる（Simon Willison、2026-09-22）。
- コードレビューで max は取りこぼしが減るが誤指摘が増え、トークンは約 +60%（CodeRabbit、2026-09-22）。

## 出典

- https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5-5
- https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5-1
- https://code.claude.com/docs/en/model-config
- https://code.claude.com/docs/en/goal
- https://code.claude.com/docs/en/best-practices
- https://code.claude.com/docs/en/memory
- https://www.anthropic.com/claude-opus-5-5
- https://claude.com/blog/what-a-task-costs-on-opus-5-5
- https://www.anthropic.com/claude-fable-and-mythos-5-1
- https://www.anthropic.com/engineering/harness-design-long-running-apps
- https://github.com/anthropics/skills/blob/main/skills/claude-api/shared/prompt-audit.md
- https://note.com/gaku_tachibana/n/n46a0dfd9ee1e
- https://simonwillison.net/2026/Sep/22/opus-and-sol-and-luna/
- https://www.coderabbit.ai/blog/opus-5-5-model-review
