"""Manual kill switch: pause / resume autonomous trading immediately.

  py scripts/halt.py               # show status
  py scripts/halt.py pause "reason"
  py scripts/halt.py resume
"""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.kill_switch import is_manually_halted, manual_halt, manual_resume


def main() -> int:
    if len(sys.argv) < 2:
        halted, reason = is_manually_halted()
        print(f"Manual halt: {'ON' if halted else 'OFF'}" + (f" — {reason}" if reason else ""))
        return 0
    action = sys.argv[1].lower()
    if action == "pause":
        reason = " ".join(sys.argv[2:]) or "manual"
        manual_halt(reason)
        print(f"PAUSED — {reason}")
    elif action == "resume":
        manual_resume()
        print("RESUMED")
    else:
        print("Usage: halt.py [pause <reason>|resume]")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
