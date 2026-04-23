"""Backtest: parking idle cash reserve in SPY vs keeping as cash.

Simulates the 20% cash reserve over multiple years under several rotation regimes:
  - Never deployed (pure SPY-park vs pure cash)
  - Moderate rotation (withdraw/redeposit a fraction weekly)
  - Heavy rotation (drain to zero every few weeks, refill)

Critically, deployments are timed to be correlated with SPY drawdowns — the bot
wants cash most when markets sold off, so SPY-parking means selling low.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
import yfinance as yf

RESERVE = 20_000.0
YEARS = 10
ROUNDTRIP_BP = 2.0  # ~1bp each leg, SPY is tight
SEED = 42


def load_spy(years: int) -> pd.DataFrame:
    end = pd.Timestamp.today()
    start = end - pd.Timedelta(days=365 * years + 30)
    df = yf.download("SPY", start=start, end=end, auto_adjust=True, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df[["Close"]].dropna().copy()
    df["ret"] = df["Close"].pct_change().fillna(0.0)
    return df


def sim_pure_park(df: pd.DataFrame) -> dict:
    """Never withdraw — full SPY exposure on the reserve."""
    end_val = RESERVE * (df["Close"].iloc[-1] / df["Close"].iloc[0])
    years = len(df) / 252
    cagr = (end_val / RESERVE) ** (1 / years) - 1
    max_dd = ((df["Close"] / df["Close"].cummax()) - 1).min()
    return {"strategy": "pure SPY park", "end_value": end_val,
            "cagr": cagr, "max_dd": max_dd, "turns": 0}


def sim_cash(df: pd.DataFrame, cash_yield: float = 0.0) -> dict:
    years = len(df) / 252
    end_val = RESERVE * (1 + cash_yield) ** years
    return {"strategy": f"cash ({cash_yield:.0%})", "end_value": end_val,
            "cagr": cash_yield, "max_dd": 0.0, "turns": 0}


def sim_rotating_park(df: pd.DataFrame, turnover_per_year: float,
                      correlation: float, rng: np.random.Generator) -> dict:
    """Simulate SPY-parked reserve where a fraction is periodically
    withdrawn (bot deploys capital) and later returned (bot closes position).

    correlation: +1 = withdraws perfectly timed to SPY drawdowns (worst case),
                  0 = random timing,
                 -1 = withdraws when SPY is up (best case).
    """
    close = df["Close"].values
    n = len(close)
    cycles = int(turnover_per_year * (n / 252))
    # A 'cycle' = withdraw ~40% of reserve, redeposit ~2-5 days later.
    withdraw_frac = 0.4
    hold_days = 5

    # Pick withdrawal days biased by SPY 5-day forward drawdown (to model
    # "we need cash when market is falling" when correlation > 0).
    # Backward-looking: how much has SPY dropped in the past 10 days?
    # Realistic concern: bot needs capital AFTER market selloff → sells SPY low.
    past_max = pd.Series(close).rolling(10).max()
    past_dd = (close - past_max.values) / past_max.values  # negative when SPY is below recent peak
    ranks = pd.Series(past_dd).rank(pct=True).values  # low rank = deepest current drawdown
    if correlation > 0:
        weights = (1 - ranks) ** (3 * correlation)
    elif correlation < 0:
        weights = ranks ** (3 * -correlation)
    else:
        weights = np.ones_like(ranks)
    weights = np.nan_to_num(weights, nan=0.0)
    # Constrain to valid days (leave buffer for hold_days)
    valid = np.arange(n - hold_days - 1)
    w = weights[valid]
    w = w / w.sum()
    draw_days = rng.choice(valid, size=min(cycles, len(valid)), replace=False, p=w)
    draw_days = np.sort(draw_days)

    # Track shares of SPY + parked-out cash separately.
    shares = RESERVE / close[0]
    parked_cash = 0.0
    friction_cost = 0.0
    withdraw_schedule = {int(d): None for d in draw_days}
    # Each draw_day: sell fraction of shares -> parked_cash; after hold_days, buy back.
    deposit_schedule: dict[int, float] = {}

    for i in range(n):
        # Return previously-parked cash to SPY
        if i in deposit_schedule:
            amt = deposit_schedule.pop(i)
            # Friction on buy-back
            amt_after = amt * (1 - ROUNDTRIP_BP / 2 / 10000)
            shares += amt_after / close[i]
            friction_cost += amt - amt_after

        if i in withdraw_schedule:
            # Sell withdraw_frac of current shares worth
            current_value = shares * close[i]
            sell_value = current_value * withdraw_frac
            sell_value_after = sell_value * (1 - ROUNDTRIP_BP / 2 / 10000)
            friction_cost += sell_value - sell_value_after
            shares -= sell_value / close[i]
            parked_cash += sell_value_after
            # schedule return
            return_day = min(i + hold_days, n - 1)
            deposit_schedule[return_day] = deposit_schedule.get(return_day, 0) + parked_cash
            parked_cash = 0  # transferred to schedule

    # Final value: remaining shares + any still-parked cash
    final = shares * close[-1] + sum(deposit_schedule.values()) + parked_cash
    years = n / 252
    cagr = (final / RESERVE) ** (1 / years) - 1
    # Reconstruct equity curve approximation for max_dd
    return {"strategy": f"rotating SPY ({turnover_per_year:.0f}/yr, corr={correlation:+.1f})",
            "end_value": final, "cagr": cagr, "max_dd": None,
            "friction": friction_cost, "turns": len(draw_days)}


def main() -> None:
    df = load_spy(YEARS)
    print(f"SPY data: {df.index[0].date()} to {df.index[-1].date()} ({len(df)} days)")
    spy_cagr = (df["Close"].iloc[-1] / df["Close"].iloc[0]) ** (252 / len(df)) - 1
    print(f"SPY CAGR over window: {spy_cagr:.2%}\n")

    rng = np.random.default_rng(SEED)
    rows = []
    rows.append(sim_cash(df, cash_yield=0.0))     # paper account
    rows.append(sim_cash(df, cash_yield=0.045))   # real account with sweep
    rows.append(sim_pure_park(df))

    # Rotating: sweep across turnover and correlation assumptions
    for tpy in (12, 52, 104):  # monthly, weekly, twice-weekly withdraw cycles
        for corr in (-0.5, 0.0, +0.5, +1.0):
            rng2 = np.random.default_rng(SEED + int(tpy * 10 + corr * 10))
            rows.append(sim_rotating_park(df, tpy, corr, rng2))

    out = pd.DataFrame(rows)
    out["end_value"] = out["end_value"].round(0)
    out["cagr"] = (out["cagr"] * 100).round(2).astype(str) + "%"
    if "friction" in out.columns:
        out["friction"] = out["friction"].fillna(0).round(0)
    print(out.to_string(index=False))
    print()

    # Headline comparisons
    pure = next(r for r in rows if r["strategy"] == "pure SPY park")
    cash0 = next(r for r in rows if r["strategy"] == "cash (0%)")
    cash4 = next(r for r in rows if r["strategy"] == "cash (4%)")

    print(f"Pure SPY-park gain vs paper cash:      ${pure['end_value'] - cash0['end_value']:+,.0f}")
    print(f"Pure SPY-park gain vs 4% cash sweep:   ${pure['end_value'] - cash4['end_value']:+,.0f}")
    print(f"Pure SPY-park max drawdown:            {pure['max_dd']:.1%}")

    worst_case = [r for r in rows if "corr=+1.0" in r["strategy"]]
    if worst_case:
        print("\nWorst-case (deployments perfectly aligned with SPY drawdowns):")
        for r in worst_case:
            diff = r["end_value"] - pure["end_value"]
            print(f"  {r['strategy']}: end=${r['end_value']:,.0f} "
                  f"(vs pure-park: {diff:+,.0f}, friction ${r['friction']:,.0f})")


if __name__ == "__main__":
    main()
