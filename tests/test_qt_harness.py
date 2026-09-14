"""The Qt harness's own guarantee: a test's widgets die with the test (D-69).

Five destroy-order defects were fixed in `conftest.py` before this file existed, and
every one of them was found by a Windows CI crash rather than by a test — because the
harness had no assertion about its own behaviour, only a docstring. This is that
assertion.

The property under test is not "no leaks". It is **lifetime ownership**: no Qt widget
built by a test is left for Python's cyclic collector to destroy at an allocation inside
some later test's Qt call.
"""

from __future__ import annotations

import gc
import sys

import pytest

pytest.importorskip("PySide6", reason="Qt UI tests require the [ui] extra")

from conftest import release_qt_widgets  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402
from shiboken6 import isValid  # noqa: E402

from interview_prep_recall.diagnostics.ring import DiagnosticRing  # noqa: E402
from interview_prep_recall.ui.diagnostics_view import DiagnosticsView  # noqa: E402


def _build_and_drop() -> None:
    """Exactly what a UI test does: an unparented widget held only by a local."""
    DiagnosticsView(DiagnosticRing())


def test_an_unparented_widget_outlives_the_frame_that_built_it(qapp: QApplication) -> None:
    """The precondition, stated so the fix cannot be mistaken for belt-and-braces.

    `DiagnosticsView` stores a bound method of its own on itself and connects another to
    a button, so dropping the last name for it frees nothing — it is cyclic garbage, and
    *Python* picks the moment it is destroyed. Collection is disabled here only to make
    that visible; in a real run the moment is unpredictable, which is the whole defect.
    """
    gc.disable()
    try:
        _build_and_drop()
        assert len(qapp.topLevelWidgets()) == 1, "the widget was freed with its last name"

        release_qt_widgets()

        assert qapp.topLevelWidgets() == []
    finally:
        gc.enable()


def test_the_harness_destroys_widgets_rather_than_leaving_them_to_the_collector(
    qapp: QApplication,
) -> None:
    """The C++ object is gone by the time the sweep returns, not merely unreferenced.

    A wrapper that is still `isValid` after the sweep means Qt still owns a live widget,
    and a live widget is one a later collection can destroy from inside a Qt constructor.
    """
    view = DiagnosticsView(DiagnosticRing())

    release_qt_widgets()

    assert not isValid(view)


def test_a_dialog_parented_to_a_window_is_left_to_its_parent(qapp: QApplication) -> None:
    """Both are top-level widgets; only the root may be deleted.

    Queuing a deletion for the child too is a double free — an access violation inside
    `processEvents` on Windows, and silently survivable on Linux, which is how it reached
    CI the first time (PR #27).
    """
    from PySide6.QtWidgets import QDialog, QWidget

    root = QWidget()
    child = QDialog(root)
    assert child in qapp.topLevelWidgets()

    release_qt_widgets()

    assert not isValid(root)
    assert not isValid(child)
    assert qapp.topLevelWidgets() == []


def test_the_sweep_stands_no_application_up_for_the_non_qt_tests(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The autouse fixture runs after every test in the suite, Qt or not.

    Most of the suite never imports Qt, and a sweep that reached for `QApplication`
    would give those tests a widget toolkit they do not use.
    """
    monkeypatch.delitem(sys.modules, "PySide6.QtWidgets")

    release_qt_widgets()

    assert "PySide6.QtWidgets" not in sys.modules
