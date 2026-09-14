"""Process entry point (T9.6). `python -m interview_prep_recall`.

Everything here is bootstrap: pick the app data directory, create the `QApplication`,
hand `startup.start` the real presenter, and show what it returns. The sequence itself
lives in `startup.py` and the composition in `app.py`, both Qt-free — so the only part
that needs a window is the part that opens one.

**Why `__main__.py` and not `app.py`**, which design §1 labels "entry point, DI wiring":
`app.py` is deliberately Qt-free, and T9.0's docstring makes that a property rather than
an accident — the wiring is testable on a machine that cannot run the UI precisely
because no Qt import can reach it. Putting `QApplication` there would trade a tested
guarantee for a filename.

**Real dependencies are constructed here (T9.6a) and the missing ones are not hidden.**
There is still no audio capture (M1) and no overlay (M5), so no session can start.
Preflight says so, in FR38's own vocabulary, and the window shows the blockers.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from interview_prep_recall.app import Application
from interview_prep_recall.notes.embedder import SentenceTransformerEmbedder
from interview_prep_recall.platform.credentials import CredentialStore
from interview_prep_recall.report.generator import MessagesClient
from interview_prep_recall.report.store import (
    Cipher,
    CipherUnavailableError,
    UnavailableCipher,
    default_cipher,
)
from interview_prep_recall.startup import (
    ApplicationFactory,
    StartupOutcome,
    run_preflight,
    start,
)

APP_DIR_NAME = "InterviewPrepRecall"

EXIT_OK = 0
EXIT_CONSENT_DECLINED = 1
EXIT_STARTUP_FAILED = 2

STARTUP_FAILED_NOTICE = (
    "Interview Prep Recall could not start.\n\nSomething it needs was not available. "
    "The details follow.\n\n"
)
"""Shown instead of a traceback. An entry point's job is to start or to say why it
cannot, and a stack trace is neither — it is what the user sees when nobody decided what
they should see."""


def app_data_root() -> Path:
    """`%APPDATA%\\InterviewPrepRecall` on Windows, an XDG-ish equivalent elsewhere.

    The fallback is not aspirational cross-platform support — the product is Windows-only
    (D-U4). It exists so the entry point can be *run* in the Linux dev container, which is
    the only way to find out that it works before the target machine is available.
    """
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / APP_DIR_NAME
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg) if xdg else Path.home() / ".config"
    return base / APP_DIR_NAME


def _build_application(root: Path) -> Application:
    """Construct the composition root with its real dependencies (T9.6a).

    Four dependencies, and each one's answer is a decision somebody else made:

    * **Which note set** — T3.8. `editor.load_active_set` reads the id FR43 puts in
      `QSettings`: the persisted set, else the only one, else a new empty one.
    * **The model client** — D-U12. A key is optional, so its absence is a configuration
      and not a failure, and the whole degraded path already existed waiting for someone
      to select it.
    * **The embedder** — D-U13, and the part that was never merely a download: nothing
      had ever implemented the Protocol.
    * **The cipher** — DPAPI where there is one, and a refusal that fires at the write
      rather than here where there is not.

    **Nothing missing is hidden and nothing missing is fatal.** Each dependency that
    cannot be satisfied on this machine degrades to a state preflight can name, because
    the alternative — refusing to start — takes away the window the user fixes it from.
    There is still no audio capture (M1) and no overlay (M5), so no session can start;
    preflight says so in FR38's own vocabulary and the window shows the blockers.
    """
    from interview_prep_recall.ui.editor import load_active_set
    from interview_prep_recall.ui.overlay import default_settings

    key = CredentialStore().get("anthropic")
    client, absent = _model_client(key)

    try:
        cipher: Cipher = default_cipher()
    except CipherUnavailableError as exc:
        cipher = UnavailableCipher(str(exc))

    application = Application(
        root=root,
        embedder=SentenceTransformerEmbedder(),
        client=client,
        cipher=cipher,
        # No ring to hand it: the set has to be loaded before the `Application` that owns
        # the ring exists, so a backup restored during this call is not recorded. Left as
        # a follow-up rather than papered over with a second ring nothing exports.
        context_set=load_active_set(root, default_settings()),
    )
    if key is not None:
        # FR19's guard, armed on the ring that is actually exported. `CredentialStore`
        # does this itself when given a ring, and it cannot be given this one — the key
        # is needed to build the client, and the client to build the application that
        # owns the ring. So it is armed the moment that ordering allows.
        application.ring.register_secret(key)
    if absent is not None:
        application.ring.record("stage2_absent", reason=absent)
    return application


def _model_client(key: str | None) -> tuple[MessagesClient | None, str | None]:
    """The Anthropic client, or why there is not one. Never raises.

    Both reasons are ordinary states rather than errors — D-U12 makes a keyless run
    supported, and the `[cloud]` extra is optional — so both return rather than raise,
    and both are recorded so a user who expected stage-2 matching can see which one
    applies to them.
    """
    if key is None:
        return None, "no_key"
    try:
        from anthropic import Anthropic
    except ImportError:
        return None, "sdk_missing"
    messages: MessagesClient = Anthropic(api_key=key).messages
    return messages, None


def main(
    argv: list[str] | None = None,
    *,
    build_application: ApplicationFactory = _build_application,
) -> int:
    """Start the application. Returns a process exit code.

    `build_application` is a parameter so the bootstrap — argument handling, the consent
    gate, notice delivery, the window — is testable with a double. Its default is the
    real construction, which is not finished; see `_build_application`.
    """
    argv = sys.argv[1:] if argv is None else argv
    root = Path(argv[0]) if argv else app_data_root()

    from PySide6.QtWidgets import QApplication, QMessageBox

    from interview_prep_recall.ui.consent_dialog import present_disclosure
    from interview_prep_recall.ui.main_window import WINDOW_TITLE, MainWindow
    from interview_prep_recall.ui.overlay import default_settings

    qt_app = QApplication.instance() or QApplication(sys.argv)

    try:
        result = start(root, present=present_disclosure, build_application=build_application)
    except Exception as exc:  # noqa: BLE001 — the alternative is a traceback on screen
        # Broad on purpose. Everything from here reaches a user with no console: a
        # missing dependency, an unwritable app-data directory, a half-built dependency
        # graph. Verified by running `python -m interview_prep_recall`, which printed a
        # `NotImplementedError` traceback before this existed.
        print(f"{STARTUP_FAILED_NOTICE}{exc}", file=sys.stderr)
        QMessageBox.critical(None, WINDOW_TITLE, f"{STARTUP_FAILED_NOTICE}{exc}")
        return EXIT_STARTUP_FAILED

    if result.outcome is StartupOutcome.CONSENT_DECLINED:
        # Nothing was constructed, so there is nothing to tear down. Exiting non-zero
        # because a refused disclosure is not a successful run.
        return EXIT_CONSENT_DECLINED

    for notice in result.notices:
        QMessageBox.warning(None, WINDOW_TITLE, notice)

    assert result.application is not None  # guaranteed by the outcome above
    application = result.application
    window = MainWindow(
        application,
        result.preflight,
        # One store for the process, built here rather than inside the widget: design §4
        # puts overlay chrome in the registry, and the composition root is what owns
        # process-wide resources (FR26).
        overlay_settings=default_settings(),
        refresh_preflight=lambda: run_preflight(application),
    )
    window.show()
    return int(qt_app.exec())


if __name__ == "__main__":  # pragma: no cover — exercised as a process, not imported
    sys.exit(main())
