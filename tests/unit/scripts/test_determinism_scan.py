from pathlib import Path

from qnwis.scripts.qa.determinism_scan import scan_for_banned_calls


def test_scan_for_banned_calls_flags_patterns(tmp_path: Path) -> None:
    target = tmp_path / "alert_stack.py"
    target.write_text(
        "from datetime import datetime\n"
        "import time\n"
        "import random\n"
        "\n"
        "value = datetime.now()\n"
        "epoch = time.time()\n"
        "noise = random.random()\n",
        encoding="utf-8",
    )

    violations = scan_for_banned_calls([target])

    assert violations, "Expected determinism violations to be reported"
    patterns = {item["pattern"] for item in violations}
    assert {"datetime.now", "time.time", "random.*"} <= patterns


def test_scan_for_banned_calls_clean(tmp_path: Path) -> None:
    target = tmp_path / "safe_stack.py"
    target.write_text("from datetime import datetime\nvalue = datetime.utcnow()", encoding="utf-8")

    violations = scan_for_banned_calls([target])

    assert violations == []
