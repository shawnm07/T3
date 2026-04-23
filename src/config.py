"""Config loader: merges .env secrets with config.yaml strategy settings."""
from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


@dataclass(frozen=True)
class AlpacaConfig:
    api_key: str
    api_secret: str
    base_url: str
    data_url: str
    mode: str


@dataclass(frozen=True)
class Config:
    alpaca: AlpacaConfig
    raw: dict[str, Any]

    @classmethod
    def load(cls, config_path: Path | str | None = None) -> "Config":
        path = Path(config_path) if config_path else ROOT / "config.yaml"
        with open(path) as f:
            raw = yaml.safe_load(f)
        alpaca = AlpacaConfig(
            api_key=os.environ["ALPACA_API_KEY"],
            api_secret=os.environ["ALPACA_API_SECRET"],
            base_url=os.environ.get("ALPACA_BASE_URL", "https://paper-api.alpaca.markets"),
            data_url=os.environ.get("ALPACA_DATA_URL", "https://data.alpaca.markets"),
            mode=os.environ.get("ALPACA_MODE", "paper"),
        )
        return cls(alpaca=alpaca, raw=raw)

    def get(self, *keys: str, default: Any = None) -> Any:
        node: Any = self.raw
        for k in keys:
            if not isinstance(node, dict) or k not in node:
                return default
            node = node[k]
        return node
