---
name: router
description: Session bootstrap and navigation hub. Read at the start of every session before any task. Contains project state, routing table, and behavioural contract.
edges:
  - target: context/architecture.md
    condition: when working on system design, integrations, or understanding how components connect (read this first)
  - target: context/stack.md
    condition: when working with specific technologies, libraries, or making tech decisions
  - target: context/conventions.md
    condition: when writing new code, reviewing code, or unsure about project patterns
  - target: context/decisions.md
    condition: when making architectural choices or understanding why something is built a certain way
  - target: context/setup.md
    condition: when setting up the dev environment or running the project for the first time
  - target: patterns/INDEX.md
    condition: when starting a task — check the pattern index for a matching pattern file
  - target: AGENTS.md
    condition: for project identity, non-negotiables, and commands (read at session start)
last_updated: 2026-09-09
---

# Session Bootstrap

If you haven't already read `AGENTS.md`, read it now — it contains the project identity, non-negotiables, and commands.

Then read this file fully before doing anything else in this session.

## Current Project State

**Re-verified 2026-09-09 after a ~3.5 week pause. `docs/implementation/06-progress.md` is the
authoritative build log — read it before trusting this summary. It tracks its own past staleness
("wrong seven times") with a standing rule: test the reason a task looks blocked, not the label.**

**Working, built, and wired to each other:**
- PySide6 overlay UI (checklist, indicators, dialogs), embedding-prefilter + Anthropic stage-2
  note matching, notes store/importer/editor with backup+restore, session state machine, progress
  tracker, post-interview report generation/view/export-to-Markdown, settings, first-run consent,
  diagnostics ring buffer. All wired together through `app.py`'s composition root and
  `ui/main_window.py`.
- Local Whisper STT backend and both cloud STT backends (Deepgram, ElevenLabs) plus an
  auto-fallback wrapper — implemented and unit-tested in isolation, but see the top blocker below.
- Test suite: 1231/1231 passing on Linux (offscreen Qt), mypy `--strict` clean on
  `stt/interface.py`, ruff clean.

**Top blocker — the app cannot run end-to-end yet:**
- `interview_prep_recall/__main__.py`'s `_build_application()` unconditionally
  `raise NotImplementedError` (task T9.6a). No audio capture and no STT backend, local or cloud,
  is ever constructed or wired into `Application`. Tracked in `06-progress.md`'s Blocked register
  as waiting on three things: a product decision on the no-API-key policy, the embedding model
  download (blocked by this dev container's network policy, not by platform), and the
  Windows-only DPAPI cipher.
- Consequence: embedding-based note matching **is** fully wired into the UI (this reverses what
  this file used to say) — it simply never receives an utterance to match, because nothing feeds
  it one yet.

**Not yet built:**
- Four modules are pure stubs with no logic: `watchdog.py`, `audio/echo.py` (FR57, audio-domain
  echo detection), `platform/win_capture_exclusion.py` (FR14/14a), `platform/win_wer.py` (FR16).
- Report export covers Markdown only; HTML/PDF export do not exist.
- A basic multi-session picker exists (`report/store.list_sessions()`, used by the report view),
  but there is no history/analytics view beyond it.

**Known issues:**
- **D-68** (found and fixed 2026-08-16): an idle WASAPI loopback endpoint delivers zero callbacks
  instead of frames of silence. Fixed with a keep-alive render stream. Unit tests for the fix
  (T1.5) are not written yet, and the 60-minute soak (T1.6, the AS-2 gate) has only run for 60
  seconds so far.
- **AS-1** (local STT latency gate, T2.4) and **AS-3/AS-7** (matching-accuracy gates, T4.7) have
  NOT been measured yet, despite older notes in `00-decisions-and-assumptions.md` reading as if
  they had — T4.7 additionally needs the user's hand-labelled transcripts plus an
  `ANTHROPIC_API_KEY`.
- **AS-8**: Deepgram/ElevenLabs wire protocols are implemented from documentation only, never
  verified against a live endpoint.
- **AS-9**: the local Whisper adapter has never loaded a real model — this dev container blocks
  `huggingface.co` — so it is untested against the real library.
- Environment split: this dev container is Linux; the product targets Windows 11. The full test
  suite (1231 tests) passes here via PySide6's offscreen Qt platform. Windows-only code
  (DPAPI, WASAPI, `SetWindowDisplayAffinity`, WER suppression) needs the Windows target machine,
  which became reachable for the first time on 2026-08-16 (see the M1 log entry).

## Routing Table

Load the relevant file based on the current task. Always load `context/architecture.md` first if not already in context this session.

| Task type | Load |
|-----------|------|
| Understanding how the system works | `context/architecture.md` |
| Working with a specific technology | `context/stack.md` |
| Writing or reviewing code | `context/conventions.md` |
| Making a design decision | `context/decisions.md` |
| Setting up or running the project | `context/setup.md` |
| Any specific task | Check `patterns/INDEX.md` for a matching pattern |

## Behavioural Contract

For every task, follow this loop:

1. **CONTEXT** — Load the relevant context file(s) from the routing table above. Check `patterns/INDEX.md` for a matching pattern. If one exists, follow it. Narrate what you load: "Loading architecture context..."
2. **BUILD** — Do the work. If a pattern exists, follow its Steps. If you are about to deviate from an established pattern, say so before writing any code — state the deviation and why.
3. **VERIFY** — Load `context/conventions.md` and run the Verify Checklist item by item. State each item and whether the output passes. Do not summarise — enumerate explicitly.
4. **DEBUG** — If verification fails or something breaks, check `patterns/INDEX.md` for a debug pattern. Follow it. Fix the issue and re-run VERIFY.
5. **GROW** — After meaningful work, run this binary checklist:
   - **Ground:** What changed in reality? Name the changed behavior, system, command, dependency, or workflow.
   - **Record:** If project state changed, update the "Current Project State" section above. If documented facts changed, update the relevant `context/` file surgically.
   - **Orient:** If this task can recur and no pattern exists, create one in `patterns/` using `patterns/README.md`, then add it to `patterns/INDEX.md`. If a pattern exists but you learned a gotcha, update it.
   - **Write:** Bump `last_updated` in every scaffold file you changed. If the why matters, run `mex log --type decision "<what changed and why>"` or `mex log "<note>"`.
