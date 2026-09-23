"""Utsushimi：人格を持ち、記憶を引き継ぐ、1対1の常駐デスクトップの相棒。"""
from pathlib import Path

# 主人の機械だけで動く（ADR 0001）。リポジトリの置き場がそのまま実行の置き場になる。
REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "data"
