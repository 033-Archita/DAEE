import sys
from pathlib import Path

from app.main import main


def test_demo_mode_writes_sample_html(tmp_path: Path, monkeypatch) -> None:
    output_path = tmp_path / "daily-curiosity-demo.html"
    monkeypatch.setattr(sys, "argv", ["app.main", "--demo", "--demo-output", str(output_path)])

    exit_code = main()

    assert exit_code == 0
    assert output_path.exists()
    html = output_path.read_text(encoding="utf-8")
    assert "Your Daily Curiosity" in html
    assert "Tomorrow's rabbit hole" in html
