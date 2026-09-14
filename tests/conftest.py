"""Shared fixtures, including the T0.4 write-allowlist guard.

The guard is autouse and active from M0, deliberately. The universal definition of
done says every task must show no writes outside the design §4 allowlist; scoping
that to "once the M6 harness lands" would have left it unverifiable for the first six
milestones, which is most of the project. T6.4's Process Monitor trace is the
full-system check against a packaged build; this is the per-test one.
"""

from __future__ import annotations

import builtins
import os
import sys
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest

from interview_prep_recall.diagnostics.ring import DiagnosticRing
from interview_prep_recall.platform.credentials import (
    CredentialStore,
    InMemoryCredentialBackend,
)

_WRITE_MODES = frozenset("wxa+")


def _is_write_mode(mode: str) -> bool:
    return any(ch in _WRITE_MODES for ch in mode)


def _allowed_roots() -> list[Path]:
    """Paths a test may legitimately write to.

    Everything the application itself writes lives under a tmp-path-backed app data
    directory in tests, so this list is about tooling, not product behaviour.
    """
    roots = [Path(tempfile.gettempdir()).resolve()]
    repo = Path(__file__).resolve().parent.parent
    # pytest/coverage bookkeeping inside the repo.
    roots += [repo / ".pytest_cache", repo / "htmlcov", repo / ".coverage"]
    for env in ("PYTEST_DEBUG_TEMPROOT", "TMPDIR"):
        if os.environ.get(env):
            roots.append(Path(os.environ[env]).resolve())
    return roots


class WriteOutsideAllowlist(AssertionError):
    """A test wrote somewhere design §4 does not permit."""


@pytest.fixture(autouse=True)
def write_allowlist(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    roots = _allowed_roots()
    real_open = builtins.open
    real_os_open = os.open

    def _check(path: object) -> None:
        try:
            resolved = Path(os.fspath(path)).resolve()  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return  # file descriptors and exotic objects are not paths
        for root in roots:
            try:
                resolved.relative_to(root)
                return
            except ValueError:
                continue
        raise WriteOutsideAllowlist(
            f"write to {resolved} is outside the design §4 allowlist.\n"
            "Application writes belong under the app data directory; tests should use tmp_path."
        )

    def guarded_open(file, mode="r", *args, **kwargs):  # type: ignore[no-untyped-def]
        if isinstance(mode, str) and _is_write_mode(mode):
            _check(file)
        return real_open(file, mode, *args, **kwargs)

    def guarded_os_open(path, flags, *args, **kwargs):  # type: ignore[no-untyped-def]
        if flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_APPEND):
            _check(path)
        return real_os_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", guarded_open)
    monkeypatch.setattr(os, "open", guarded_os_open)
    yield


@pytest.fixture
def ring() -> DiagnosticRing:
    return DiagnosticRing()


@pytest.fixture
def credentials(ring: DiagnosticRing) -> CredentialStore:
    return CredentialStore(backend=InMemoryCredentialBackend(), ring=ring)


@pytest.fixture
def app_data(tmp_path: Path) -> Path:
    """A throwaway %APPDATA%\\InterviewPrepRecall equivalent."""
    root = tmp_path / "InterviewPrepRecall"
    root.mkdir()
    return root


@pytest.fixture(scope="session", autouse=True)
def qt_settings_sandbox(tmp_path_factory: pytest.TempPathFactory) -> Iterator[None]:
    """Point `QSettings` at a throwaway directory for the whole test session.

    **Session-scoped, and that is not an optimisation.** `setDefaultFormat` and `setPath`
    are process-global Qt state. Setting and restoring them around every test churns the
    configuration underneath `QSettings` objects created inside a test and destroyed after
    it, which segfaults the interpreter once enough have accumulated — found while adding
    the overlay geometry store, and it cost more to diagnose than the fixture saves.

    The T0.4 guard above cannot see these writes: `QSettings` persists through Qt's C++
    layer, not through Python's `open`, so a test that constructs one and stores a value
    writes to the user's real registry or `~/.config` and the allowlist never fires. That
    is the one hole in an otherwise per-test guarantee, and T5.4 made it reachable —
    `MainWindow` now owns the overlay's geometry store (FR26).

    `IniFormat` is forced because `setPath` has no effect on the native backend, which on
    the Windows target is the registry. Redirecting only the format we do not ship on
    would have looked like protection and provided none.
    """
    try:
        from PySide6.QtCore import QSettings
    except ImportError:  # the [ui] extra is optional; nothing to sandbox without it
        yield
        return

    previous_format = QSettings.defaultFormat()
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(
        QSettings.Format.IniFormat,
        QSettings.Scope.UserScope,
        str(tmp_path_factory.mktemp("qsettings")),
    )
    yield
    QSettings.setDefaultFormat(previous_format)


def release_qt_widgets() -> None:
    """Dispatch this test's queued events, then destroy the widgets it built.

    Both halves, in that order, and neither is optional.

    **Draining first** keeps each test's events and its objects inside one lifetime.
    Anything still queued for a widget the test is about to drop would otherwise be
    dispatched by whichever test next pumps the loop — the D-66 property.

    **Destroying second** is the part D-66 missed. A widget is not freed when the test's
    last name for it goes: `DiagnosticsView` stores `self._ask_for_path` on itself and
    connects `self.refresh` to a button, so it is *cyclic* garbage, and only Python's
    cyclic collector can free it. Every top-level widget in this suite has a cycle of
    that shape — `QFrame`, `NotesEditor`, `ImportDialog`, `OverlayPanel`, `MainWindow`,
    `SettingsDialog`, `DiagnosticsView`, `ReportView`, `FirstRunConsentDialog` — so
    parentless widgets pile up across modules and a later collection destroys a batch of
    them at whatever allocation happens to trip the threshold. That allocation is
    routinely inside a Qt constructor, because a `PySide6` wrapper is a container object:
    Qt is then tearing down widgets **re-entrantly, part-way through building another
    one**. On Windows that is an access violation; on Linux it is survivable, which is
    why only CI sees it.

    Deleting here puts the destruction back under the harness's control, while the
    `QApplication` is alive and while Qt is not inside anything.

    **Only parentless roots are deleted, and never a widget Qt has already destroyed.**
    A `QDialog` parented to a window is *both* a top-level widget and that window's
    child, so queuing a deletion for everything `topLevelWidgets()` returns would queue
    one for objects their parent is about to delete on the same pass — a double free.
    Deleting the roots and letting Qt cascade is the ordering it documents; `isValid`
    guards the wrappers whose C++ object went with an earlier root.

    `hide()` rather than `close()` because a close may legitimately be **refused** —
    `NotesEditor` does exactly that when a save was rejected and closing would lose the
    edits (T3.7) — and destroying a *visible* top-level widget is its own hazard.

    `sendPostedEvents` is needed because `processEvents` alone does not run deferred
    deletions, and running them here is the whole point.

    A no-op when Qt is not loaded: the guard keeps this off the non-Qt tests entirely
    rather than standing a `QApplication` up for them.
    """
    qt = sys.modules.get("PySide6.QtWidgets")
    if qt is None:
        return
    app = qt.QApplication.instance()
    if app is None:
        return

    from PySide6.QtCore import QCoreApplication, QEvent
    from shiboken6 import isValid

    app.processEvents()
    for widget in list(app.topLevelWidgets()):
        if not isValid(widget) or widget.parent() is not None:
            continue
        widget.hide()
        widget.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    app.processEvents()


@pytest.fixture(scope="session")
def qapp() -> Iterator[object]:
    """The one `QApplication` for the test session.

    Six test modules each defined their own copy, which left every widget ever built
    alive until interpreter shutdown — where Qt destroys them in whatever order it likes,
    after the `QApplication` may already be gone (D-54).

    The teardown that fixed it used to live here, and no longer does. `release_qt_widgets`
    runs after **every** test instead, so by the time this fixture would have swept there
    is nothing left to sweep. Per-test is strictly stronger: a session-scoped sweep leaves
    the widgets of tests 1..n-1 alive and collectable at any allocation in between, which
    is D-69.
    """
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture(autouse=True)
def qt_lifetime() -> Iterator[None]:
    """Give every test's Qt widgets a lifetime that ends with the test.

    The sixth destroy-order defect in this harness (D-53, D-54, PR #27's two, and D-66),
    and the third to surface as a crash with every test reported passing. See
    `release_qt_widgets` for what it does and why both of its halves are needed.
    """
    yield
    release_qt_widgets()
