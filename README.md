# 写し身 (Utsushimi)

**"Not yet divine. Not yet free."**

人格を持ち、記憶を引き継ぐ、Windows 常駐のテキスト・デスクトップ相棒。
前身 [影式 (Kage-Shiki)](https://github.com/sougetuOte/Kage-Shiki) の作り直しです。

- 人格の根っこは最初に決めたら変わらず、根っこ以外が共に過ごした歴史で変わっていく
- 会話の記憶はセッションをまたいで続き、異常終了でも失われない
- 同じ入力から同じキャラは二度と生まれない（生成時のゆらぎによる唯一性）

## 状態

作り直しの途中（2026年10月）。段1の骨格・人格の器・キャラ作りができたところで、最初の起動で主人と AI が一緒にキャラを生み、
そのキャラと話せて、話したことが残ります。

## 起動（主人の機械）

用意（最初の1回）：

1. [uv](https://docs.astral.sh/uv/) を入れる。Python 3.14 は uv が用意する。
2. リポジトリの直下で `uv sync` を実行する（`.venv` ができる）。
3. リポジトリの直下に `.env` を置き、`ANTHROPIC_API_KEY=...` を1行書く（git に載らない）。
4. スタートメニューにショートカットを作る（PowerShell。リポジトリの直下で）：

   ```powershell
   $s = (New-Object -ComObject WScript.Shell).CreateShortcut([Environment]::GetFolderPath('Programs') + '\Utsushimi.lnk')
   $s.TargetPath = "$PWD\.venv\Scripts\pythonw.exe"; $s.Arguments = '-m utsushimi'; $s.WorkingDirectory = "$PWD"; $s.Save()
   ```

いつもの起動：スタートメニューの **Utsushimi** を開く。コンソールの窓は出ない。

- 最初の起動（`data/persona/` が無いとき）は、キャラ作りの画面が出る。「おまかせ」（キーワードから AI が調べながら候補を3体考える）か
  「既存イメージ」（ほしい相棒を自由に書く）を選び、候補とお試しで話してから「確定」する。確定すると、そのまま会話の窓に替わる。
  同じキーワードでも、作るたびに違うキャラが生まれる。生まれた経緯は `data/persona/origin.md` に残る。
- 窓の上の帯をドラッグで動かせる。「×」で隠れてトレイに残る。
- トレイのアイコンを左クリックで出し入れ、右クリックで「表示」「隠す」「終了」。終わるのは「終了」だけ。
- 会話・設定・ログは `data/` の下（git に載らない）。設定は `data/config.toml`（最初の起動で `config.default.toml` から作る）。
- 人格は `data/persona/core.md`（根っこ C1〜C11）と `style.md`（口調の見本 S1〜S7）。本体が書くのはキャラ作りで確定したときだけで、
  固めた後は書き換えない。必須の項目が欠けていると起動を止めて知らせる。固めた後に手で書き換えると、次の起動で「この内容で固め直す／このまま使う」を問う。
- キャラ作りで広げる連想の数は `data/config.toml` の `[creation] associations`（既定5）で変えられる。
- 起動するとキャラから最初のひと言がある。

## 開発

Claude Code で開発しています。方針は [`CLAUDE.md`](CLAUDE.md)、現在地は [`SESSION_STATE.md`](SESSION_STATE.md) にあります。

**見取り図**：プロジェクトの発端から今までを、年表・追跡・決定・本体の構造・文書の地図・前身とのずれ・気がかり・分岐の角度から見る HTML 群です。
リポジトリの今の中身（git の履歴と、git に載った文書・コード）から作り直します。生成物は git に載りません。

```
uv run python tools/overview/build.py
```

できた `build/overview/index.html` をブラウザで開きます。図のライブラリは CDN から読むので、ネットにつながっている必要があります。

## ライセンス

MIT
