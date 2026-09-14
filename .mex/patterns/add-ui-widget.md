---
name: add-ui-widget
description: Add a new UI widget, view, or overlay component to the main window
triggers:
  - "add widget"
  - "new UI feature"
  - "overlay component"
  - "add view"
edges:
  - target: context/conventions.md
    condition: when understanding class naming and structure patterns
  - target: context/architecture.md
    condition: when understanding how widgets integrate with MainWindow
  - target: context/stack.md
    condition: when understanding PySide6-specific patterns and constraints
  - target: patterns/track-session-progress.md
    condition: when a widget needs to update or display session state
last_updated: 2026-09-14
mex:
  id: mx_01M2GHK748V8AWHDRYGSWJC9XF
  type: pattern
  status: promoted
  revision: 4
  title: add-ui-widget
  grounds_to:
    - node: class:6e32db9af44732d2d30b14b07bc3c2b2
      fingerprint: mh:64:7b226d696e68617368223a5b383939303735392c393631393038342c33303636333333382c333534353038352c31303332343130332c31313236333331382c363633363132322c34383430333936312c31353935393932372c31313130393635372c31353537343536322c31313236353438362c31373431353239352c31383537323237312c343831303535372c393032393333302c3131333135353632322c373535353739342c34353839353537392c323134373331302c33383137363739372c32363739393939392c313830393030342c393832393038372c373035303231302c34353634323633352c31353436373239372c31303537373234392c35353939353230392c313634363838322c323633383732302c32303731383530392c343431393134332c31333139323230352c35333435323433352c32303535353530322c31393939393132392c363737333533322c32393433363739322c353332323233322c33313938363937392c383131373337302c3832363536312c36363539393130392c353630353534392c343936303734382c35383039323536372c3130323633323734312c373832383038302c363536313337362c33303336353434372c34353338343234322c32333433393030392c383036313235342c31363730373933312c353833373833352c33393934363934322c313830313638392c383538363932332c31303831393534332c393132323439302c32343834353935362c333235313338392c31313732363932355d2c226e65696768626f7273223a5b5d2c22746f6b656e436f756e74223a313437327d
      bodyHash: 1588e5a1f187ed721db12df14478f6ff121ac109190edf1ee1093231b6dc1e9d
  relations:
    - type: related_to
      target: mx_01M2GHK6R6GR8Z910CVXWDKJFK
      note: when understanding class naming and structure patterns
    - type: related_to
      target: mx_01M2GHK6K4BGKA2Q2EW93N325R
      note: when understanding how widgets integrate with MainWindow
    - type: related_to
      target: mx_01M2GHK76CSP63RZMP9N9ZWKXN
      note: when a widget needs to update or display session state
---

# Add UI Widget

## Context

All UI components are PySide6-based and live in `interview_prep_recall/ui/`. The [`MainWindow`](mex://class:6e32db9af44732d2d30b14b07bc3c2b2) is the composition root that owns all widgets and connects them to the `Application` instance. New widgets are instantiated in the main window and wired to session/settings callbacks.

Patterns:
- Each major widget/view is its own file (e.g., `editor.py`, `checklist.py`, `overlay.py`)
- Widgets receive `Application` and relevant data/callbacks via constructor
- Qt signals propagate state changes back to Application
- No widget owns multiple major concerns; split if growing beyond ~300 lines

## Steps

1. Create the widget class in a new file under `interview_prep_recall/ui/`, e.g. `interview_prep_recall/ui/my_widget.py`
   - Inherit from appropriate Qt base class (`QWidget`, `QDialog`, etc.)
   - Define `__init__` with `Application` parameter and any callbacks
   - Declare Qt signals for events that affect session state (use `Signal` from PySide6.QtCore)
   - Do not store mutable application state; only read-only access to Application properties

2. Add widget instantiation to `MainWindow.__init__()` in `interview_prep_recall/ui/main_window.py`
   - Instantiate with `Application` instance and wire signals to callbacks
   - Add to layout if visible; otherwise keep reference for programmatic show/hide

3. Wire state changes:
   - Connect widget signals → Application methods if the change affects session/findings
   - Connect Application state changes → widget slots if the widget displays that state
   - Use Qt's signal/slot mechanism; avoid direct imperative updates

4. Add tests in `tests/test_ui_<my_widget>.py`
   - Instantiate widget with a test Application and tmp_path for notes store
   - Test signal emissions and slot reactions
   - Do not test Qt rendering; only state changes and signal flow

## Gotchas

- **Don't put business logic in widgets** — keep widgets as view-only; use Application methods for changes
- **Don't store mutable state in widgets** — read from Application, emit signals for changes
- **Qt signal connections are implicit** — verify signal names match exactly (typos create silent failures)
- **MainWindow owns lifecycle** — don't keep extra references to widgets in tests that outlive the window
- **Test QApplication availability** — use `qapp` fixture from conftest.py; tests mark with `@pytest.mark.skip` if PySide6 not installed

## Verify

- [ ] New widget class is in `interview_prep_recall/ui/<name>.py` with PascalCase name
- [ ] `__init__` receives `Application` as parameter, no global imports of Application
- [ ] All state-changing operations emit signals or call Application methods
- [ ] Widget has no `@property` methods that write to Application state directly
- [ ] MainWindow instantiates the widget and wires signals
- [ ] Tests pass: `pytest tests/test_ui_<name>.py`
- [ ] No print/logging in widget code; use exceptions with context if something fails

## Debug

If widget does not update when state changes: check that Application state change actually invokes the widget's slot. Trace the signal chain: Application → signal → widget slot.

If widget signals don't propagate back to Application: verify signal is declared with `Signal()`, emitted with `self.signal.emit(args)`, and connected in MainWindow with `.connect()`.

If tests fail due to missing QApplication: ensure test file imports `qapp` fixture or runs under `QT_QPA_PLATFORM=offscreen`.

## Update Scaffold

- [ ] Update `.mex/ROUTER.md` "Current Project State" if a new UI subsystem was added
- [ ] If this widget represents a new category of UI patterns, create a domain file: `.mex/context/ui-patterns.md`
- [ ] Update this pattern if gotchas discovered
