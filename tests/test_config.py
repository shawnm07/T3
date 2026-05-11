from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config import Config


def test_config_load_reads_utf8_yaml(tmp_path, monkeypatch):
    monkeypatch.setenv("ALPACA_API_KEY", "key")
    monkeypatch.setenv("ALPACA_API_SECRET", "secret")

    config_path = tmp_path / "config.yaml"
    config_path.write_text('risk:\n  note: "weight \u221d score"\n', encoding="utf-8")

    cfg = Config.load(config_path)

    assert cfg.raw["risk"]["note"] == "weight \u221d score"
