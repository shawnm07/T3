"""Quick: measure size of last selector_input event in decisions.jsonl."""
import json
from pathlib import Path

p = Path(__file__).resolve().parents[1] / "data" / "journal" / "decisions.jsonl"
with p.open() as f:
    lines = f.readlines()

for ln in reversed(lines):
    try:
        d = json.loads(ln)
    except json.JSONDecodeError:
        continue
    if d.get("event") == "selector_input":
        ctx = d.get("context", {}) or {}
        ctx_str = json.dumps(ctx)
        print("=== selector_input ===")
        print(f"context bytes: {len(ctx_str):,}")
        print(f"approx tokens: ~{len(ctx_str) // 4:,}")
        print("keys:", sorted(ctx.keys()))
        print(f"candidate_pool size: {len(ctx.get('candidate_pool', []))}")
        if ctx.get("candidate_pool"):
            s0 = ctx["candidate_pool"][0]
            print("sample candidate keys:", sorted(s0.keys()))
            ic = s0.get("intraday_chart")
            print(f"intraday_chart bytes: {len(json.dumps(ic)) if ic else 0}")
            print(f"avg candidate bytes: {sum(len(json.dumps(c)) for c in ctx['candidate_pool']) // len(ctx['candidate_pool']):,}")
        rd = ctx.get("recent_decisions", {})
        print(f"recent_decisions bytes: {len(json.dumps(rd)):,}")
        print(f"spy_block bytes: {len(json.dumps(ctx.get('spy_block', {}))):,}")
        print(f"trading_rules bytes: {len(json.dumps(ctx.get('trading_rules', []))):,}")
        break
else:
    print("no selector_input event found in jsonl")
