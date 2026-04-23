"""Does trimming winners when their technical score cools actually help?

Simulates two strategies on a diversified basket over 5+ years:
  A: hold_through  - once entered, hold until exit signal (tech<-0.3 or stop).
  B: trim_on_cool  - trim 30% of position any time tech score drops from >0.5 to <0.3
                     while in profit. Reinvest freed cash into fresh top-scored entry.

Entry rule: tech score > 0.5. Exit rule: tech score < -0.3 OR -6% stop OR +15% target.
Both strategies identical except for the trim behavior.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
import yfinance as yf

BASKET = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "JPM",
          "V", "UNH", "LLY", "AVGO", "HD", "WMT", "XOM", "CVX", "KO",
          "PEP", "NFLX", "AMD"]
YEARS = 5
STOP_PCT = -0.06
TARGET_PCT = 0.15
TRIM_FRAC = 0.30


def tech_score(df: pd.DataFrame) -> pd.Series:
    """Simple composite: SMA trend + RSI-normalized + momentum."""
    close = df["Close"]
    sma20 = close.rolling(20).mean()
    sma50 = close.rolling(50).mean()
    trend = np.sign(sma20 - sma50) * np.minimum(abs((sma20 - sma50) / sma50), 0.1) * 10
    # RSI-14
    delta = close.diff()
    up = delta.clip(lower=0).rolling(14).mean()
    down = (-delta.clip(upper=0)).rolling(14).mean()
    rs = up / down.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    rsi_score = (rsi - 50) / 50  # -1 to +1
    # 20-day momentum
    mom = (close / close.shift(20) - 1).clip(-0.3, 0.3) / 0.3
    score = 0.4 * trend + 0.3 * rsi_score + 0.3 * mom
    return score.clip(-1, 1)


def load_panel(basket: list[str], years: int) -> dict[str, pd.DataFrame]:
    end = pd.Timestamp.today()
    start = end - pd.Timedelta(days=365 * years + 60)
    raw = yf.download(basket, start=start, end=end, auto_adjust=True, progress=False)
    panel = {}
    for s in basket:
        try:
            df = pd.DataFrame({"Close": raw["Close"][s]}).dropna()
            df["score"] = tech_score(df)
            panel[s] = df.dropna()
        except KeyError:
            continue
    return panel


def simulate(panel: dict[str, pd.DataFrame], strategy: str, capital: float = 100_000) -> dict:
    """Single-position-per-symbol simulation. Allocates up to 10% equity per trade."""
    # Get unified date range
    all_dates = sorted(set().union(*[set(df.index) for df in panel.values()]))
    cash = capital
    positions: dict[str, dict] = {}  # symbol -> {entry, shares, peak_score}
    equity_curve = []
    trades = 0
    trims = 0

    for date in all_dates:
        # Update equity mark
        mv = cash
        for sym, pos in positions.items():
            if date in panel[sym].index:
                mv += pos["shares"] * panel[sym].at[date, "Close"]
        equity_curve.append(mv)

        # Exits & trims
        for sym in list(positions.keys()):
            if date not in panel[sym].index:
                continue
            df = panel[sym]
            close = df.at[date, "Close"]
            score = df.at[date, "score"]
            pos = positions[sym]
            ret = close / pos["entry"] - 1
            # Hard exits
            if ret <= STOP_PCT or ret >= TARGET_PCT or score < -0.3:
                cash += pos["shares"] * close
                del positions[sym]
                trades += 1
                continue
            # Strategy-specific trim
            if strategy == "trim_on_cool":
                # Trim when score cools from >0.5 peak to <0.3 while in profit
                pos["peak_score"] = max(pos["peak_score"], score)
                if pos["peak_score"] > 0.5 and score < 0.3 and ret > 0:
                    trim_shares = pos["shares"] * TRIM_FRAC
                    cash += trim_shares * close
                    pos["shares"] -= trim_shares
                    pos["peak_score"] = score  # reset so we don't re-trim immediately
                    trims += 1

        # Entries: pick best-scoring symbol not already held, if score > 0.5 and cash > min
        cand_scores = {}
        for sym, df in panel.items():
            if sym in positions or date not in df.index:
                continue
            s = df.at[date, "score"]
            if pd.notna(s) and s > 0.5:
                cand_scores[sym] = s
        if cand_scores and cash > capital * 0.05:
            # Enter up to 3 new positions per day, best-scoring first
            best = sorted(cand_scores.items(), key=lambda x: x[1], reverse=True)[:3]
            for sym, _ in best:
                alloc = min(cash * 0.5, capital * 0.10)  # 10% per position
                if alloc < capital * 0.02:
                    break
                price = panel[sym].at[date, "Close"]
                shares = alloc / price
                positions[sym] = {"entry": price, "shares": shares, "peak_score": panel[sym].at[date, "score"]}
                cash -= shares * price
                trades += 1

    # Final liquidation
    last_date = all_dates[-1]
    for sym, pos in positions.items():
        if last_date in panel[sym].index:
            cash += pos["shares"] * panel[sym].at[last_date, "Close"]

    eq = pd.Series(equity_curve, index=all_dates)
    years = (all_dates[-1] - all_dates[0]).days / 365.25
    cagr = (cash / capital) ** (1 / years) - 1
    dd = ((eq / eq.cummax()) - 1).min()
    daily_ret = eq.pct_change().dropna()
    sharpe = (daily_ret.mean() / daily_ret.std()) * np.sqrt(252) if daily_ret.std() > 0 else 0
    return {
        "strategy": strategy, "final": cash, "cagr": cagr,
        "max_dd": dd, "sharpe": sharpe, "trades": trades, "trims": trims,
    }


def main() -> None:
    print(f"Loading {YEARS} years of data for {len(BASKET)} symbols...")
    panel = load_panel(BASKET, YEARS)
    print(f"Loaded {len(panel)} symbols\n")

    results = []
    for strat in ("hold_through", "trim_on_cool"):
        r = simulate(panel, strat)
        results.append(r)
        print(f"{strat:15s} final=${r['final']:>11,.0f} CAGR={r['cagr']:>6.2%} "
              f"maxDD={r['max_dd']:>6.1%} Sharpe={r['sharpe']:.2f} "
              f"trades={r['trades']:>4d} trims={r['trims']:>3d}")

    hold, trim = results
    diff = trim["final"] - hold["final"]
    print(f"\nTrim-on-cool vs hold-through: {diff:+,.0f} ({trim['cagr']-hold['cagr']:+.2%} CAGR)")


if __name__ == "__main__":
    main()
