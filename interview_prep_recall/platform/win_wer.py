"""Disable Windows Error Reporting dumps for this process (FR16).

FR16's rewritten claim concedes the OS may write a crash dump of process memory on an
unhandled exception, since that is outside application control — but WER does not have
to be the mechanism that does it. Microsoft's own documentation for `SEM_NOGPFAULTERRORBOX`
is explicit that this is stronger than hiding a dialog: "the system does not invoke
Windows Error Reporting" at all for the process. That is what FR16 needs — no WER means
no WER-authored dump, which means no path from a session's transcript in this process's
memory into a dump file neither this app nor the user chose to write.

`WerSetFlags(WER_FAULT_REPORTING_FLAG_NOUI)` — the alternative the same doc page names —
only silences WER's dialog while leaving it free to write a report in the background,
which is precisely the guarantee FR16 needs and that flag does not give.
"""

from __future__ import annotations

import ctypes

SEM_FAILCRITICALERRORS = 0x0001
"""Errors go to the calling process instead of a system dialog. Microsoft's documented
best practice is every application sets this at startup regardless of FR16, so it is
folded into the one call this module makes rather than left unset beside it."""

SEM_NOGPFAULTERRORBOX = 0x0002
"""The flag FR16 depends on: WER is not invoked for this process at all."""


def disable_wer_dumps() -> None:
    """Best-effort, idempotent, and silent off Windows.

    `SetErrorMode` has no documented failure return — unlike `SetWindowDisplayAffinity`
    (T5.2), there is no success/failure outcome for a caller to act on, so this returns
    nothing. What it must never do is raise: called once, early, before startup can
    reach anything that might crash, an exception here would take the whole process
    down over the one API call that exists to keep a crash from leaking data.
    """
    try:
        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        kernel32.SetErrorMode(SEM_FAILCRITICALERRORS | SEM_NOGPFAULTERRORBOX)
    except (AttributeError, OSError):
        pass
