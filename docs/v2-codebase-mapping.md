# v2 Requirements Mapped to the Existing Codebase

**Companion to:** `v2-feature-request.md` (revision 7).
**Updated:** 2026-09-14 for OQ-14's answer and for T9.6a landing on `main` at `13df252`.
**Question this answers:** does v2 modify this codebase, or start fresh?
**Date:** 2026-09-14

---

## 1. The answer

**Modify. Do not start fresh.** Rewrite one file.

The case for starting fresh rested on one true fact: the app did not run. That was a wiring problem
in a single function, and **T9.6a has since fixed it** — `_build_application` is real as of
`13df252`. The app launches. It still cannot run a session, because audio capture (M1) and the
overlay wiring (M5) are missing and `model_present` blocks until the embedding weights exist.

That progression is the argument in miniature. The gap was never architectural. Everything a fresh
start would have to rebuild already exists, is tested, and passes its gates.

Three measurements decide it:

| Measurement | Value |
|---|---|
| App code | **14,873 lines** |
| Test code | **15,483 lines**, 36 files, 573 passing in the non-GUI subset |
| `ruff check` | `All checks passed!` |
| `ruff format --check` | 98 files already formatted |
| `mypy interview_prep_recall` | `Success: no issues found in 62 source files` |
| Code that v2 **deletes** | `ui/main_window.py`. That is the whole list |

A fresh start throws away more tests than it writes code, and buys nothing that a new store, a new
package and one rewritten window do not already buy.

**The one exception:** `ui/main_window.py` is a settings-and-reports panel, and FR107 needs a
workspace. That window is rewritten. Every other dialog is kept and embedded as a component.

---

## 2. What the v2 work actually is

Three shapes, and only one of them touches existing behaviour.

| Shape | Requirements | Existing code affected |
|---|---|---|
| **New, beside what exists** | FR90–FR95, FR99–FR106, FR111–FR113 | None. New store, new `suggest/`, new `proactive/` |
| **Extends an existing seam** | FR96–FR98, FR108, FR110, FR114 | Adds to an interface that was built to be added to |
| **Rewrites** | FR107 | `ui/main_window.py`, one file |

That distribution is the argument. The retrieval lane, the matching pipeline, the STT interface, the
session state machine, the note store and the report are all untouched by v2, because D-U14 keeps
recall unchanged and D-U24 keeps `ContextSet` unchanged.

---

## 3. Package by package

Measured, not estimated.

| Package | Lines | v2 verdict | What happens |
|---|---|---|---|
| `stt/` | 1,834 | **Untouched** | The backend Protocol, three implementations, the automatic fallback and the conformance suite already do what v2 needs. This package is the model for how the LLM provider seam should look |
| `audio/` | 792 | **Untouched** | Windows capture is the requirement (D-U15), not a liability. Still needs M1 validation, which is PR 2 and predates v2 |
| `session/` | 680 | **One hook** | `PurgeHooks` gains a sixth field, `_purge` a sixth tuple entry (FR112) |
| `matching/` | 714 | **Changed, still additive** | Stage 1 and stage 2 keep their logic. `Prefilter` takes a list of sets instead of one (FR117), `KIND_TAU_OFFSET` gains a row (FR123), and `MessagesClient` generalises into the provider Protocol (FR126). The suggest lane still runs beside them, walled by FR113 |
| `tracker/` | 260 | **One new consumer** | The mic stream gains the proactive engine alongside the tracker (D-U23). The tracker itself does not change |
| `notes/` | 1,103 | **Additive, plus two changes** | Two extractors and one chunking strategy (FR96–FR98). `store.py`'s hardcoded `"notesets"` subdirectory becomes a parameter (D-U27). `model.py` gains one `SourceKind` member and a version bump to v3 (D-U35) — the only place v2 touches it, and it amends D-U24 rather than sliding past it |
| `report/` | 1,339 | **Additive** | A company id in the session record (§6.3) and a fifth report section (FR106). `separation.py` is generalised to take a pair rather than a hardcoded one |
| `diagnostics/` | 233 | **Untouched** | The ring and its field allowlist already cover the new events |
| `platform/` | 179 | **One stub filled, then wrapped** | `win_capture_exclusion.py` is implemented (FR114). Protocols added later (FR110) |
| top-level | 1,695 | **Done, plus one method** | `_build_application` **is written**, on `main` since `13df252`. `app.py` gains `activate_company` |
| `ui/` | 5,741 | **One file rewritten, the rest kept** | See §4 |
| **New** | — | — | company store, `suggest/`, `proactive/`, `ui/suggest_panel.py`, company editor, wizard |

---

## 4. The `ui` package, in detail

`ui/` is 39% of the app. Deciding it wholesale either way would be the expensive mistake, so it is
decided file by file.

| File | Verdict | Why |
|---|---|---|
| `main_window.py` | **Rewrite** | It is a settings-and-reports panel. FR107 needs a workspace with companies, sources and interviews. This is the file the product's shape is wrong in |
| `overlay.py` | **Keep** | Drag, resize, opacity, brightness, lock, text scaling and a full WCAG contrast sweep across 101 settings. The single most expensive piece to rebuild and the least reason to |
| `editor.py` | **Keep, embed** | Notes CRUD with debounced save and immutable kinds. Becomes the sources pane |
| `report_view.py` | **Keep, embed** | Session list and evidence rendering. Becomes the interviews pane |
| `import_notes.py` | **Keep, extend** | Gains `.pdf` and `.docx` and the semantic strategy (FR96–FR98). `READABLE_SUFFIXES` is the seam |
| `settings.py` | **Keep, embed** | Moves out of the top level into the shell |
| `indicators.py` | **Keep** | Where the PRISM tokens actually live. Gains one indicator for the suggest lane |
| `diagnostics_view.py`, `restore.py`, `checklist.py`, `match_feed.py`, `consent_dialog.py` | **Keep** | No v2 requirement touches them |
| `suggest_panel.py` | **New** | Required to be its own module, by D-U26 |

Rewriting `main_window.py` alone costs one file. Rewriting `ui/` wholesale would cost roughly 3,000
lines of working, tested dialogs and the twelve Qt test modules that cover them.

---

## 5. Requirement to code

| Req | Lands in | New or change |
|---|---|---|
| FR90 FR91 FR92 | new company store, beside `notes/store.py` | New |
| FR93 | a second `NotesStore` rooted at `library/`; `notes/store.py` subdirectory parameter (D-U27) | Change, one parameter |
| FR115 FR116 | copy-into-set in the company editor; provenance via the existing `Note.tags` (D-U28) | New |
| FR117 FR118 | `matching/prefilter.py` takes a list of sets; `notes/index.py` unchanged | Change, small |
| FR119 FR120 FR121 | new distiller module reading `report/record.py` | New |
| FR122 FR123 | `notes/model.py` new `SourceKind` + `SCHEMA_VERSION` 3; `prefilter.py` `KIND_TAU_OFFSET` | Change, schema |
| FR124 FR125 | `config.py` gains a model per lane; `selector.py` and `generator.py` defaults | Change, config |
| FR126 FR127 FR128 | `matching/selector.py` `MessagesClient` -> provider Protocol; new OpenAI client; `platform/credentials.py` `KNOWN_ACCOUNTS` | Change, additive |
| FR129 | `suggest/` request construction, plus a diagnostics-ring counter for cold-cache detection | New |
| FR130 | `config.py` per-lane provider and model, replacing one `llm_model_id`; `ui/settings.py` pickers | Change, migration |
| FR131 FR132 | new model-catalogue module: live fetch, curation, bundled fallback | New |
| FR133 FR134 | catalogue filters per lane; model-not-found falls back for the run only, recorded to the ring, config untouched (D-U39) | New |

**STT provider choice needs nothing.** `stt/interface.py`, the three backends, `FallbackSttBackend`
and the settings control all shipped under FR17, FR18 and FR21. The LLM half should copy that shape
rather than introduce a second one.
| FR94 | `report/store.py` session record; `_reindex` carries it | Change, small |
| FR95 | company editor writes `INTERVIEWER` chunks through the existing `ContextSet` path | New |
| FR96 FR97 FR98 | `notes/importer.py`, `ui/import_notes.py` | Change, additive |
| FR99 FR100 FR102 | new `suggest/`, new `ui/suggest_panel.py` | New |
| FR101 | new consent record, shaped on `report/consent.py` | New |
| FR103 | new `ConversationState` in `session/` | New |
| FR104 FR105 | new `proactive/`; mic routing in `app.py` (D-U23) | New |
| FR106 | `report/evidence.py` section enum, `report/generator.py` prompt | Change, small |
| FR107 | `ui/main_window.py` | **Rewrite** |
| FR108 | new wizard; `startup.py` and `first_run.py` already own the gates it wraps | New |
| FR109 | packaging, no app code | New |
| FR110 | `platform/` Protocols | Change, mechanical |
| FR111 | `app.py`, beside `activate_context_set` | New |
| FR112 | `session/manager.py` `PurgeHooks` and `_purge` | Change, 2 lines plus tests |
| FR113 | `report/separation.py` generalised, second assertion added | Change, small |
| FR114 | `platform/win_capture_exclusion.py` | Fill a stub |

**Nothing in this table deletes a passing test.** FR107 replaces `test_main_window.py`, which is the
one exception and is expected.

---

## 6. What a fresh start would cost

Stated so the option is rejected on numbers rather than on sentiment.

**You would rebuild, from nothing:**

- The streaming STT interface, three backends, and the conformance suite that lets a fourth inherit
  every test (1,834 lines)
- WASAPI loopback plus mic capture, bounded queues, and the D-68 keep-alive that took a hardware
  spike to find at all (792 lines)
- The session state machine, with health as an orthogonal attribute and an ordered purge (680 lines)
- Atomic write, five-generation backup rotation, corrupt-file recovery and a working schema
  migration, which the safety review named the single highest risk in the product (1,103 lines)
- The overlay, including the WCAG sweep across every reachable brightness setting (part of 5,741)
- Evidence-bound report generation that refuses an uncited finding (1,339 lines)
- 15,483 lines of tests

**You would keep:** the documentation. 87 requirements, 68 decisions and a traceability matrix,
which is the part that is genuinely hard to reproduce and the part a fresh start does not free you
from anyway.

**You would gain:** nothing v2 asks for. Every v2 requirement is new code beside existing code, an
extension of a seam that exists, or one rewritten window.

---

## 7. The honest case against modifying

Two real costs, so this is not one-sided.

1. **The codebase carries a guardrail v2 partly reverses.** D-5's retrieval-only rule is cited in
   comments across `notes/`, `report/`, `matching/` and `ui/`. Adding a generated lane beside it
   means the codebase states two contracts at once, and a later reader has to know which applies
   where. **Mitigation:** D-U26 puts the lane in its own package, and FR113 makes the boundary a
   test rather than a convention. The comments stay true, because the recall lane does not change.

2. **The documentation is 11,000 lines and every requirement is cross-referenced.** Adding 25
   requirements and 13 decisions means updating the decision log, the requirements table and the
   traceability matrix, or they rot. **Mitigation:** it is the same cost under a fresh start, and
   the matrix already has a recorded gap for FR66–FR87.

Neither cost approaches the cost of rebuilding 14,873 tested lines.

---

## 8. How to move forward

1. ~~**Land the wiring first.**~~ **Done.** T9.6a landed on `main` at `13df252` and the app
   launches. What is left of PR 1 is the first-run model download and the FR108 wizard.
2. **Open the hardware gate early.** PRs 2 and 3 need your Windows machine. Start them as soon as
   PR 1 lands, because PR 3 blocks the headline feature through FR114.
3. **Run the six unblocked pull requests in parallel with the gate.** PRs 4, 6, 7, 8, 9 and 10 need
   no hardware at all.
4. **Do not let PR 8 grow.** It rewrites one window and embeds nine existing dialogs. The moment it
   starts rewriting `overlay.py`, it has become the fresh start this document argues against.
5. **Keep the decision log current as you go.** D-U14 to D-U26 belong in
   `00-decisions-and-assumptions.md`, not only here. The log is the reason this review could check
   the plan against intent at all.

---

## 9. What changed since the first version of this document

- **T9.6a landed.** `_build_application` is implemented and the app launches. It still cannot run a
  session: M1 audio capture, M5 overlay wiring, and the embedding weights are all outstanding, and
  `model_present` blocks a session start until the last of those exists. **Launching is not running**,
  and this document does not claim otherwise. The app could not be launched here to check, because
  PySide6 needs `libEGL` and this container lacks it.
- **`notes/embedder.py` exists.** AS-10 records that it has never loaded weights, for the same
  huggingface.co 403 as AS-9.
- **OQ-14 is answered: many documents.** It cost less than expected. A library document is a name
  plus chunks, which is `ContextSet`'s shape, so the library is a second `NotesStore` rather than a
  new store (D-U27), and provenance rides on the `Note.tags` field that already exists (D-U28).
  `notes/model.py` is still untouched by all of v2.

None of this changes the recommendation. It strengthens it: the one function that made the app
unrunnable was fixed in a single pull request, by someone reading the same code this document maps.

---

## 10. What revision 5 changed here

- **Company-wide retrieval is a smaller change than it sounds.** `Prefilter` takes a list of context
  sets rather than one, and the per-set `.npz` cache files are concatenated. No new index type, no
  new store, no new retrieval path. Keeping the cache per set is what preserves per-set invalidation.
- **Transcript distillation is the one genuinely new module**, and `notes/model.py` gains its only
  v2 change: one `SourceKind` member and a schema bump to v3. Storing each distilled interview as a
  read-only `ContextSet` means the store, index, prefilter and verify paths all apply unchanged.
- **Multi-provider lands on a Protocol that already exists.** `MessagesClient` in
  `matching/selector.py` is already the seam; it generalises rather than being invented.
- **None of this changes the recommendation.** The additions are new modules and one widened
  parameter. The count of files v2 rewrites is still one: `ui/main_window.py`.
