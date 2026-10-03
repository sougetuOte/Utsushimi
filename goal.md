# goal.md — 段1 T3「キャラ作り」

**状態：承認済み（2026-10-03 主人）**
種別：feature（G0 あり）。材料は `docs/specs/stage1/`（tasks の T3、design §2・§3・§4.1・§4.3・§4.8・§5・§6）、`docs/concept.md` §8.2〜§8.9、ADR 0002・0003。モデルは Opus 5.5（D8）。
基準コミット（着手前）= `51d0330`。前身 = `C:\work5\Kage-Shiki`（以下 `K/`）。

範囲：主人と AI が一緒にキャラを生み、ゆらぎを経て固める流れを、T2 までの本体に足す。中身は `tasks.md` の T3 の記述どおりで、
キャラ作りの画面（おまかせ・既存イメージ）、5段の生成と核の乱数（外から与える）、サーバー側の web search、候補3体、お試しの会話、
確定（`seal()`）と `origin.md`、LLM の口を偽物に替える設定（BH-37）を作る。確定したら、起動し直さずに会話の窓へ移る。
前置きとして、T2 の確かめで `data/` に溜まった物を `data/smoke/t2/` へ移す。

design が決めていない所は、次のとおりにする。

- `data/persona/` に `core.md` と `style.md` がどちらも無く、`persona_seal` にも行が無いときに、キャラ作りの画面を出す。
  ファイルが無いのに封の行があるときは、固めた人格のファイルが消えた状態なので、新しいキャラは作らずに T2 と同じ「壊れている」小窓を出す。
- キャラ作りの画面は枠のある普通の窓にし、方式（おまかせ／既存イメージ）の選択と入力を同じ画面に置く。
  この窓を閉じるとアプリが終わる（design §4.8 の経路。終了の全経路を確かめるのは T5）。
- おまかせの入力はキーワードだけにする（design §4.3）。呼び方などを細かく決めたいときは、既存イメージの記述に書く。
- 連想は、LLM に設定の数より多く出させてから、核の乱数で設定の数（`[creation] associations`、既定5）だけ選ぶ。調べる語は、選んだ連想から核の乱数で1〜2語を選ぶ。
- 候補は名前（C1）と人格核文（C4）で並べる。候補を選ぶと、その候補の口調の見本（S1〜S7）を作ってからお試しの会話に入る。
  お試しの画面には「確定」と「やり直す」を置き、「やり直す」は同じ候補の並びに戻る。
  候補の画面には「作り直す」を置き、同じ入力のまま段2（連想）からやり直す。既存イメージの候補は1体にする。
- お試しの発言は `utterances` に種類 `trial` で残す。確定した後の会話の欄と文脈には、種類 `dialogue` の発言だけを入れる。
- 会話の欄でキャラの発言に付ける名前を、C1 の名前にする（T2 までは仮に「Utsushimi」としていた）。
- 確定の口 `seal(draft)` は、`core.md`・`style.md`・`origin.md` を書いてから `persona_seal` に1行足す。`persona_seal` に行があれば、ファイルに触れずに拒む。
  `origin.md` の見出しは `## 日時`・`## モデル`・`## 方式`・`## 主人の入力`・`## 連想`・`## 調べた語`・`## 要点` の7つにし、乱数の種を書く欄は置かない。
- 生成の途中で API が失敗したら、画面に理由を出して入力の画面へ戻る。入れた言葉は残す。
- LLM の呼び先は `data/config.toml` の `[llm] target`（`anthropic`／`fake`）で選ぶ。`fake` は決まった返事を返し、Anthropic のクライアントを作らない。
  核の乱数は、本番では `random.SystemRandom`（種を持たない）で作る。種を `data/config.toml` から読むのは、呼び先が `fake` のときだけにする。
- `data/config.toml` に無い項目は `config.default.toml` の値を使う（T1 から残る `data/config.toml` には、T3 で足す項目が無いため）。

## 完了条件

1. T2 の残りを移した：T3 の確かめを始める前に、`data/utsushimi.db`・`data/persona/`・`data/logs/utsushimi.log` を `data/smoke/t2/` の下へ移した。
   消さないのは、前のフェーズの主張（完了条件13）を検収で確かめるためである。`data/config.toml` は残す。
2. 人格が無ければキャラ作りから始まる（BH-06・BH-07・BH-09）：人格が無い状態で実起動するとキャラ作りの画面が出て、
   設定ファイルもコマンドも触らずに、おまかせと既存イメージのそれぞれを確定まで通せた。
3. 候補を選び、試し、戻り、確定する（BH-08・BH-42・B-9）：実起動したおまかせで、候補3体が名前と人格核文つきで並び、選んだ1体と3往復お試しで話し、
   「やり直す」で候補選びに戻れ、「作り直す」で新しい候補3体が並び、「確定」で起動し直さずに会話の窓に移った。
   会話の欄ではキャラの発言に C1 の名前が付いていた。そのあと本アプリのプロセスは1つだけだった。
4. 同じキーワードから別のキャラが生まれ、経緯が残る（BH-10・BH-11）：データを分けて2回、同じキーワードでおまかせのキャラを作ると、
   2体の名前・人格核文・連想が違った。どちらの `origin.md` にも経緯（日時・モデル・方式・主人の入力・連想・調べた語と要点）があり、乱数の種はどこにも無かった。
   どちらのキャラでも、調べた要点のどれかが確定した人格の文に現れていた。
5. 連想の数を変えられる（BH-41）：設定の連想の数を 3 と 7 にしてそれぞれ実起動し、`origin.md` の連想の数が設定どおりだった。
6. 偽物の口でゆらぎを止められる（BH-37・禁則「ゆらぎはテストで外から固定できる」）：LLM の呼び先を偽物にし、核の乱数の種を固定して、データを分けて2回実起動すると、
   キャラ作りから会話まで API を呼ばずに通せ、2回の `core.md` が1バイトも違わなかった。
7. 主人が書いた所が残る（保護指定3）：既存イメージの記述に書いた名前と一人称が、確定した `core.md` の C1 と C2 に入っていた。
8. 根っこを書く口は確定だけ（BH-19）：`src/` で `data/persona/` の下へ書くのは確定の口だけで、その口は `persona_seal` に行があれば書かずに拒む。
   固めた人格のファイルが無くなった状態で実起動すると、キャラ作りの画面ではなく「壊れている」小窓が出た。
9. 閉じたら終わり、失敗したら戻る：キャラ作りの画面を閉じると、数秒以内に本アプリのプロセスが残らなかった。
   生成の途中で API が失敗すると、画面に理由が出て入力の画面に戻り、入れた言葉が残っていた。
10. 手順書（B-10・共通）：`docs/smoke-test.md` に 2〜9 の確かめ方とキャラ作りの画面の目視項目がある。
    その全項目と T1・T2 の項目 S-1〜S-8・S-10 を、T3 の本体で実起動して通した日付と結果が報告に書かれている（S-9 は時間帯を2つまたぐので通し直さない）。
11. 目視（L-5・共通）：キャラ作りの画面の各場面と、確定の後の会話の窓を実起動して目で確かめ、はみ出し・重なり・操作できない部分が無かったことが報告に書かれ、
    それぞれのスクリーンショットがある。
12. 秘密が漏れない：API キーがコミットにもログにも出ていない。人格のファイルと `data/` がコミットに無い。
13. 前のフェーズの締めの主張が事実と合っている：検収を通っていない `d11dff7`（T7 に1行足した）と `51d0330`（T2 の締め）が、
    `SESSION_STATE.md` とコミットメッセージに書いた主張が、それが指す場所の事実と合っている。

### ログの語（検収はこの語で数える）

T1・T2 の語はそのまま使う。足すのは次の語で、本文と人格の中身はログに出さない。

| 出来事 | 語 |
|---|---|
| 起動のたびの呼び先と乱数の出どころ | `llm target=<anthropic\|fake>`・`rng source=<os\|fixed>`（種の値は出さない） |
| 人格が無い | `persona absent` |
| キャラ作りの画面を出した | `creation show` |
| 作り始めた | `creation begin method=<omakase\|image>` |
| 連想を選んだ | `creation associations setting=<数> offered=<数> chosen=<数>` |
| 調べた | `creation search words=<数> queries=<数>` |
| 候補が並んだ | `creation candidates n=<数>` |
| 候補を選んだ・見本を作った | `creation pick index=<番号>`・`creation style index=<番号>` |
| お試しの発言の保存 | `trial send id=<番号>`・`trial reply id=<番号>` |
| やり直す・作り直す | `creation back`・`creation redo` |
| 生成の失敗 | `creation failed stage=<段> reason=<例外の型>` |
| 確定した | `persona sealed core=<sha256> style=<sha256>` |
| 会話の窓に移った | `show via=creation` |
| 呼び出しごとの使用量 | T2 の `usage` の `kind=` に `associate`・`search`・`integrate`・`style`・`trial` を足す。呼び先が `fake` のときは出さない |

## 検証方法

検収役が見る。採点範囲は本フェーズの成果コミット（`51d0330` より後で、報告に列挙したもの）に限る。
実起動の証拠は git の外にある：ログ `data/logs/utsushimi.log`、各起動のデータの置き場（`data/` と、移した先の `data/smoke/t3/<名前>/`）、
スクリーンショットと報告（`data/smoke/t3/`）。報告に、各完了条件を確かめた起動のプロセス番号・時刻・データの置き場を書く。
検収役はその番号でログを引き、DB を読み取り専用で開いて突き合わせる。確かめで作るキャラは使い捨てなので、報告に人格の中身（名前や語句）を写してよい。

| # | 完了条件 | 確かめ方 |
|---|---|---|
| V1 | 1 | `data/smoke/t2/` の下に `utsushimi.db`・`persona/core.md`・`persona/style.md`・`utsushimi.log` がある。`data/logs/utsushimi.log` の最初の行の時刻と、報告に列挙した T3 の DB すべての `lifecycle` の最初の行の `started_at` が、本フェーズの G0 コミットの時刻より後 |
| V2 | 2 | 報告のおまかせの起動と既存イメージの起動のそれぞれで、同じプロセス番号の行に順に `persona absent`・`creation show`・`creation begin method=omakase`（既存イメージは `image`）・`creation candidates`・`creation pick`・`persona sealed`・`show via=creation` があり、`persona absent` から `show via=creation` までのあいだに別のプロセス番号の `start` が無い。どちらの起動にも `llm target=anthropic` と `rng source=os` がある |
| V3 | 3 | V2 のおまかせの起動に、`creation candidates n=3` の後の `creation pick`、`trial send id=` と `trial reply id=` が3行以上ずつ、`creation back`、`creation redo` の後の `creation candidates n=3` がある。その `trial` の番号の `utterances` の種類が `trial`。`data/smoke/t3/` の候補の画面のスクリーンショットで3体の名前と人格核文が読め、確定の後の会話の窓のスクリーンショットで最初の挨拶に C1 の名前が付いている（検収役が画像を見る）。報告に、`show via=creation` の後に取った `pythonw.exe` の一覧（プロセス番号・親の番号・コマンドライン）があり、ログの番号の本体と、その親（venv の起動器）のほかに無い |
| V4 | 4 | 報告の2つの起動（同じキーワード）で `creation associations` の `setting=` が同じ。それぞれの置き場の `origin.md` に上の7つの見出しがあって中身が空でなく、7つ以外の見出しが無い。`## 主人の入力` は2つで同じで、`core.md` の C1 と C4、`origin.md` の `## 連想` は2つで違う。2つの置き場の `core.md`・`style.md`・`origin.md` に `[Ss][Ee][Ee][Dd]` の当たりが0件。`src/` で、本番の乱数が `random.SystemRandom` から作られ、種を読むのは呼び先が `fake` のときだけ（検収役がコードを読む）。報告に、起動ごとに `## 要点` にある語句1つと、それが現れる `core.md` か `style.md` の見出しが書かれ、検収役がその語句を両方のファイルで grep して当たる |
| V5 | 5 | 報告の2つの起動の `creation associations` の行が、それぞれ `setting=3` と `chosen=3`、`setting=7` と `chosen=7` を含む。それぞれの置き場の `origin.md` の `## 連想` の中の、行頭が `- ` の行が3行と7行 |
| V6 | 6 | 報告の2つの起動のそれぞれに、`llm target=fake`・`rng source=fixed`・`persona sealed`・`show via=creation` と、その後の `send id=` と `reply id=` が1組以上あり、同じ番号の `usage` と `ERROR` が0行。2つの `persona sealed` の `core=` が同じ。報告に、2回ともダミーの `ANTHROPIC_API_KEY` を本アプリのプロセスにだけ渡して起動したことと、そのコマンドがある。`src/` で、呼び先が `fake` のとき Anthropic のクライアントを作らない（検収役がコードを読む） |
| V7 | 7 | 報告に既存イメージの起動で入れた記述が写してあり、その起動の置き場の `core.md` の C1 の中身が記述の名前を含み、C2 の中身が記述の一人称を含む。その `origin.md` の `## 主人の入力` が記述と同じ |
| V8 | 8 | `grep -rnE "write_text\|write_bytes\|open\(\|\.replace\(\|\.rename\(\|shutil\.\|unlink\|mkdir" src/` の当たりのうち `data/persona/` に触るものが、すべて `persona.py` の確定の口の中にあり、その口は `persona_seal` に行があるとファイルに触れる前に拒む（検収役がコードを読む）。報告の起動（封の行がある DB のまま `data/persona/` を移した状態）に `persona broken file=core.md heading=- reason=missing` と `persona broken file=style.md heading=- reason=missing` があり、`creation show` が無い |
| V9 | 9 | 報告の閉じた起動に、`creation show` の後の `shutdown begin via=creation_close call=1` と `shutdown done` があり、報告に閉じた後の `tasklist` の出力（本アプリの `pythonw.exe` が無い）がある。報告の失敗の起動に `creation failed stage=` の行があり、`data/smoke/t3/` にその後の画面のスクリーンショット（理由と、入れた言葉が残った入力欄が読める）がある |
| V10 | 10 | `docs/smoke-test.md` に T3 の項目（2〜9 にあたるもの）とキャラ作りの画面の目視項目がある。報告に、S-1〜S-8・S-10 と T3 の全項目の実施日と結果（可／不可）がある |
| V11 | 11 | `data/smoke/t3/` に、方式と入力（おまかせ・既存イメージ）・経過・候補・お試し・失敗の各場面と、確定の後の会話の窓のスクリーンショットが1枚以上ずつある（検収役が画像を見て、はみ出し・重なりが無いことを確かめる）。報告に目視の結果がある |
| V12 | 12 | `git log -p 51d0330..<最後の成果コミット>` を `grep -E 'sk-ant-[A-Za-z0-9]'` で見て0件。`data/logs/utsushimi.log` に `sk-ant` が0件。成果コミットに `.env`・`data/`・`.venv/` のパスが無い |
| V13 | 13 | `git show 51d0330:<パス> \| wc -l` が、`51d0330` の `SESSION_STATE.md` の「読む順序」の数と合う：`goal.md` 109、`docs/concept.md` 681、`docs/behaviors.md` 140、`docs/lessons.md` 236、`docs/adr/0001`〜`0004` がどれも44〜61、`docs/specs/stage1/` の requirements 96・design 214・tasks 87、`docs/smoke-test.md` 93、`docs/research/2026-09-23-phase1-spike.md` 88、`docs/research/2026-09-23-overview-tools.md` 65。`51d0330` の `src/utsushimi/` の `.py` が7本で、行数の和が660〜680 |
| V14 | 13 | `51d0330` の `src/` に、キャラ作り・日記・検索・2重起動の防止・突っつき・最前面の処理が無い（検収役がコードを読む）。長い返事の自動スクロールが無いことは、V16 の主人の発話（スクロールしないと末尾が読めない）で確かめる |
| V15 | 13 | `data/smoke/t2/utsushimi.log` の `start console=` の行のうち、日付が 2026-09-23 のものが8行。`data/smoke/t2/utsushimi.db` の `utterances` が54行 |
| V16 | 13 | セッションの記録 `C:\Users\metral\.claude\projects\D--work8-Utsushimi\d88bd052-e627-4add-a13c-eb3aca3fea65.jsonl` のうち、`type` が `user` で `isSidechain` が false の行の、主人が打った本文（`message.content` の文字列か `text` の塊。`tool_result` は除く）に、次の4つがある：「ちゃんと朝の挨拶になりました」（朝の挨拶の判定）、「複数行の発言の時は私が能動的にスクロールさせる必要がある」（`d11dff7` の指摘）、「君の判断に任せる」（別コミットの委任）、「SESSION_STATE と tasks の更新、承認する」（`51d0330` の承認）。同じフォルダの下の `*/subagents/*.meta.json` のうち、`agentType` が `seneschal:columba` で `description` が `T2「人格の器」の検収` のものが1つだけで、その記録の判定が PASS で、V1〜V13 がすべて PASS |
| V17 | 範囲 | `git diff --name-only 51d0330..<最後の成果コミット>` が、`goal.md`・`src/`・`docs/smoke-test.md`・`README.md`・`config.default.toml` の下だけ |
| V18 | やらないこと | 前身に書き込んでいない：`git -C C:\work5\Kage-Shiki rev-parse --short HEAD` が `39b030f` |
| V19 | 品質 | 成果の Markdown に制御文字 `[\x00-\x08\x0b\x0c\x0e-\x1f]` が無い |

時間で壊れないように、証拠は足すだけの物（ログ・`utterances`・`persona_seal`）、移した先に残した物、報告に書き写した値で見る。
「今の `data/persona/` のハッシュ」「今プロセスが無いこと」のような、検収の時点で変わる値は物差しにしない。

## G1 の事前承認（この goal の承認に含む）

- T2 の残りを `data/smoke/t2/` へ移すこと。確かめの間に、`data/` の DB と人格を `data/smoke/t3/<名前>/` へ移して、人格の無い状態を作り直すこと（どちらも消さない）。
- 確かめのために `data/config.toml` を書き換え（連想の数・呼び先・種）、終わったら元の中身に戻すこと。
- S-7・S-8 の通し直しのために、`data/persona/` のファイルを手で書き換え（C1 を消す・1文字変える）、写しから戻すこと。
- Anthropic API を実際に呼ぶこと（`.env` のキー、`claude-opus-5-5`）。呼び出しは目安100回以内、web search の検索は30回以内。
  web search では、確かめ用のキーワードから出た語が検索語として外へ送られる。最初に web search を1回だけ呼んで使えるかを確かめ、使えなければ止めて主人に返す（Console の設定は主人がする）。
- 失敗と偽物の確かめで、ダミーの `ANTHROPIC_API_KEY` を本アプリのプロセスにだけ渡して起動すること（主人の環境変数は変えない）。
- 確かめの間、合成入力で主人の PC のマウスとキーボードを動かすこと（主人に PC から離れてもらう）。スクリーンショットは本アプリの窓の範囲だけを撮る。

## やらないこと

### このフェーズではやらない

- 白紙から育てる（BH-07 の一部・BH-12）と、確定の後に作り直す口（BH-40）。どちらも段2以降
- 日記・検索・文脈の上限（T4）、2重起動の防止と終了の全経路（T5）、主人について・関係の変化・点検（T6）、
  突っつき・最前面・最初の文字までの秒数・長い返事の自動スクロール（T7）。お試しの欄のスクロールも、会話の欄と同じ今の作りのままにする
- 生まれたキャラの手触りを作り込むことと、判定すること（判定は主人がする。完了条件は事実だけにする。requirements の「読み方」）
- 本物の相棒を生むこと（検収の後に主人が自分で生む）。確かめで作るキャラはすべて使い捨てにする
- モデルを役割で分けること（ADR 0003）
- 自動テストを書くこと（完了は実起動で数える。確かめ用の使い捨てスクリプトはスクラッチに置き、コミットしない）
- `CLAUDE.md`・`SESSION_STATE.md`・`docs/specs/`・`docs/concept.md` の書き換え（`SESSION_STATE.md` と `tasks.md` の ☑ は検収後に別コミット）
- `data/smoke/` の中身をごみ箱へ移すこと（検収の後、主人の指示で）
- push（検収 PASS の後、主人の指示で）

### 起きてはならない

- 前身（`C:\work5\Kage-Shiki`）への書込。前身の `data/` と `.env` の読込（機構なし。検収でも見えない）
- API キー・`.env`・`data/`・`.venv/` のコミット。キーと人格のファイルの中身をログに書くこと
- `data/` の下のファイルを消すこと（ごみ箱へ移すことも含む。このフェーズの片づけは移すだけ）
- 本番の乱数の種をどこかに書くこと
- 主人に求めずに行うグローバル導入・処理系のインストール・Anthropic のアカウントや Console の設定の変更
- 承認後の `goal.md` の書き換え（誤りは訂正節で足す）
- 自分で検収を採点すること
- 成果コミットの amend・force push（検収の指摘は訂正コミットで直す）
