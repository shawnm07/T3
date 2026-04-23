"""News sentiment via Alpaca news + simple lexical scoring.

Future: swap in a proper model (FinBERT) when we want more signal.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

POSITIVE = {
    "beat", "beats", "surge", "rally", "soar", "upgrade", "upgraded", "bullish",
    "breakthrough", "record", "strong", "growth", "expand", "expansion", "accelerate",
    "outperform", "buyback", "raise", "raised", "profit", "profitable", "crush", "tops",
}
NEGATIVE = {
    "miss", "missed", "plunge", "drop", "tumble", "downgrade", "downgraded", "bearish",
    "lawsuit", "probe", "investigation", "fraud", "scandal", "warn", "warning", "cut",
    "loss", "losses", "layoff", "layoffs", "bankrupt", "default", "recall", "weak",
    "decline", "slow", "slowdown", "concern", "concerns", "fears",
}


@dataclass
class SentimentSignal:
    symbol: str
    score: float
    article_count: int
    positive_hits: int
    negative_hits: int
    top_headlines: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "score": round(self.score, 3),
            "article_count": self.article_count,
            "positive_hits": self.positive_hits,
            "negative_hits": self.negative_hits,
            "top_headlines": self.top_headlines[:5],
        }


def _score_text(text: str) -> tuple[int, int]:
    words = text.lower().split()
    pos = sum(1 for w in words if w.strip(".,!?:;") in POSITIVE)
    neg = sum(1 for w in words if w.strip(".,!?:;") in NEGATIVE)
    return pos, neg


def score_news_for_symbol(symbol: str, news_items: list) -> SentimentSignal:
    pos_total = 0
    neg_total = 0
    headlines: list[str] = []
    for item in news_items:
        if getattr(item, "symbols", None) and symbol not in item.symbols:
            continue
        headline = getattr(item, "headline", "") or ""
        summary = getattr(item, "summary", "") or ""
        p, n = _score_text(headline + " " + summary)
        pos_total += p
        neg_total += n
        headlines.append(headline[:140])
    total = pos_total + neg_total
    if total == 0:
        score = 0.0
    else:
        raw = (pos_total - neg_total) / total
        score = float(max(-1.0, min(1.0, raw * min(1.0, total / 8))))
    return SentimentSignal(
        symbol=symbol, score=score,
        article_count=len(headlines),
        positive_hits=pos_total, negative_hits=neg_total,
        top_headlines=headlines,
    )
