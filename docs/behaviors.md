# behaviors.md — 振る舞いカタログ（前身「影式」から抜き出したもの）

前身 `C:\work5\Kage-Shiki`（以下 `K/`）の US-1〜US-19 と FR を、**主人から見えるふるまい**の単位に組み直した表である。
「どう作るか」は書かない。技術に触れるときは「前身では」と明示し、Utsushimi の技術選定はしない。

## 0. 読み方

- **ふるまい**：主人が画面の前で出会うこと。1行に1つ。行番号 `BH-nn` は本文書の中だけの通し番号。
- **元**：前身の US と FR。US と FR の対応は前身の対応表に従う（K/docs/specs/phase1-mvp/requirements.md:62-70、K/docs/specs/phase2a-foundation/requirements.md:74-81、K/docs/specs/phase2b-autonomy/requirements.md:80-87）。
- **優先度**：前身の表記をそのまま写す（Must / Should / Could。FR-4.4 だけは前身で May）。US も FR も無い行は「—」。
- **前身での状況**：
  - **実装済み**：前身の起動経路（`main.py`）から呼ばれるコードがある。
  - **未統合**：モジュールと単体テストはあるが、起動経路から呼ばれていない。主人が起動しても出会えない。
  - **未着手**：そのふるまいを成り立たせるコードが無い（または要る部分が欠けている）。
  - いずれも**コードと git log から判定した**もので、本文書の作成で前身を実起動して確かめてはいない。判定の根拠は §8。
- **出典**：`K/<パス>:<行>` の形。行番号は 2026-09-23 に前身の作業ツリーを読んで確かめた。
- **保護指定N**：`CLAUDE.md` §0 の保護指定1〜4 との紐付け。まとめは §9。

## 1. 話す・そばにいる

出典：K/docs/specs/phase1-mvp/requirements.md:52-57

| 行 | ふるまい | 元 | 優先度 | 前身での状況 | 出典 | 紐付け・備考 |
|---|---|---|---|---|---|---|
| BH-01 | 人格を持つ相棒と、日常的に文字で話せる。書いて送ると、キャラの口調で返事が来る。自分の発言もやり取りの欄に残る | US-1 / FR-2.3, FR-2.4, FR-6.1 | Must | 実装済み | K/docs/specs/phase1-mvp/requirements.md:52、K/docs/specs/phase1-mvp/requirements.md:488-489、K/docs/memos/feedback-smoketest-2026-03-07.md:18、K/src/kage_shiki/main.py:398-406 | 自分の発言が見えないのは主人が触って直させた点（feedback #8） |
| BH-02 | 窓は枠が無く、ドラッグで好きな場所へ動かせる。最前面に固定するかどうかは主人が選べる | US-1 / FR-2.1, FR-2.2, FR-2.10 | Must（FR-2.10 は Should） | 実装済み | K/docs/specs/phase1-mvp/requirements.md:486-487、K/docs/specs/phase1-mvp/requirements.md:495、K/src/kage_shiki/gui/tkinter_view.py:74-77 | 前身では窓の既定の大きさを主人の感想で 1.5 倍に広げた（K/docs/memos/feedback-smoketest-2026-03-07.md:19） |
| BH-03 | 作業の邪魔になるときは、しまっておける。閉じるとトレイに隠れ、トレイから「表示」「最小化」「終了」を選べる | US-4 / FR-2.7, FR-2.8, FR-2.9 | Must | 実装済み | K/docs/specs/phase1-mvp/requirements.md:55、K/docs/specs/phase1-mvp/requirements.md:492-494、K/docs/memos/feedback-smoketest-2026-03-07.md:13、K/src/kage_shiki/tray/system_tray.py:84-90 | 目的の禁則「作業の邪魔をしない」に対応 |
| BH-04 | 話しかけても、返事で待たされない（前身では送信から5秒以内が目安） | US-13 / FR-8.11 | Should | 実装済み | K/docs/specs/phase2a-foundation/requirements.md:70、K/docs/specs/phase2a-foundation/requirements.md:230、K/docs/specs/phase2a-foundation/requirements.md:319 | 前身の確かめ方は偽の応答器を使った計測で、実際の通信での5秒は保証していない（同 :319 が自ら指摘） |
| BH-05 | 窓を突っつくと、キャラが軽く反応する。文字を打たなくても「そばにいる」と感じられる | US-6 / FR-2.5 | Should | 実装済み（前身では窓のヘリではなく、窓の上の専用の ♪ ボタンに寄せた） | K/docs/specs/phase1-mvp/requirements.md:57、K/docs/specs/phase1-mvp/requirements.md:490、K/docs/memos/方向性.md:15-16、K/docs/memos/feedback-smoketest-2026-03-07.md:12、K/src/kage_shiki/gui/tkinter_view.py:108-119、K/src/kage_shiki/main.py:423-428 | **保護指定1**。主人の言葉は「ヘリを突っつく」「そこをボディの代わりにする」（K/docs/memos/middle-draft/06-gui-and-body.md:219-238 も同じ）。前身では最初は反応せず、ボタン化して直した。ヘリそのものを体にする形は前身で満たしきっていない |

## 2. キャラを作る

出典：K/docs/specs/phase1-mvp/requirements.md:53、K/docs/specs/phase1-mvp/requirements.md:529-539

| 行 | ふるまい | 元 | 優先度 | 前身での状況 | 出典 | 紐付け・備考 |
|---|---|---|---|---|---|---|
| BH-06 | 相棒がまだいないときは、最初にキャラ作りから始まる | US-2 / FR-4.7 | Must | 実装済み | K/docs/specs/phase1-mvp/requirements.md:524、K/src/kage_shiki/main.py:323-329 | |
| BH-07 | 作り方を3つから選べる。おまかせ（キーワードから連想を広げて候補を作る）／既存イメージ（主人の自由な記述を整えて足りない所を補う）／白紙から育てる（名前と一人称だけ決める） | US-2 / FR-5.1, FR-5.2, FR-5.3, FR-5.4 | Must（白紙育成 FR-5.4 は Should） | 実装済み | K/docs/specs/phase1-mvp/requirements.md:531-534、K/src/kage_shiki/persona/wizard.py:270、K/src/kage_shiki/persona/wizard.py:305、K/src/kage_shiki/persona/wizard.py:399、K/src/kage_shiki/persona/wizard.py:528 | 前身の要件は「候補から選ぶ」だが、実際は AI が1体を自動で選んでいた（BH-42） |
| BH-08 | 確定する前に、そのキャラと数往復お試しで話せる。気に入れば確定、気に入らなければやり直せる | US-2, US-12 / FR-5.5, FR-5.6, FR-8.9, FR-8.10 | Must | 実装済み（前身では確定の後に一度アプリを起動し直す必要があった） | K/docs/specs/phase1-mvp/requirements.md:535-536、K/docs/specs/phase2a-foundation/requirements.md:223-224、K/docs/memos/feedback-smoketest-2026-03-07.md:20 | 確定すると根っこが固まる（BH-19） |
| BH-09 | キャラ作りは画面の上だけで終わる。設定ファイルを開いたりコマンドを打ったりしなくてよい | US-12 / FR-8.8 | Must | 実装済み | K/docs/specs/phase2a-foundation/requirements.md:69、K/docs/specs/phase2a-foundation/requirements.md:222、K/src/kage_shiki/main.py:230-252 | |
| BH-10 | 主人が同じキーワードを入れても、毎回ちがうキャラが生まれる。連想の広がり方が毎回ゆらぎ、その過程が記録に残る | US-2 / FR-5.7, FR-5.8 | Must（記録 FR-5.8 は Should） | 実装済み（連想のゆらぎまで） | K/docs/specs/phase1-mvp/requirements.md:537-538、K/docs/memos/2026-03-03-char.md:11、K/docs/memos/middle-draft/07-character-design.md:341-343、K/src/kage_shiki/persona/wizard.py:270-302 | **保護指定3**。唯一性の源。ただしテストではゆらぎを外から固定できること（CLAUDE.md の禁則） |
| BH-11 | キャラ作りの途中で、AI が自分で調べ（前身の設計ではネット検索）、見つけた具体的な事柄がキャラに入る。調べた時と結果の違いが、さらにゆらぎになる | US・FR なし（主人の言葉と前身の設計） | — | 未着手 | K/docs/memos/方向性.md:17、K/docs/memos/2026-03-03-char.md:11、K/docs/memos/middle-draft/07-character-design.md:347-356 | **保護指定3**。主人の言葉の「AI が調べながら作る」の本体。前身は「調べる仕組みができてから足す」として先送りし、そのまま止まった（同 :355-356） |
| BH-12 | 白紙から育てたキャラは、しばらく話した後（前身の既定では20会話）にキャラの方から「自分はこういう者だ」と全体像を差し出し、主人が承認すると根っこが固まる | US-2 / FR-5.9 | Should | 未統合（差し出す文を作る処理はあるが、会話の流れから呼ばれていない） | K/docs/specs/phase1-mvp/requirements.md:539、K/src/kage_shiki/persona/wizard.py:575、K/src/kage_shiki/persona/wizard.py:594 | **保護指定4**（固めるのは主人の承認）。前身の `src/` で `should_propose_freeze` を呼ぶ所は `wizard.py` の外に無い |

## 3. 覚えている

出典：K/docs/specs/phase1-mvp/requirements.md:54、K/docs/specs/phase1-mvp/requirements.md:56、K/docs/specs/phase1-mvp/requirements.md:499-512

| 行 | ふるまい | 元 | 優先度 | 前身での状況 | 出典 | 紐付け・備考 |
|---|---|---|---|---|---|---|
| BH-13 | 話したことは、一言ごとにその場で残る。後でまとめて保存するのではない | US-5 / FR-3.3 | Must | 実装済み | K/docs/specs/phase1-mvp/requirements.md:56、K/docs/specs/phase1-mvp/requirements.md:503、K/src/kage_shiki/agent/agent_core.py:352-360 | 目的の禁則「記憶を失わない」 |
| BH-14 | 「昨日の話の続き」ができる。直近数日の日記を覚えた状態で起き、会話の中で関係する昔の発言を思い出して返事に使う | US-3 / FR-3.4, FR-3.5, FR-3.6, FR-3.7, FR-3.12 | Must | 実装済み | K/docs/specs/phase1-mvp/requirements.md:54、K/docs/specs/phase1-mvp/requirements.md:504-507、K/src/kage_shiki/main.py:366-371、K/src/kage_shiki/agent/agent_core.py:322-326 | その日の会話そのものは、次の起動へは持ち越さない（同 :512） |
| BH-15 | 1日の会話が、キャラの日記（数文）にまとまる。終わるときに書き、書けなかった日は次に起きたときに遡って埋める | US-3, US-5 / FR-3.8, FR-3.10, FR-7.5 | Must | 実装済み | K/docs/specs/phase1-mvp/requirements.md:508、K/docs/specs/phase1-mvp/requirements.md:510、K/docs/specs/phase1-mvp/requirements.md:561、K/src/kage_shiki/main.py:356-361 | 前身では日記を5〜8文としていた（K/docs/specs/phase1-mvp/requirements.md:115） |
| BH-16 | 閉じても、落ちても、電源の都合で終わっても、会話の記録は失われない。終わり方が何通りあっても、終わりの処理は1回だけ走る | US-5 / FR-3.9, FR-7.3, NFR-9 | Must（書込の待ち FR-7.3 は Should） | 実装済み | K/docs/specs/phase1-mvp/requirements.md:509、K/docs/specs/phase1-mvp/requirements.md:559、K/docs/specs/phase1-mvp/requirements.md:577、K/src/kage_shiki/main.py:468-469、K/src/kage_shiki/memory/db.py:199 | 目的の禁則「記憶を失わない」。前身は実起動でここを踏んでいる（lessons.md へ） |
| BH-17 | 長く話し込んでも、キャラの人格と今の会話は最後まで保たれる。入りきらなくなったら、昔の記憶の方から削る | US-11 / FR-6.2, FR-8.7 | Must | 実装済み | K/docs/specs/phase2a-foundation/requirements.md:68、K/docs/specs/phase2a-foundation/requirements.md:110-117、K/docs/specs/phase2a-foundation/requirements.md:216、K/src/kage_shiki/agent/agent_core.py:332-334 | 削る順：関連する昔の発言 → 日記 → 今の会話の古い方。人格は最後まで残す |
| BH-18 | 主人について、主人がはっきり言ったことだけを覚えていく。推測では書かず、その場限りのことは書かず、食い違ったら新しい方を採る | US-1, US-7 / FR-4.5, FR-6.6 | Must | 実装済み | K/docs/specs/phase1-mvp/requirements.md:277-281、K/docs/specs/phase1-mvp/requirements.md:522、K/docs/specs/phase1-mvp/requirements.md:550、K/src/kage_shiki/agent/agent_core.py:741-748 | **保護指定4**（主人についての欄は主人も AI も書ける側。K/docs/memos/middle-draft/07-character-design.md:248） |

## 4. 根っこは変わらない

出典：K/docs/specs/phase1-mvp/requirements.md:58、K/docs/memos/2026-03-03-char.md:9-10

| 行 | ふるまい | 元 | 優先度 | 前身での状況 | 出典 | 紐付け・備考 |
|---|---|---|---|---|---|---|
| BH-19 | 確定した人格の根っこ（名前・一人称・呼び方・性格・口調・口癖・価値観・禁忌など）と口調の見本は、AI が書き換えられない。変えられるのは主人の手だけ | US-7 / FR-4.1, FR-4.2, FR-4.3 | Must | 実装済み | K/docs/specs/phase1-mvp/requirements.md:58、K/docs/specs/phase1-mvp/requirements.md:518-520、K/docs/memos/middle-draft/07-character-design.md:246-247、K/docs/memos/middle-draft/07-character-design.md:270-275、K/src/kage_shiki/persona/persona_system.py:281-292 | **保護指定4**。目的の禁則「凍結核を AI が書き換えない」。中身の一覧は concept.md（前身の C1〜C11・S1〜S7） |
| BH-20 | 主人が書ける部分と書けない部分が分かれている。主人が書く：自分についての欄、確定前の根っこ、関係の変化の承認。主人が書かない：会話の記録・日記・好奇心の軌跡（書き換えると記憶や「自分で調べた」が嘘になる） | US-7 / FR-4.3, FR-4.5, FR-4.6 | Must | 実装済み（書く側の線引きまで。主人が記憶を眺める画面は未着手） | K/docs/memos/2026-03-03-char.md:10、K/docs/memos/middle-draft/07-character-design.md:244-253、K/docs/memos/middle-draft/07-character-design.md:257-268 | **保護指定4**。権限の全表は concept.md。記憶を眺める画面は前身で Phase 2 以降へ送られた（K/docs/specs/phase1-mvp/requirements.md:43） |
| BH-21 | 主人が根っこを手で書き換えたら、キャラの側が気づく | US-7 / FR-4.4 | May | 実装済み（前身では記録に警告を残すだけ。設計にあった「再凍結しますか」の確認は無い） | K/docs/specs/phase1-mvp/requirements.md:521、K/docs/memos/middle-draft/07-character-design.md:275、K/src/kage_shiki/main.py:334-335 | **保護指定4** |
| BH-22 | 関係の変化（呼び方・感情の傾向・新しい口癖）は、キャラが会話の中で提案し、主人が承認したときだけ書き加わる | US-7 / FR-4.6 | Must | 実装済み | K/docs/specs/phase1-mvp/requirements.md:324、K/docs/specs/phase1-mvp/requirements.md:523、K/docs/memos/middle-draft/07-character-design.md:249、K/src/kage_shiki/agent/agent_core.py:763-778 | **保護指定4**。根っこ以外が歴史で変わる、の入口 |
| BH-23 | 返事の前に「このキャラならどう反応するか」を踏まえ、一定の間隔（前身の既定では15発言ごと）で人格のぶれを自分で点検する | US-7 / FR-6.3, FR-6.4 | Must（定期点検 FR-6.4 は Should） | 実装済み | K/docs/specs/phase1-mvp/requirements.md:547-548、K/src/kage_shiki/agent/agent_core.py:313-320、K/src/kage_shiki/agent/agent_core.py:369-371 | 人格らしさの最終判定は主人（CLAUDE.md §2） |
| BH-24 | 気持ちを「（嬉しそうに）」のような括弧書きで書かず、言葉づかいだけで表す | US-1, US-7 / FR-6.5 | Must | 実装済み | K/docs/specs/phase1-mvp/requirements.md:549、K/src/kage_shiki/agent/prompt_builder.py:61 | |
| BH-25 | 人格のファイルが壊れていたら、人格のないまま動き出さない。起動を止めて主人に知らせる | US-7 / FR-4.8, FR-7.4 | Must | 実装済み | K/docs/specs/phase1-mvp/requirements.md:525、K/docs/specs/phase1-mvp/requirements.md:560、K/src/kage_shiki/main.py:311-321 | |

## 5. 自分から動く

出典：K/docs/specs/phase2b-autonomy/requirements.md:69-76、K/docs/memos/方向性.md:18-20

前身では、この節のふるまいはモジュールと単体テストまで作られ、起動経路への組み込み（前身の Wave 5）に手が付かないまま止まった（§8）。

| 行 | ふるまい | 元 | 優先度 | 前身での状況 | 出典 | 紐付け・備考 |
|---|---|---|---|---|---|---|
| BH-26 | メインループは止まらずに回り、いくつかの行動予定（前身では「話したい／知りたい／振り返りたい／休みたい」の4つの欲求）がそれぞれの活性で、やる・やらないが決まる。活性の計算そのものには AI を呼ばない | US-14 / FR-9.1, FR-9.2 | Must | 未統合 | K/docs/memos/方向性.md:18-20、K/docs/memos/middle-draft/02-personality-system.md:93-106、K/docs/specs/phase2b-autonomy/requirements.md:100、K/docs/specs/phase2b-autonomy/requirements.md:114、K/docs/specs/phase2b-autonomy/requirements.md:221-222 | **保護指定2**。同じ欲求で続けて話しかけない（活性の間は1回だけ） |
| BH-27 | しばらく話していないと、キャラの方からひとこと話しかけてくる（前身では30分ほど入力が無いのが目安） | US-14 / FR-9.3 | Must | 未統合 | K/docs/specs/phase2b-autonomy/requirements.md:71、K/docs/specs/phase2b-autonomy/requirements.md:126、K/docs/specs/phase2b-autonomy/requirements.md:228、K/src/kage_shiki/agent/agent_core.py:275-278 | **保護指定2**。「相手から話しかけてくれる」が「そばにいる」の核 |
| BH-28 | 自分からの発言はうるさくない。短い独り言で（前身では50字以内）、頻度は控えめな側に倒す | US-15 / FR-9.4 | Must（独り言の文脈 FR-9.4 は Should） | 未統合 | K/docs/specs/phase2b-autonomy/requirements.md:72、K/docs/specs/phase2b-autonomy/requirements.md:229、K/docs/specs/phase2b-autonomy/requirements.md:358、K/docs/memos/middle-draft/02-personality-system.md:85-87、K/src/kage_shiki/agent/autonomous_prompt.py:29 | **保護指定2**。目的の禁則「うるさくない側に倒す」。1対1では「うるさい」が致命的という判断 |
| BH-29 | 主人が話しかけたら、自分からのふるまいは即座に引く。主人の入力が常に最優先（前身では、途中まで進んだ生成は終わるのを待って結果を捨てる方式） | US-17 / FR-9.5 | Must | 未統合（入力のときに行動予定を下げる呼び出しが、前身の `src/` のどこにも無い） | K/docs/specs/phase2b-autonomy/requirements.md:74、K/docs/specs/phase2b-autonomy/requirements.md:235、K/docs/specs/phase2b-autonomy/requirements.md:361、K/src/kage_shiki/agent/desire_worker.py:414、K/src/kage_shiki/agent/agent_core.py:475-478 | **保護指定2**。目的の禁則「入力が来たら即座に引く」 |
| BH-30 | 会話で気になった話題を、キャラが自分で調べ始め（「〜が気になってた」）、終わったら「〜だったよ」と短く話す | US-16 / FR-9.6, FR-9.7 | Should | 未統合 | K/docs/specs/phase2b-autonomy/requirements.md:73、K/docs/specs/phase2b-autonomy/requirements.md:241-242、K/src/kage_shiki/agent/agent_core.py:643-647、K/src/kage_shiki/agent/autonomous_prompt.py:74 | 調べた結果が可変層（興味の広がり）に積もり、後の会話で使われる（K/docs/memos/middle-draft/07-character-design.md:210） |
| BH-31 | 調べた先で見つけた別の話題が、次の興味として積み上がる。増えすぎないよう上限がある | US-16 / FR-9.8, FR-9.11 | Could（興味の記録 FR-9.11 は Must） | 未統合 | K/docs/specs/phase2b-autonomy/requirements.md:137、K/docs/specs/phase2b-autonomy/requirements.md:243、K/docs/specs/phase2b-autonomy/requirements.md:261、K/src/kage_shiki/agent/agent_core.py:594-620 | 前身の要件の対応表では FR-9.11 は US に紐付いていない。ここでは US-16 に寄せた |
| BH-32 | 主人が同じ話題に触れると、その話題を調べる順番が早まる | FR-9.12（前身の対応表では US 未紐付け。US-16 に寄せた） | Could | 未着手（順番を変える関数はあるが、主人の発言と照らし合わせる処理も、それを呼ぶ所も無い） | K/docs/specs/phase2b-autonomy/requirements.md:262、K/src/kage_shiki/memory/db.py:584 | |
| BH-33 | ときどき「ちょっと考え事してた」と、最近の日記を振り返った独り言を言う | US-18 / FR-9.9 | Could | 未統合 | K/docs/specs/phase2b-autonomy/requirements.md:75、K/docs/specs/phase2b-autonomy/requirements.md:249、K/src/kage_shiki/agent/autonomous_prompt.py:47 | |
| BH-34 | 長く動いていると「ちょっと眠い」と休みの気配を見せる。続けて何度も言わない | US-14 / FR-9.1 | Must（FR-9.1 として） | 未統合 | K/docs/specs/phase2b-autonomy/requirements.md:129-130、K/docs/specs/phase2b-autonomy/requirements.md:307、K/src/kage_shiki/agent/autonomous_prompt.py:57 | 見せ方（短くなる・テンポが落ちる等）は前身でも決めきっていない（同 :316） |

## 6. 開発者向け（lessons.md へ送る）

出典：K/docs/specs/phase2a-foundation/requirements.md:65-67、K/docs/specs/phase2b-autonomy/requirements.md:76

主人から見えるふるまいではない。行としては残し、中身（なぜ要ったか・次にどう確かめるか）は `lessons.md` で扱う。

| 行 | ふるまい | 元 | 優先度 | 前身での状況 | 出典 | 紐付け・備考 |
|---|---|---|---|---|---|---|
| BH-35 | 開発者向け：段階の完了前に、実際に起動して触る手順（起動・対話・終了・2回目の起動）と画面の目視項目がある | US-8 / FR-8.1, FR-8.2 | Must | 実装済み | K/docs/specs/phase2a-foundation/requirements.md:65、K/docs/specs/phase2a-foundation/requirements.md:195-196、K/docs/testing/smoke-test.md:1-4 | 開発者向け。lessons.md へ送る |
| BH-36 | 開発者向け：複数の流れの受け渡し・既存の記憶がある状態での起動・終了の全経路を、自動の試験で確かめる | US-9 / FR-8.3, FR-8.4, FR-8.5 | Must | 実装済み | K/docs/specs/phase2a-foundation/requirements.md:66、K/docs/specs/phase2a-foundation/requirements.md:202-204 | 開発者向け。lessons.md へ送る（前身の実起動の不具合から出た宿題） |
| BH-37 | 開発者向け：AI の呼び先を、上の処理を変えずに差し替えられる | US-10 / FR-8.6 | Should | 実装済み | K/docs/specs/phase2a-foundation/requirements.md:67、K/docs/specs/phase2a-foundation/requirements.md:210、K/src/kage_shiki/agent/llm_client.py:50 | 開発者向け。lessons.md へ送る |
| BH-38 | 開発者向け：自分で調べる仕組みの中身を、上の処理を変えずに差し替えられる | US-19 / FR-9.10 | Should | 未統合（差し替え口と1つ目の実装はあるが、起動経路で組み込まれていない） | K/docs/specs/phase2b-autonomy/requirements.md:76、K/docs/specs/phase2b-autonomy/requirements.md:255、K/src/kage_shiki/agent/agentic_search.py:60、K/src/kage_shiki/agent/agentic_search.py:291 | 開発者向け。lessons.md へ送る |

## 7. 主人が触って出した要望（前身で未対応のもの）

出典：K/docs/memos/feedback-smoketest-2026-03-07.md:24-53

前身の US にも FR にも入っていないが、主人が実際に触って出した言葉なので、振る舞いとして残す。

| 行 | ふるまい | 元 | 優先度 | 前身での状況 | 出典 | 紐付け・備考 |
|---|---|---|---|---|---|---|
| BH-39 | キャラの主人の呼び方が、関係の深さで変わる（はじめは「さん」付け、親しくなって主人が望めば「くん」「ちゃん」へ）。やり取りの欄に出る主人の名前とは別物として扱う | 主人の要望 F-1 | — | 未着手 | K/docs/memos/feedback-smoketest-2026-03-07.md:26-34 | 根っこの「呼び方」との関係は未決（呼び方は前身では凍結核に入っている。K/docs/specs/phase1-mvp/requirements.md:168） |
| BH-40 | キャラを作り直すときは取り返しがつく。二重に確かめ、前のキャラに戻せる | 主人の要望 F-2 | — | 未着手（前身では確認1回と控え1世代だけ） | K/docs/memos/feedback-smoketest-2026-03-07.md:36-43、K/src/kage_shiki/tray/system_tray.py:88-89 | 目的の禁則「記憶を失わない」に近い |
| BH-41 | キャラ作りで広げる連想の数を、主人が調整できる | 主人の要望 F-3 | — | 実装済み（前身では設定値で） | K/docs/memos/feedback-smoketest-2026-03-07.md:45-48、K/docs/specs/phase1-mvp/requirements.md:340 | |
| BH-42 | おまかせで作るとき、候補の3体を見せてもらい、主人が選ぶ | 主人の要望 F-4 | — | 未着手（前身では AI が最も点の高い1体を自動で選んでいた） | K/docs/memos/feedback-smoketest-2026-03-07.md:50-53 | 前身の要件 FR-5.2 の「選択」を、主人の手に戻す要望 |

## 8. 状況の判定根拠

出典：K/src/kage_shiki/main.py:398-406、K/docs/tasks/phase2b-autonomy-tasks.md:497-508

前身の README と SESSION_STATE は食い違っているので採らず、git log と `src/` で判定した。

- **前身の最終コミット**は `39b030f`（2026-07-20、Phase 2b の Wave 3 完了記録）。
- **Phase 1 の範囲（§1〜§4 の多く）**：起動の組み上げ `e889601`、実起動の不具合7件の修正 `bc9710d`、主人の触った感想の12件修正 `fe9fd6e` を経て、`main.py` から呼ばれている（各行の `main.py`・`agent_core.py` の出典）。
- **Phase 2a の範囲（BH-04・BH-08・BH-09・BH-17・BH-35〜37）**：`aaab8a5`・`d74f5f5`・`6eb645b`・`7d2c928`・`248ad8f`、完了は `1ac18a9`（「スモークテスト全項目パス」）。
- **Phase 2b の範囲（§5 と BH-38）**：欲求・調べる仕組み・興味の記録は `89f9fe5`（Wave 1）、自分からの発言は `7d4677a`（Wave 2）、調べる流れは `c45ae99`（Wave 3）で入った。しかし `main.py` は相棒の本体を欲求と調べる仕組み**抜き**で組み立てており（K/src/kage_shiki/main.py:398-406）、本体の側にも「組み込みは Wave 5 で」と書かれている（K/src/kage_shiki/agent/agent_core.py:275-283）。前身の作業計画も Wave 5 を未着手としている（K/docs/tasks/phase2b-autonomy-tasks.md:504-508）。よって**未統合**と判定した。
- **白紙育成の全体像の提案（BH-12）**も、提案を作る処理が `wizard.py` の外から呼ばれていないので未統合とした。
- 前身の作業ツリーには、コミットされていない変更が `src/` の3ファイル（`agent_core.py`・`agentic_search.py`・`config.py`）にある。どれも Phase 2b の本体側で、`main.py` は変わっていないため、判定は変わらない。出典の行番号はこの作業ツリーの内容に合わせている。

## 9. 保護指定との対応と、拡張口

出典：K/docs/memos/方向性.md:15-20、K/docs/memos/2026-03-03-char.md:10-11、K/docs/memos/middle-draft/04-unified-design.md:22-25

| 保護指定 | 中身 | 紐付けた行 | 前身での状況 |
|---|---|---|---|
| 保護指定1 | 窓のヘリを突っつくと反応する。そこを体の代わりにする | BH-05 | 反応はある。ただしヘリではなく専用ボタン |
| 保護指定2 | メインループは止まらない。行動予定の活性でやる・やらないを決める | BH-26、BH-27、BH-28、BH-29 | すべて未統合 |
| 保護指定3 | 主人が書いた部分以外は、AI が調べながら作る。その過程のゆらぎが唯一無二にする | BH-10、BH-11 | 連想のゆらぎは実装済み。「調べながら」は未着手 |
| 保護指定4 | 主人が書ける部分と書けない部分を分ける | BH-12、BH-18、BH-19、BH-20、BH-21、BH-22 | 書く側の線引きは実装済み |

**拡張口（AITuber）**：前身の US-1〜US-19 に、1対多の配信へ寄ったふるまいは無い。前身の設計はそもそも 1対1 と 1対多 の違いから制約を決めている（K/docs/memos/middle-draft/04-unified-design.md:22-25）ので、「拡張口」と印を付ける行は無かった。
