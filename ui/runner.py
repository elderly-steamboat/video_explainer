"""Run a pipeline subprocess, yielding combined stdout/stderr lines.

Usage:
    gen = run(argv)
    for line in gen:        # each output line as it arrives
        ...
    exit_code = gen.value   # available after StopIteration

Run from the repo root so `python -m src.cli` resolves.
"""
import subprocess
from pathlib import Path


def run(argv: list[str], cwd: Path = Path(".")):
    """Generator: yields output lines; return value is the exit code."""
    proc = subprocess.Popen(
        argv,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        encoding="utf-8",
        errors="replace",
    )
    assert proc.stdout is not None
    for line in proc.stdout:
        yield line.rstrip("\n")
    proc.wait()
    return proc.returncode
