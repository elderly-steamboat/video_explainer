import sys
from ui.runner import run


def test_run_yields_lines_and_returns_zero():
    argv = [sys.executable, "-c", "print('hello'); print('world')"]
    lines = []
    code = yield_collect(argv, lines)
    assert code == 0
    assert "hello" in lines
    assert "world" in lines


def test_run_nonzero_exit():
    argv = [sys.executable, "-c", "import sys; sys.stderr.write('boom\\n'); sys.exit(3)"]
    lines = []
    code = yield_collect(argv, lines)
    assert code == 3
    assert any("boom" in ln for ln in lines)


def yield_collect(argv, lines):
    """Drive the run() generator, collecting lines, returning the exit code."""
    gen = run(argv)
    try:
        while True:
            lines.append(next(gen))
    except StopIteration as stop:
        return stop.value
