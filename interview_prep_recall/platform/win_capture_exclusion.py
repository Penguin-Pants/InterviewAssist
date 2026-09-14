"""SetWindowDisplayAffinity via ctypes (FR14, FR14a).

`WDA_EXCLUDEFROMCAPTURE` hides a window from every capture path a screen-share tool
can use — full-screen, single-window, and process-level capture APIs alike — which is
why one call at window-creation time satisfies FR14's six Zoom/Teams/Meet combinations
together rather than one at a time.

FR14a is why `exclude_from_capture` returns a bool instead of raising: a failed
exclusion is a WARN, not a crash, and the caller — not this module — decides what the
user sees. What the caller may never do is discard the return value; treating a
failed call as success is exactly the silent assumption FR14a forbids.
"""

from __future__ import annotations

import ctypes

WDA_EXCLUDEFROMCAPTURE = 0x00000011
"""windows.h. `WDA_NONE` (0) and the older `WDA_MONITOR` (1) do not satisfy FR14:
`WDA_MONITOR` blacks the window out in a *capture* but still lets some virtual-camera
and remote-desktop paths see it, where `WDA_EXCLUDEFROMCAPTURE` (Windows 10 2004+)
omits it from the source entirely."""


def exclude_from_capture(hwnd: int) -> bool:
    """Best-effort. Returns whether `hwnd` is now excluded from screen capture.

    Never raises: an unsupported OS build, a stale handle, or any other failure comes
    back as `False` for the caller to surface via FR14a's warning, not as an exception
    that would take the rest of the window down with it.
    """
    try:
        user32 = ctypes.windll.user32  # type: ignore[attr-defined]
        return bool(user32.SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE))
    except (AttributeError, OSError):
        return False
