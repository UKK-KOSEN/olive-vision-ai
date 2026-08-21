"""Shared CLI helpers: ANSI colour output and animated processing effects."""
from __future__ import annotations

import itertools
import os
import sys
import threading
import time


class _Ansi:
    """Minimal ANSI escape helpers that degrade gracefully on dumb terminals."""
    ENABLED = sys.stdout.isatty() and os.getenv("NO_COLOR") is None

    @staticmethod
    def wrap(code: str, text: str) -> str:
        if not _Ansi.ENABLED:
            return text
        return f"\x1b[{code}m{text}\x1b[0m"


# --- basic styles -----------------------------------------------------------
def bold(text) -> str:
    return _Ansi.wrap("1", text)


def dim(text) -> str:
    return _Ansi.wrap("2", text)


def cyan(text) -> str:
    return _Ansi.wrap("36", text)


def green(text) -> str:
    return _Ansi.wrap("32", text)


def yellow(text) -> str:
    return _Ansi.wrap("33", text)


def red(text) -> str:
    return _Ansi.wrap("31", text)


def magenta(text) -> str:
    return _Ansi.wrap("35", text)


def blue(text) -> str:
    return _Ansi.wrap("34", text)


def accent_ok(text) -> str:
    return green(bold(text))


def accent_warn(text) -> str:
    return yellow(bold(text))


def accent_err(text) -> str:
    return red(bold(text))


# --- box drawing ------------------------------------------------------------
def rule(char: str = "─", width: int = 56) -> str:
    return dim(char * width)


def panel(title: str, body: str) -> str:
    line = rule()
    return f"{line}\n{cyan(bold(title))}\n{body}\n{line}"


# --- spinner ----------------------------------------------------------------
class Spinner:
    """Print an animated spinner on a fresh line while work runs in the caller.

    It spins from a background thread; stopping clears the line. Safe for
    terminals and piped output (falls back to static text when not a TTY).
    """

    FRAMES = ("⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏")

    def __init__(self, message: str = "Processing", stream=sys.stderr, min_visible: float = 0.9):
        self._message = message
        self._stream = stream
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._frames = itertools.cycle(self.FRAMES if _Ansi.ENABLED else ("|", "/", "-", "\\"))

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *_exc):
        self.stop()
        return False

    def start(self):
        self._stop.clear()

        def _run():
            while not self._stop.is_set():
                self._stream.write(f"\r{cyan(next(self._frames))} {bold(self._message)} ")
                self._stream.flush()
                self._stop.wait(0.1)

        self._thread = threading.Thread(target=_run, daemon=True)
        self._thread.start()

    def stop(self, final: str | None = None):
        if self._thread is not None:
            self._stop.set()
            self._thread.join(timeout=0.5)
            self._thread = None
        if final is not None:
            self._stream.write(f"\r{green('✔')} {bold(final)}\n")
        else:
            self._stream.write("\r" + " " * (len(self._message) + 8) + "\r")
        self._stream.flush()


class ProgressBar:
    """A thin, deterministic progress bar updated from the worker thread.

    Renders only the newest state on one line; no flicker when flushed.
    """

    def __init__(self, total: int, width: int = 24, stream=sys.stderr,
                 label: str = "Frames"):
        self._total = max(1, int(total))
        self._width = width
        self._stream = stream
        self._label = label
        self._last = -1

    def update(self, done: int, note: str = ""):
        done = min(int(done), self._total)
        frac = done / self._total
        filled = int(frac * self._width)
        bar = "█" * filled + "░" * (self._width - filled)
        pct = f"{frac * 100:5.1f}%"
        line = (f"\r{dim(self._label):>6} {green(bar)} {pct} "
                f"{bold(str(done) + '/' + str(self._total))}")
        if note:
            line += f"  {dim(note)}"
        self._stream.write(line + " " * max(0, self._last - len(line)))
        self._last = len(line)
        self._stream.flush()

    def finish(self, note: str = ""):
        bar = "█" * self._width
        line = f"\r{dim(self._label):>6} {accent_ok(bar)} 100.0% {bold(str(self._total) + '/' + str(self._total))}"
        if note:
            line += f"  {dim(note)}"
        self._stream.write(line + "\n")
        self._stream.flush()


# --- decorative animations ---------------------------------------------------
def countup(get_value, format_fn, stream=sys.stderr, steps: int = 18,
            delay: float = 0.02, color=accent_ok, prefix: str = ""):
    """Animate a number climbing to its target (best effort, TTY only)."""
    target = get_value()
    if not _Ansi.ENABLED:
        stream.write(prefix + format_fn(target) + "\n")
        stream.flush()
        return
    for step in range(steps + 1):
        frac = step / steps
        eased = 1 - (1 - frac) ** 2
        value = target * eased
        stream.write(f"\r{prefix}{color(format_fn(value))} ")
        stream.flush()
        time.sleep(delay)
    stream.write("\n")
    stream.flush()


def countup_line(items, stream=sys.stderr, steps: int = 10, delay: float = 0.012):
    """Animate several metrics together on a single line (subdued).

    items: list of (get_value, format_fn, color). Rendered side by side,
    all climbing together, then left on one clean line.
    """
    targets = [it[0]() for it in items]
    if not _Ansi.ENABLED:
        stream.write("  " + "   ".join(it[1](targets[i]) for i, it in enumerate(items)) + "\n")
        stream.flush()
        return
    for step in range(steps + 1):
        frac = step / steps
        eased = 1 - (1 - frac) ** 2
        parts = []
        for i, (get_v, fmt, color) in enumerate(items):
            parts.append(color(fmt(targets[i] * eased)))
        stream.write("\r  " + "   ".join(parts) + " ")
        stream.flush()
        time.sleep(delay)
    stream.write("\n")
    stream.flush()