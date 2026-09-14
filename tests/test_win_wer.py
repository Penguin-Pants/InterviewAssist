"""T6.4 — `disable_wer_dumps` (FR16).

`ctypes.windll` only exists on Windows, so what is unit-tested here is the contract:
the right flags reach `SetErrorMode`, and nothing about a missing or failing API
escapes as an exception — this runs before startup can reach anything that might
crash, and raising here would take the process down over the one call that exists to
stop a crash from leaking a transcript. The ProcMon trace confirming no dump is ever
actually written is the real-surface half FR16 still needs (see
`docs/implementation/06-progress.md`).
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from interview_prep_recall.platform import win_wer


def test_sets_the_no_gpfault_and_failcritical_flags(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[int] = []
    kernel32 = SimpleNamespace(SetErrorMode=lambda mode: calls.append(mode))
    monkeypatch.setattr(win_wer.ctypes, "windll", SimpleNamespace(kernel32=kernel32), raising=False)

    win_wer.disable_wer_dumps()

    assert calls == [win_wer.SEM_FAILCRITICALERRORS | win_wer.SEM_NOGPFAULTERRORBOX]


def test_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[int] = []
    kernel32 = SimpleNamespace(SetErrorMode=lambda mode: calls.append(mode))
    monkeypatch.setattr(win_wer.ctypes, "windll", SimpleNamespace(kernel32=kernel32), raising=False)

    win_wer.disable_wer_dumps()
    win_wer.disable_wer_dumps()

    assert len(calls) == 2


def test_silent_when_the_call_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise(mode: int) -> None:
        raise OSError("no such API")

    kernel32 = SimpleNamespace(SetErrorMode=_raise)
    monkeypatch.setattr(win_wer.ctypes, "windll", SimpleNamespace(kernel32=kernel32), raising=False)

    win_wer.disable_wer_dumps()  # must not raise


def test_silent_when_windll_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    """The non-Windows shape: `ctypes` has no `windll` attribute at all."""
    monkeypatch.delattr(win_wer.ctypes, "windll", raising=False)

    win_wer.disable_wer_dumps()  # must not raise
