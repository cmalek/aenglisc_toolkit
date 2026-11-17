"""Run Tectonic in a ``QProcess`` so the window stays responsive."""

from __future__ import annotations

from PySide6.QtCore import QObject, QProcess, Signal, Slot


class PdfExportJob(QObject):
    """
    Compile one LaTeX file with an external process.

    Args:
        parent: Owning widget. The process is stopped when the parent is
            destroyed.

    """

    #: ``(cancelled, exit_code, stdout, stderr)``. Exit code ``-1`` means the
    #: program failed to start.
    finished = Signal(bool, int, str, str)
    #: Latest compiler output line, for the progress dialog.
    status_text = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        """
        Initialize the instance.

        Args:
            parent: Owning widget.

        """
        super().__init__(parent)
        #: External Tectonic process.
        self._process = QProcess(self)
        #: Text Tectonic wrote to stdout.
        self._stdout = ""
        #: Text Tectonic wrote to stderr.
        self._stderr = ""
        #: Whether :meth:`finished` has already been emitted.
        self._reported = False
        #: Whether the user asked to stop the compile.
        self._cancelled = False
        self._process.finished.connect(self._on_finished)
        self._process.errorOccurred.connect(self._on_error)
        self._process.readyReadStandardOutput.connect(self._on_output)
        self._process.readyReadStandardError.connect(self._on_output)

    def start(self, program: str, arguments: list[str]) -> None:
        """
        Start ``program`` with ``arguments``.

        Args:
            program: Absolute path to the executable.
            arguments: Arguments, not including the program.

        """
        self._stdout = ""
        self._stderr = ""
        self._reported = False
        self._cancelled = False
        self._process.setProgram(program)
        self._process.setArguments(arguments)
        self._process.start()

    @Slot()
    def cancel(self) -> None:
        """Stop the compile."""
        self._cancelled = True
        if self._process.state() == QProcess.ProcessState.NotRunning:
            self._report(cancelled=True, code=-1)
            return
        self._process.kill()

    def wait_until_finished(self, timeout_ms: int = 5000) -> bool:
        """
        Block until the process has exited.

        Call this on the GUI thread before destroying the job. ``QProcess``
        waits in its destructor when it is destroyed while still running.

        Args:
            timeout_ms: How long to wait, in milliseconds.

        Returns:
            True when the process is no longer running.

        """
        if self._process.state() == QProcess.ProcessState.NotRunning:
            return True
        return bool(self._process.waitForFinished(timeout_ms))

    @Slot(int, QProcess.ExitStatus)
    def _on_finished(self, code: int, _status: QProcess.ExitStatus) -> None:
        """
        Report the process exit.

        Args:
            code: Process exit code.
            _status: Normal exit or crash.

        """
        self._report(cancelled=self._cancelled, code=code)

    @Slot(QProcess.ProcessError)
    def _on_error(self, error: QProcess.ProcessError) -> None:
        """
        Report a process that never started.

        A crash also emits ``finished``, which carries the exit code.

        Args:
            error: Why ``QProcess`` failed.

        """
        if error == QProcess.ProcessError.FailedToStart:
            self._stderr = self._stderr or "Failed to start the PDF engine."
            self._report(cancelled=False, code=-1)

    @Slot()
    def _on_output(self) -> None:
        """Append new compiler output and publish its last line."""
        out = bytes(self._process.readAllStandardOutput().data()).decode(
            "utf-8", errors="replace"
        )
        err = bytes(self._process.readAllStandardError().data()).decode(
            "utf-8", errors="replace"
        )
        self._stdout += out
        self._stderr += err
        text = (self._stderr or self._stdout).strip()
        if text:
            self.status_text.emit(text.splitlines()[-1][:200])

    def _report(self, *, cancelled: bool, code: int) -> None:
        """
        Emit :attr:`finished` once.

        Keyword Args:
            cancelled: Whether the user stopped the compile.
            code: Process exit code.

        """
        if self._reported:
            return
        self._reported = True
        self.finished.emit(cancelled, code, self._stdout, self._stderr)
