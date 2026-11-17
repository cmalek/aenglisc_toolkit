"""QProcess PDF compile job."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import QWidget

from oeapp.ui.pdf_export_job import PdfExportJob


def _job(qtbot) -> tuple[QWidget, PdfExportJob]:
    """Return a job and the widget that owns it."""
    parent = QWidget()
    qtbot.addWidget(parent)
    return parent, PdfExportJob(parent)


def test_pdf_job_success(qtbot, tmp_path: Path) -> None:
    """A zero exit reports success."""
    script = tmp_path / "ok.py"
    script.write_text(
        "import sys\n"
        "from pathlib import Path\n"
        "args = sys.argv[1:]\n"
        "outdir = Path(args[args.index('--outdir') + 1])\n"
        "(outdir / 'full_translation.pdf').write_bytes(b'%PDF')\n",
        encoding="utf-8",
    )
    work = tmp_path / "work"
    work.mkdir()
    _parent, job = _job(qtbot)

    with qtbot.waitSignal(job.finished, timeout=5000) as blocker:
        job.start(sys.executable, [str(script), "--outdir", str(work)])

    cancelled, code, _stdout, _stderr = blocker.args
    assert cancelled is False
    assert code == 0
    assert (work / "full_translation.pdf").read_bytes() == b"%PDF"


def test_pdf_job_failure(qtbot, tmp_path: Path) -> None:
    """A non-zero exit keeps stderr for the error dialog."""
    script = tmp_path / "bad.py"
    script.write_text(
        "import sys\nprint('bad tex', file=sys.stderr)\nsys.exit(2)\n",
        encoding="utf-8",
    )
    _parent, job = _job(qtbot)

    with qtbot.waitSignal(job.finished, timeout=5000) as blocker:
        job.start(sys.executable, [str(script)])

    cancelled, code, _stdout, stderr = blocker.args
    assert cancelled is False
    assert code == 2
    assert "bad tex" in stderr


def test_pdf_job_cancel(qtbot, tmp_path: Path) -> None:
    """Cancel kills a running compile."""
    script = tmp_path / "sleep.py"
    script.write_text(
        "import time\nprint('started', flush=True)\ntime.sleep(30)\n",
        encoding="utf-8",
    )
    _parent, job = _job(qtbot)

    with qtbot.waitSignal(job.status_text, timeout=5000):
        job.start(sys.executable, [str(script)])
    with qtbot.waitSignal(job.finished, timeout=5000) as blocker:
        job.cancel()

    cancelled, _code, _stdout, _stderr = blocker.args
    assert cancelled is True


def test_pdf_job_failed_to_start(qtbot, tmp_path: Path) -> None:
    """A missing program is reported instead of hanging."""
    _parent, job = _job(qtbot)

    with qtbot.waitSignal(job.finished, timeout=5000) as blocker:
        job.start(str(tmp_path / "missing-tectonic"), [])

    cancelled, code, _stdout, stderr = blocker.args
    assert cancelled is False
    assert code == -1
    assert stderr
