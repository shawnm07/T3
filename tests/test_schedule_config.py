from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def test_8am_phoenix_scan_is_in_schedule_script_and_config():
    config = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    assert config["scheduling"]["intraday_times"] == [
        "10:00",
        "11:00",
        "12:00",
        "13:00",
        "14:00",
        "15:00",
    ]

    setup_script = (ROOT / "scripts" / "setup_schedule.ps1").read_text(encoding="utf-8")
    assert '"08:00"' in setup_script
    assert "--scheduled-run" in setup_script
    assert "10/11/12/13/14/15 ET EDT" in setup_script
