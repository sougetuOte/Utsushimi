# spikes/ — Phase 1 の使い捨てスパイク

**本体に持ち込まない。**結果と消滅条件は `docs/research/2026-09-23-phase1-spike.md`。

## 共通の約束（3候補が同じにふるまう）

- 窓：題名 `utsushimi-spike-<候補>`、枠なし、380×260（論理ピクセル）。
  上端から 8px の縁 → 高さ 22 の帯（中に「×」）→ 会話の欄 → 高さ 24 の入力行、下の余白 12、左右の余白 12。
- 縁（外周 8px）を押す → ログ `poke edge x y`。内側を押す → `click inner x y`。帯を押してドラッグ → 窓が動く。
- 「×」と Alt+F4 → 隠れてトレイに残る（`hide`）。トレイの左クリック → `show`。トレイの右クリック「終了」→ `shutdown count=N`。
- 送信 → SQLite（WAL・`synchronous=FULL`）に1行書いてコミット → `send id=N` → 裏で `--bg-seconds` 秒待つ（LLM 呼び出しの代わり）。
  その間 UI スレッドのタイマーが 20ms ごとに刻み、`bg end maxgap=…ms input_during_bg="…"` を出す。
- 起動 → `start pid=… console=none|present loaded=<読んだ行数> tray=…`。
- 引数：`--run-dir DIR`（既定は実行ファイルの隣の `run/`）、`--auto-send TEXT`、`--bg-seconds N`、`--topmost`。

## 用意（Windows 11）

| 候補 | 用意 | 実行ファイル |
|---|---|---|
| pyside6 | `uv venv --python 3.14 spikes/pyside6/.venv` → `uv pip install --python spikes/pyside6/.venv/Scripts/python.exe PySide6==6.11.2` | `spikes/pyside6/.venv/Scripts/python.exe spikes/pyside6/spike.py` |
| tauri | `cd spikes/tauri && npm install && npx tauri build --no-bundle`（Rust stable-msvc・VS 2022 の C++ ビルドツール・WebView2） | `spikes/tauri/src-tauri/target/release/spike-tauri.exe` |
| wpf | `dotnet build -c Release spikes/wpf`（.NET SDK 10） | `spikes/wpf/bin/Release/net10.0-windows/SpikeWpf.exe` |

## 計測

```
python spikes/tools/check.py <pyside6|tauri|wpf>       # S1〜S7。pwsh（PowerShell 7）が要る
python spikes/tools/footprint.py <pyside6|tauri|wpf>   # 参考：起動時間とメモリ
```

`check.py` はマウスとキーボードを合成して動かす。走っている間（約25秒）は触らない。
