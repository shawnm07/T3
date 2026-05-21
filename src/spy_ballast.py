"""SPY-ballast cap + idle-cash treasury proxy routing.

Before 2026-05-11 the bot would park unused equity in SPY whenever a scan
failed to find ≥3 names that cleared its gates. On 2026-05-11 that meant
~78% of equity sat in SPY all day on a -0.12% loss — beta exposure with
none of the alpha.

Post-fix: cap SPY at ``risk.max_spy_pct`` (default 30%). Any idle equity
above that cap routes to the short-duration treasury proxy
(``risk.cash_proxy_idle_symbol``, default BIL).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from src.config import Config

log = logging.getLogger(__name__)


@dataclass
class BallastTargets:
    spy_target_pct: float
    bil_target_pct: float
    cash_target_pct: float
    rerouted_pct: float
    audit: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "spy_target_pct": round(self.spy_target_pct, 4),
            "bil_target_pct": round(self.bil_target_pct, 4),
            "cash_target_pct": round(self.cash_target_pct, 4),
            "rerouted_pct": round(self.rerouted_pct, 4),
            "audit": self.audit,
        }


def split_idle_ballast(
    cfg: Config,
    proposed_spy_pct: float,
    proposed_cash_pct: float = 0.0,
) -> BallastTargets:
    """Take a selector-proposed SPY weight and split anything over the cap
    into BIL. The cash target is preserved as-is (operational buffer).
    """
    cap = float(cfg.get("risk", "max_spy_pct", default=1.0) or 1.0)
    bil_symbol = str(cfg.get("risk", "cash_proxy_idle_symbol", default="BIL") or "BIL")
    spy_target = max(0.0, float(proposed_spy_pct or 0.0))
    cash_target = max(0.0, float(proposed_cash_pct or 0.0))
    rerouted = 0.0
    if spy_target > cap and cap > 0.0:
        rerouted = spy_target - cap
        spy_target = cap
    audit = {
        "max_spy_pct": cap,
        "proposed_spy_pct": float(proposed_spy_pct or 0.0),
        "proposed_cash_pct": float(proposed_cash_pct or 0.0),
        "rerouted_to": bil_symbol,
        "rerouted_pct": rerouted,
    }
    return BallastTargets(
        spy_target_pct=spy_target,
        bil_target_pct=rerouted,
        cash_target_pct=cash_target,
        rerouted_pct=rerouted,
        audit=audit,
    )


def force_deploy_failure(
    cfg: Config,
    macro_score: float,
    cash_pct: float,
    selected_count: int,
) -> dict[str, Any] | None:
    """Return a "scanning failure" audit when the bot is sitting on cash
    in a risk-on tape without finding enough names.

    Caller (orchestrator / EOD report) decides whether to alert.
    """
    if float(macro_score or 0.0) <= 0.40:
        return None
    if float(cash_pct or 0.0) < 0.20:
        return None
    if int(selected_count or 0) >= 4:
        return None
    return {
        "kind": "force_deploy_failure",
        "macro_score": float(macro_score),
        "cash_pct": float(cash_pct),
        "selected_count": int(selected_count),
        "message": (
            f"Risk-on macro ({macro_score:+.2f}) but only {selected_count} "
            f"selections with {cash_pct*100:.1f}% cash idle — investigate gate calibration."
        ),
    }
