"""Utsushimi：人格を持ち、記憶を引き継ぐ、1対1の常駐デスクトップの相棒。"""
import os
from pathlib import Path

# 主人の機械だけで動く（ADR 0001）。リポジトリの置き場がそのまま実行の置き場になる。
REPO = Path(__file__).resolve().parents[2]
# データの置き場。確かめの起動は UTSUSHIMI_DATA で別のフォルダを渡し、主人の相棒が住む data/ に触らない
DATA_SOURCE = "env" if os.environ.get("UTSUSHIMI_DATA") else "default"
DATA = Path(os.environ["UTSUSHIMI_DATA"]) if DATA_SOURCE == "env" else REPO / "data"
