"""T5.2 — `exclude_from_capture` (FR14, FR14a).

`ctypes.windll` only exists on Windows, so the real call cannot run in this container
(see `docs/implementation/06-progress.md`). What is tested here — and is the entire
FR14a-relevant surface — is the contract every caller relies on: success and failure
both come back as a plain bool, and nothing about a failure escapes as an exception
that would let a caller skip deciding what the user sees.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from interview_prep_recall.platform import win_capture_exclusion as wce


def test_true_on_success(monkeypatch: pytest.MonkeyPatch) -> None:
    user32 = SimpleNamespace(SetWindowDisplayAffinity=lambda hwnd, affinity: 1)
    monkeypatch.setattr(wce.ctypes, "windll", SimpleNamespace(user32=user32), raising=False)

    assert wce.exclude_from_capture(12345) is True


def test_false_on_api_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """`SetWindowDisplayAffinity` returning 0 is Win32 for "failed", not an exception."""
    user32 = SimpleNamespace(SetWindowDisplayAffinity=lambda hwnd, affinity: 0)
    monkeypatch.setattr(wce.ctypes, "windll", SimpleNamespace(user32=user32), raising=False)

    assert wce.exclude_from_capture(12345) is False


def test_false_when_call_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """Any OS-level failure (missing API, stale handle) is a warning, not a crash."""

    def _raise(hwnd: int, affinity: int) -> int:
        raise OSError("no such window")

    user32 = SimpleNamespace(SetWindowDisplayAffinity=_raise)
    monkeypatch.setattr(wce.ctypes, "windll", SimpleNamespace(user32=user32), raising=False)

    assert wce.exclude_from_capture(12345) is False


def test_false_when_windll_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    """The non-Windows shape: `ctypes` has no `windll` attribute at all."""
    monkeypatch.delattr(wce.ctypes, "windll", raising=False)

    assert wce.exclude_from_capture(12345) is False
