# v2 Feature Request — from recall tool to interview copilot

**Status:** Feature request. Not a build plan.
**Date:** 2026-09-14
**Revision:** 3. Each revision was reviewed against the codebase rather than against the progress
log. Revision 1 had eleven confirmed errors, revision 2 had ten. §11 and §12 record every one, so
the corrections are not silently absorbed.
**Extends:** `interviewpreprecallprd.md`. Reverses four of its guardrails, each named below with the
decision that reverses it.
**Reader:** anyone who has read `docs/implementation/06-progress.md`. If you have not, read §2 first.

---

## 1. What this asks for

Today the product is **Interview Prep Recall**: a Windows overlay that hears the interviewer and
resurfaces a sentence you already wrote. It never writes anything itself. That is an
architecturally enforced guarantee, not a preference.

v2 keeps that and adds a second job. The app becomes an **interview copilot**:

1. **A workspace.** You create a company you applied to. Everything about that application lives
   inside it: the job ad, your resume, company research, interviewer notes, prep notes, and every
   interview you ran against it, transcripts included.
2. **A suggester.** When the interviewer asks something, the app can also propose a tailored
   answer, built from your resume, the job ad, and what has already been said in this interview.
   Not a generic answer. This answer, for this question, in this conversation.
3. **A copilot, not a lookup.** It watches the whole conversation, not just the last sentence, and
   raises things on its own: a job-ad requirement you have not evidenced, a story you prepared and
   have not used, a contradiction against your own resume, a question worth asking back.

| Reference | What we take | What we do not take |
|---|---|---|
| Granola | External listener, no bot joins the call, no video, works with any meeting app | Its post-hoc note-taking focus |
| Contact-centre agent assist | Proactive analysis, next-best-action, surfacing before you ask | Its supervisor and QA tooling |
| Claude / ChatGPT Projects | A named container that owns files and conversations | Chat as the primary surface |

---

## 2. What already exists

Accurate as of `3c8485c`, verified against the code rather than against the progress log.

### 2.1 Built, and its tests pass

**"Tests pass" is not "verified working."** Three of these have never run against real hardware or a
real API key. The right-hand column says which.

| Capability | Where | Verified how far |
|---|---|---|
| Audio capture | `audio/capture.py` | Tests only. **Never run on a real Windows audio device** (M1) |
| Pluggable streaming STT | `stt/` | Local, Deepgram and ElevenLabs behind one Protocol, with a conformance suite. **No live vendor protocol check** (AS-8) |
| Utterance assembly | `stt/assembler.py` | Tests. Silence-terminated finalised spans |
| Two-stage matching | `matching/` | Tests. **Stage-2 never run against a real Anthropic key** (T4.7) |
| Five typed context sources | `notes/model.py` | Tests. `COMPANY`, `ROLE` (job ad), `INTERVIEWER`, `PREP`, `RESUME` |
| Multiple named context sets | `notes/store.py` | Tests. Atomic write, 5-deep backup rotation, v1 to v2 migration |
| Overlay | `ui/overlay.py` | Tests. Frameless, always-on-top, drag, resize, opacity, brightness, lock |
| Progress checklist | `tracker/progress.py` | Tests. Mic-only, with echo suppression |
| Encrypted transcript store | `report/store.py`, `platform/win_dpapi.py` | Tests, with a fake cipher. **DPAPI itself is Windows-only and unrun** |
| Post-interview report | `report/` | Tests. Four rubric dimensions, evidence-citation enforced. **Never run against a real key** |
| Session state machine | `session/manager.py` | Tests. Explicit states, health orthogonal |
| Diagnostics ring | `diagnostics/ring.py` | Tests. Field allowlist, never transcript |
| FR79 separation wall | `report/separation.py` | Tests. Static import check: the report package may not import the overlay |
| Design system | `docs/prism-design-system.md`, `ui/indicators.py` | PRISM tokens are hand-written into the Qt chrome |

**560 tests pass** in the non-GUI subset. A further 12 Qt modules need a display and run on Windows CI.

### 2.2 Not built

| Gap | Evidence |
|---|---|
| **The app does not start** | `__main__.py:83` raises `NotImplementedError` on purpose (T9.6a) |
| **Screen-capture exclusion is a stub** | `platform/win_capture_exclusion.py` is a docstring saying "Not yet implemented". **FR14 and FR14a are v1 requirements and are not met.** The overlay is currently visible in a screen share |
| No real embedding model | `notes/index.py` defines an `Embedder` Protocol. Only test fakes implement it |
| Audio capture never validated on Windows | M1 blockers. D-68 records that an idle loopback endpoint emits no callbacks at all |
| No packaging | T9.4. No installer, no signing, no update path |
| No first-run setup wizard | T9.3 |
| No company or project container | Context sets are flat, with nothing above them |
| Sessions link to nothing | `report/store.py` paths are `{session_id}.transcript`, and one encrypted `sessions.index` sits at the root |
| No PDF or DOCX ingest | `notes/importer.py` and `ui/import_notes.py` take `.txt` and `.md` |
| No generated text anywhere live | Forbidden by FR10, FR42, FR79 and D-5 |
| No proactive behaviour | The pipeline is strictly request-response per utterance |
| No calendar or meeting-platform integration | Confirmed absent across the tree |

### 2.3 Already delivered, contrary to the request

The request lists post-interview scoring as a future roadmap item. **It shipped in M11.**
`report/evidence.py` defines the sections: prep coverage, role fit, resume use, craft, what went
well, what to change. `report/generator.py` rejects any finding that cannot cite the utterance or
chunk it rests on (FR78, FR31). It is descriptive with evidence, not a single score.

**Decision: keep as built** (D-U-keep). Removed from the roadmap, extended only to cover the new
suggest lane (FR106).

---

## 3. Decisions

Continuing `docs/implementation/00-decisions-and-assumptions.md`. D-U13 is the last existing entry.

| ID | Decision | Consequence |
|---|---|---|
| **D-U14** | **Two lanes: recall and suggest.** Recall keeps the verbatim guarantee unchanged. Suggest is generated, always visually distinct, and can be switched off. | Reverses D-5 and FR42 **for the suggest lane only**. FR79 stays: report text still cannot reach the overlay. |
| **D-U15** | **Windows first. The platform abstraction layer lands before macOS is attempted.** | D-U4 stands for v2. `platform/` gains a Protocol per capability. No macOS code in v2. |
| **D-U16** | **`Company` is a new container above `ContextSet`.** It owns structured fields, many context sets, and many interview sessions. | See D-U24 for how it is stored, which is not by extending the note-set schema. |
| **D-U17** | **Meeting data is entered by hand in v2.** No calendar OAuth, no Meet API. | The Google Meet integration in the request is deferred whole. Capture already works with every meeting app. |
| **D-U18** | **PDF and DOCX are accepted at import.** | Reverses D-U1's deferral of `.docx`. Adds a layout-free chunking strategy. |
| **D-U19** | **Proactive assistance is three behaviours**: next-best-action, gap and risk alerts, and a rolling conversation state. **No live web or company search during an interview.** | Keeps the in-interview network surface to the calls already accounted for. |
| **D-U20** | **Bring your own Anthropic key.** No hosted backend, no accounts, no billing. | Confirms D-U12. Without a key the app still captures, transcribes, prefilters and recalls. Suggest, report and stage-2 need it. |
| **D-U21** | **PRISM stays. The app shell is rebuilt around it.** | The main window becomes a workspace. The overlay's D-U7 neutral-gray exemption is unchanged. |
| **D-U22** | **The composition root is finished before any v2 feature is built.** | The app must launch before it grows. §8's order follows from this. |
| **D-U23** | **D-10 is amended: the mic stream feeds the progress tracker *and* the proactive engine.** It still never feeds recall matching. | FR105 needs the user's own speech to detect a contradiction against a `RESUME` chunk. D-10's word was "exclusively", so this is a reversal and is named as one. Recall stays interviewer-only, which is what D-10 was protecting. |
| **D-U24** | **`Company` is a separate store with its own file and its own schema version. Context-set files are not migrated and stay at schema v2.** | `MIGRATIONS` in `notes/store.py` is per-file, `dict -> dict`, and always ends in `ContextSet.from_dict`. It structurally cannot build a container spanning files. Backfill is a one-time store-level upgrade, not a schema bump. Every embedding cache survives untouched, because cache files are keyed on note-set id. |
| **D-U25** | **The shared resume is a library, and creating a context set copies the chosen chunks into it.** Shared at the library level, materialised per set. | `EmbeddingIndex.build()`, `Prefilter.note_set`, `ContextSet.verify()` and D-58's snapshot all assume every in-scope note lives in one set. A referenced-but-external source is invisible to all four. Copying keeps every one of those invariants intact. Cost: editing the library does not retro-update existing sets, which is correct anyway, since a past interview must be graded against what you actually had. |
| **D-U26** | **The suggest lane is its own package (`suggest/`) rendered by its own module (`ui/suggest_panel.py`).** `report/separation.py` is generalised and a second assertion added, so recall cannot import suggest and vice versa. | The existing wall is a static import check between a package and a module. It cannot see inside one module, so two lanes in `ui/overlay.py` would be unenforceable. Splitting the modules makes the mechanism that already works apply unchanged. |

---

## 4. New functional requirements

FR1 to FR87 are taken. Numbering starts at FR90.

### 4.1 Company workspace

| ID | Requirement |
|---|---|
| **FR90** | A **Company** is a named, persisted container. It owns structured fields, context sets and interview sessions. Deleting one deletes everything it owns, after one confirmation naming the counts. |
| **FR91** | A company carries optional structured fields: display name, website URL, LinkedIn URL, role title, application date, status, free-text notes. URLs are stored and displayed only. Nothing fetches them (D-U19). |
| **FR92** | A company owns **one or more context sets**, one per interview round. A new set may be seeded by copying an existing set in the same company. |
| **FR93** | A **resume library** exists at app-root scope. Creating or editing a context set copies chosen resume chunks into that set (D-U25). The library is where you maintain your resume; the set is what an interview is matched and graded against. |
| **FR94** | Every saved session is filed under exactly one company and one context set. The session list filters by company. Sessions that exist before the backfill move to a company named `Unfiled`. |
| **FR95** | A session may carry meeting metadata entered beforehand: title, scheduled time, and named participants with optional role and LinkedIn URL. Participants are written into the context set as `INTERVIEWER` chunks, so they reach matching by the path that already exists. |
| **FR111** | Switching company is an explicit operation with the same guarantees as FR43's set switch: **refused while a session is running**. It rebuilds the four things `activate_context_set` rebuilds — the active `ContextSet`, `EmbeddingIndex.build()`, the prefilter's set reference, and the tracker's set reference plus its reset — and one new one, the session list's company filter (FR94). A company's **most recently used context set** becomes active; if it has none, the switch creates an empty one rather than leaving no active set. |

### 4.2 Ingestion

| ID | Requirement |
|---|---|
| **FR96** | Import accepts `.pdf` and `.docx` in addition to `.txt` and `.md`. Extraction is text-only. Images, and text recoverable only by OCR, are not extracted. |
| **FR97** | When a document carries no usable heading structure, a **semantic chunking strategy** is offered alongside the existing three. It is named and switchable before saving (T3.7a), and every chunk stays editable before it is written. |
| **FR98** | A file that yields no extractable text is **rejected with the reason at import**, never saved as an empty or partial source. A PDF of scanned images is the expected case and must say so by name. |

### 4.3 The suggest lane

| ID | Requirement |
|---|---|
| **FR99** | On an interviewer utterance the app may render a **generated suggested answer** in a lane that is distinguishable from the recall lane at a glance, without reading the text. |
| **FR100** | The suggestion is generated from: the utterance, the rolling conversation state (FR103), the matched context chunks, the job ad, and the resume chunks in the active set. It carries the ids of the sources it drew on, and the panel shows them. |
| **FR101** | The suggest lane is **off by default** and enabled per company. Enabling it requires a one-time acknowledgement that generated text is being shown and that it is not something you wrote. Separate from FR63 and FR85, for the reason FR85 is separate. |
| **FR102** | With no API key, on API failure, or on timeout, the suggest lane **shows a single-line reason and no suggested content.** It never falls back to unmarked recall text. The recall lane is unaffected. |
| **FR113** | **`suggest/` may not import `ui/overlay.py`, and `matching/` may not import `suggest/`.** Enforced by the generalised `separation.py` check at test time, the way FR79 already is (D-U26). |

### 4.4 Proactive assistance

| ID | Requirement |
|---|---|
| **FR103** | The app maintains a **rolling conversation state**: topics covered, questions asked, points made, time elapsed. In-memory session state, updated on each finalised utterance from either stream. |
| **FR112** | `ConversationState` is cleared by purge. It is added to `PurgeHooks` as a sixth hook, **ordered immediately before `drop_transcript`**, because it is derived from the transcript and must not outlive it. **FR59 needs no amendment**: it requires only that in-flight network work is neutralised before local state is cleared, and the new hook sits well after `cancel_network`. |
| **FR104** | The app raises **next-best-action prompts** unprompted: a prepared point not yet used, a question worth asking back, a job-ad requirement not yet evidenced. Each cites its source chunk. Rate-limited, and never while the interviewer is speaking. |
| **FR105** | The app raises **gap and risk alerts**: a job-ad requirement raised with no matching evidence, a statement contradicting a `RESUME` chunk, a single answer running long. Each cites the chunk or utterance that triggered it. An alert that cannot cite one is not shown (FR78 principle). Requires the mic stream (D-U23). |
| **FR106** | The report gains a **fifth section covering the suggest lane**: what was suggested, what you used, what you ignored. Same evidence rule. Omitted, not faked, when the lane was off. |

### 4.5 Product surface

| ID | Requirement |
|---|---|
| **FR107** | The main window is a **workspace**: companies on the left, the selected company's sources and interviews in the middle, session controls always reachable. Settings, reports and diagnostics move into the shell. |
| **FR108** | A **first-run wizard** covers, in order: the FR63 disclosure, STT model choice and download (D-U13), audio device selection and test, optional API key entry, and resume import. Skippable after the disclosure, resumable later. |
| **FR109** | The app ships as a **signed Windows installer** that installs, launches and uninstalls cleanly with no Python toolchain on the machine. |
| **FR110** | **Platform capabilities sit behind Protocols**: audio capture, credential storage, at-rest encryption, screen-capture exclusion, crash reporting. Windows is the only implementation in v2. There is exactly one place to add a second (D-U15). |
| **FR114** | **FR14 and FR14a are completed before the suggest lane ships.** `SetWindowDisplayAffinity` is implemented and verified on a real screen share. A lane that renders generated text you are reading must not be visible to the person you are reading it to. |

---

## 5. Non-goals for v2

- **No macOS or Linux build.** The seam is built (FR110). No second implementation.
- **No calendar, Zoom, Teams or Meet integration** (D-U17).
- **No live web search during an interview** (D-U19).
- **No hosted backend, accounts or billing** (D-U20).
- **No video capture, ever.** Audio only. Not a scope call; it is what the product is.
- **No speaker diarization.** Stream separation plus echo detection stands (D-8, AS-5).
- **No use in someone else's interview.** Unchanged.
- **No single overall interview score.** The report stays descriptive with evidence.

---

## 6. Data model

### 6.1 Shape

"App root" below is `%APPDATA%\InterviewPrepRecall`. This is a single-user desktop app. There is no
user identity, no tenancy and no isolation boundary, and none is being introduced.

```
App root
├── resume library  (RESUME chunks, copied into sets on use)   FR93, D-U25
├── companies/<uuid>.json        NEW STORE, own schema version  D-U24
│   └── fields, ordered context-set ids, last-used set id       FR91, FR111
├── notesets/<uuid>.json         UNCHANGED, stays schema v2
├── index/<uuid>.<model>.npz     UNCHANGED, caches survive
└── sessions/<id>.transcript     gains a company id             FR94
```

A company **references** context sets by id. It does not contain them. That is what lets the
existing note-set store, its atomic write, its backup rotation and its embedding cache carry on
untouched.

### 6.2 Backfill, not a schema migration

`MIGRATIONS` in `notes/store.py` maps one file's dict to the next version's dict and always ends in
`ContextSet.from_dict`. It cannot produce a different type, and it cannot span files. **A schema v3
bump is the wrong tool** (D-U24). Instead, a one-time store-level backfill runs once at startup:

1. For each existing note-set file, create a company named from the set, referencing that one set.
2. Create an `Unfiled` company.
3. Copy each set's `RESUME` chunks into the resume library. Keep the set's own copy as-is.
4. Write a marker so the backfill never runs twice.

**Nothing in `notesets/` is rewritten.** Note-set ids, note ids and content hashes are all
untouched, so every `.npz` cache file stays valid. This is the difference between the backfill and
the schema bump: the schema bump would have had to rewrite every set file to move it under a
container, and `path_for()` names each cache by note-set id.

### 6.3 The session store needs its own backfill, and it is smaller than it looks

`report/store.py` is a separate store the notes migration cannot reach. It also does **not** work
the way a first reading suggests. `_reindex` says so in as many words: the index is *"derived,
encrypted, and never authoritative... Rebuilt from the files on every change rather than maintained
incrementally, so it cannot drift into listing a session that no longer exists or hiding one that
does."* `list_sessions()` reads the session files. The index exists for speed and for FR83.

So the backfill is one thing, not three:

- **The company id goes in the session record**, which is the authoritative copy. `_reindex()` then
  carries it into the index on the next write, for free.
- **There is no index migration**, and none should be written. An index migration would be
  maintaining incrementally exactly what the store refuses to maintain incrementally.
- **Session files are not renamed.** Renaming an encrypted file to add a key buys nothing and risks
  orphaning a transcript that cannot be re-derived.
- Records with no company become `Unfiled`.
- **An unreadable session is skipped and recorded, not fatal.** This is the store's existing rule
  and it is deliberate: one unreadable session must not hide the rest. A backfill that stopped on
  first failure would invert it.

**This backfill runs on Windows only.** `default_cipher()` raises anywhere else (D-40), so no
session can be read or written off-platform. It is listed in §8 as such.

---

## 7. Architecture changes

| Area | Change | Risk |
|---|---|---|
| new `suggest/` | The generator. Unconstrained output, unlike the selector. Rendered by `ui/suggest_panel.py` | Walled from recall by FR113's import assertions, not by convention |
| `report/separation.py` | Generalised from one hardcoded pair to a checkable rule, then given FR113's second pair | It is the only structural guarantee in the product. Changing it needs its own tests first |
| `session/` | Owns `ConversationState` (FR103), cleared by a sixth purge hook (FR112) | `PurgeHooks` is a frozen dataclass and `_purge` iterates a hardcoded tuple whose order is FR59. Both change together, and FR59's text changes with them |
| new `proactive/` | Detectors for FR104 and FR105. Each returns a cited prompt or nothing | Rate limiting and the never-interrupt rule live here, not in the UI |
| `tracker/` and mic routing | The mic stream gains a second consumer (D-U23) | D-10 said "exclusively". The amendment is explicit so a later reader does not read it as drift |
| `notes/importer.py` | Two extractors, one chunking strategy | PDF extraction quality varies wildly. FR98 is the guard |
| new company store | New module beside `notes/store.py`, reusing its atomic-write and rotation shape | Do not fold it into the note-set schema (D-U24) |
| `report/store.py` | Company id in the index, plus §6.3's backfill | Encrypted index. A failed read must stop, not rebuild |
| `app.py` | `activate_company` beside `activate_context_set` (FR111) | Must refuse mid-session, as FR43 already does for sets |
| `platform/win_capture_exclusion.py` | Implement it (FR114) | Currently a docstring. A v1 requirement, unmet |
| `platform/` | Protocol per capability (FR110) | Pure refactor. Tests should prove behaviour did not change |
| `ui/` | **`main_window.py` is rewritten into a workspace shell. Every other dialog is kept and embedded as a component** — `overlay.py`, `editor.py`, `report_view.py`, `settings.py`, `indicators.py`, `diagnostics_view.py`, `import_notes.py`, `restore.py`, `checklist.py`, `match_feed.py`. Plus the wizard (FR108), company editor, suggest panel and proactive tray | `ui/` is 5,741 of the app's 14,570 lines. Confining the rewrite to the one window that is currently a settings panel keeps the overlay's contrast sweeps, its geometry work and the PRISM tokens, and keeps their tests meaningful |
| `__main__.py` | Finish `_build_application`. Real embedder. No-API-key policy | Blocks everything |

---

## 8. Sequencing

One pull request per block. Each leaves the app runnable and CI green.

**Two of these cannot be finished by an agent.** Every row therefore splits the work. Sizes are
rough and are for ordering, not for planning.

| PR | Agent can do | Only you can do | Size |
|---|---|---|---|
| **1. Make it run** | Composition root, no-API-key policy, wizard (FR108), embedder behind its Protocol | **Run the first-launch model download** (huggingface.co is blocked here, AS-9) | L |
| **2. Windows reality** | Latency harness, device-enumeration code, D-68 keep-alive wiring | **Run M1 on your Windows 11 machine with a real audio device.** Nothing downstream is trustworthy until this passes | M + hardware |
| **3. Capture exclusion** | `SetWindowDisplayAffinity` via ctypes (FR114, FR14, FR14a) | **Verify on a real screen share.** Headless cannot test this | S + hardware |
| **3b. UI shell decision** | — | Already taken: new shell, existing dialogs kept as components (§7) | — |
| **4. Company store** | New store, FR90 to FR92, FR111, §6.2 backfill | — | L |
| **5. Session filing** | FR94, FR95, §6.3 record backfill | **Run the backfill.** Windows-only: `default_cipher()` raises elsewhere (D-40) | M + hardware |
| **6. Resume library** | FR93, copy-into-set, library editor | — | M |
| **7. Ingestion** | PDF and DOCX, FR96 to FR98 | Supply real resumes and job ads as fixtures | M |
| **8. App shell** | Workspace UI (FR107), company editor, PRISM applied | Judge it at a glance, as with FR72's 1 m test | L |
| **9. Separation wall** | Generalise `separation.py`, add FR113's assertions, with tests first | — | S |
| **10. Conversation state** | FR103, FR112 sixth purge hook, FR59 amended | — | M |
| **11. Suggest lane** | `suggest/`, `ui/suggest_panel.py`, FR99 to FR102 | **Approve FR101's disclosure wording.** An ethics decision, not copy | L |
| | *Depends on PR 3 (FR114) **and** PR 2: OQ-12 and §9 both need PR 2's latency numbers before this lane's budget can be set* | | |
| **12. Proactive** | `proactive/`, FR104, FR105, D-U23 mic routing, rate limits | Judge whether the alerts help or intrude, live | L |
| **13. Report extension** | FR106 | **An Anthropic key.** T4.7 has never run against one | S |
| **14. Platform seam** | FR110 Protocols | — | **L, and growing** |
| **15. Packaging** | PyInstaller build, installer script, **re-run PR 1's first-run download against the packaged build** | **Buy a code-signing certificate.** Needs a legal identity and money | M + purchase |

### What the hardware gate actually blocks

The gate is **not** only PRs 1 and 2. Four pull requests need your Windows machine:

| PR | Why |
|---|---|
| 1 | First-run model download. huggingface.co is blocked in the dev container (AS-9) |
| 2 | M1 audio capture on a real device |
| 3 | Screen-capture exclusion, verified on a real screen share |
| 5 | The session backfill. `default_cipher()` raises off Windows (D-40) |

And PR 3 is not a leaf: **FR114 makes PRs 11 and 12 wait on it**, so the gate reaches the headline
feature. PR 11 additionally needs PR 2's latency numbers, per OQ-12 and §9.

**PRs 4, 6, 7, 8, 9 and 10 are clear of the gate.** They are data-model, ingestion and UI work and
can proceed in full while you are away from the machine. That is six of fifteen, which is what makes
the split worth stating rather than waving at.

### Why PR 14 is larger than it reads

PR 14 is described in §7 as a pure refactor. It is not, because it runs last:

- PR 2 adds WASAPI device enumeration
- PR 3 adds `SetWindowDisplayAffinity` through `ctypes`
- PR 15 adds PyInstaller path handling

Each lands as direct Windows code and each then has to be pulled behind a Protocol by PR 14. The
seam gets bigger the later it runs. It stays late because D-U15 only requires it before macOS, and
moving it earlier would mean designing Protocols around code that does not exist yet. **The cost is
accepted, not overlooked**, and the size is marked L rather than M to say so.

### PyInstaller changes the write profile

`04-test-strategy.md` is explicit: *"Run against the packaged build, not just the dev build —
PyInstaller changes the write profile."* The design doc's allowlist puts the model caches outside
the app root, at `%USERPROFILE%\.cache\huggingface` and `%LOCALAPPDATA%\torch`, plus PyInstaller's
own `_MEI*` temp directory. **PR 1's first-run download is therefore not finished until PR 15
re-runs it against the packaged build.** That is the one backward dependency in this sequence, and
it is named rather than discovered.

---

## 9. Risks

| Risk | Why it is real | Mitigation |
|---|---|---|
| **The verbatim guarantee is the product's spine, and FR99 cuts into it** | Retrieval-only is enforced in four places and cited by dozens of tests. A generated lane is a second, weaker contract beside a strong one | Two lanes in two packages, walled by FR113's import assertions, the way FR79 already works. Off by default, per company |
| **The Windows audio assumption is still unproven** | M1 has never run on the target machine. D-68 already found an idle loopback endpoint delivers no callbacks at all, which breaks silence-based finalisation | PR 2 exists for this. Nothing downstream of it is trustworthy until it passes |
| **The overlay is currently visible in a screen share** | FR14 is a v1 requirement and `win_capture_exclusion.py` is a docstring. This is true today, before any v2 work | PR 3, before the suggest lane, by FR114 |
| **Suggestion latency stacks on an unmeasured STT latency** | The budget is 2 to 3 s end to end. Local STT alone was estimated at 2 to 3 s and never measured on the target laptop. A generated answer is far more output tokens than an enum | Measure in PR 2 before designing PR 11's budget. Stream the suggestion. Consider a different model for this lane (OQ-12) |
| **Reading a generated answer on camera is visible** | Recall shows a bullet you wrote and already know. A generated paragraph must be read, and reading is obvious | The suggest lane is bullets and fragments, never prose. Carry D-6's sentence-boundary discipline across |
| **Proactive assistance competes with the interview for attention** | An alert that fires while you are thinking is worse than no alert | FR104's never-while-they-are-speaking rule, hard rate limits, a global mute |
| **Disclosure gets harder, not easier** | Recall is defensible: it is your own notes. A tailored generated answer is a different claim, and the original non-goals already ruled out use in someone else's interview | FR101's acknowledgement must say plainly what the lane does. Do not soften it. Wording is yours to approve (PR 11) |
| **PDF extraction quality is unpredictable** | Multi-column resumes and design-heavy templates extract as interleaved nonsense. Bad chunks poison the index silently | FR98 rejects empties. FR97's review step is mandatory, not skippable |
| **Scope** | Fifteen pull requests on a codebase that cannot currently start | PRs 1 to 3 come first and are not negotiable. PRs 4 to 10 run in parallel with the hardware gate |

---

## 10. Open questions

| ID | Question | Owner | Blocks |
|---|---|---|---|
| **OQ-12** | Which model serves the suggest lane? The selector's Haiku is tuned for a one-token enum, not for drafting | Needs PR 2's latency numbers | PR 11 |
| **OQ-13** | Does the suggest lane need its own confidence floor, or does it inherit the prefilter's τ? | Design | PR 11 |
| **OQ-14** | Is the resume library one document or many? | You | PR 6 **and PR 7** — the answer decides whether the importer handles one resume or a set of them |
| **OQ-15** | How do a proactive alert and a recall snippet share the overlay when both fire? | Design | PR 12 |
| **OQ-16** | What signs the installer, and at what cost? | You | PR 15 |
| **OQ-17** | What exactly does FR101's acknowledgement say? | You | PR 11 |
| **OQ-18** | How many proactive alerts per minute is the ceiling, and does it differ by kind? | You, from live use | PR 12 |
| **OQ-19** | Does the report's fifth section (FR106) need your judgement of each suggestion, or only whether you used it? | Design | PR 13 |

---

## 11. What changed in revision 2

Revision 1 was reviewed against the codebase. Eleven confirmed errors, listed so the corrections
are not silently absorbed.

| # | Error in revision 1 | Fix |
|---|---|---|
| 1 | Listed screen-capture exclusion as built | Moved to §2.2. FR114 and PR 3 added. `win_capture_exclusion.py` is a docstring |
| 2 | Proposed a "schema v3 migration" for the Company container | D-U24 and §6.2. `MIGRATIONS` is per-file and cannot span files. Company is a separate store; note-set files stay v2 |
| 3 | Made the resume user-level and referenced | D-U25 and FR93. A referenced source is invisible to `EmbeddingIndex.build()`, `Prefilter.note_set`, `ContextSet.verify()` and D-58's snapshot. It is a library that copies into sets |
| 4 | Claimed `report/separation.py` could wall the two lanes as-is | D-U26 and FR113. It is a package-to-module import check and cannot see inside one module. The suggest lane gets its own package |
| 5 | FR105 silently reversed D-10, and §3 claimed no other reversals | D-U23 names the reversal. Recall stays interviewer-only |
| 6 | No migration plan for `report/store.py` | §6.3. Its own backfill, its own failure rule |
| 7 | No design for switching company | FR111. Refuses mid-session, rebuilds what `activate_context_set` rebuilds, defines which set becomes active |
| 8 | Called purge "a hook list" | FR112. It is a frozen dataclass plus an FR59-ordered tuple. The new hook has a named position |
| 9 | Sequencing was not executable: PRs 1 and 2 need hardware and a blocked download | §8 splits every row into agent work and your work, and names which PRs do not depend on the gate |
| 10 | FR102 said the lane "renders nothing and says why" | Reworded: a single-line reason and no suggested content |
| 11 | §2.1 blurred "tests pass" with "works" | §2.1 gained a verification column. Three rows have never run against real hardware or a real key |

Three findings from the review were **dropped** rather than fixed, because they did not survive a
second pass:

- *"A user level needs identity, tenancy and isolation."* Wrong product. This is a single-user
  desktop app with one `%APPDATA%` root. §6.1 says so explicitly now.
- *"The backfill invalidates every embedding cache."* Moot once the company is a separate store:
  nothing in `notesets/` or `index/` is rewritten.
- *"FR105 is unimplementable."* Overstated. It needed D-10 amended, not a redesign.

---

## 12. What changed in revision 3

A second review round, against the fixes themselves rather than against revision 1. Ten confirmed.

| # | Error in revision 2 | Fix |
|---|---|---|
| 1 | §6.3 proposed migrating the encrypted session index | `report/store.py:345` states the index is *"derived, encrypted, and never authoritative... rebuilt from the files on every change"*. The company id goes in the session **record**; `_reindex()` carries it. §6.3 rewritten, and it is now the smallest of the three backfills rather than the largest |
| 2 | §6.3 said the backfill stops if the index cannot be decrypted | That inverts the store's deliberate rule, which is that one unreadable session must not hide the rest. Skip and record, as `list_sessions` already does |
| 3 | The session backfill was not marked as needing Windows | `default_cipher()` raises off Windows (D-40). Named in §6.3 and in §8's gate table |
| 4 | FR112 said FR59's order is amended | FR59 requires only network-first. No amendment needed, and claiming one would have sent someone editing a requirement for no reason |
| 5 | FR111 said "rebuilds what `activate_context_set` rebuilds" | Now names the four, plus the one new thing a company switch adds |
| 6 | §8 said the hardware gate is PRs 1 and 2 | It is PRs 1, 2, 3 and 5, and FR114 makes PR 3 block the suggest lane. New gate table says which six PRs are genuinely clear of it |
| 7 | §8 gave PR 11 only a PR 3 dependency | §9 and OQ-12 both require PR 2's latency numbers first. Stated in the table |
| 8 | PR 14 was called a pure refactor, sized M | PRs 2, 3 and 15 each add direct Windows code that PR 14 must then abstract. Re-sized L, with the reason for keeping it late written down |
| 9 | PR 1's first-run download was treated as finishable in PR 1 | `04-test-strategy.md` says PyInstaller changes the write profile, and the model caches sit outside the app root. PR 15 re-runs it. The one backward dependency, now named |
| 10 | OQ-14 blocked only PR 6 | It blocks PR 7 too: the answer decides whether the importer handles one resume or many |

Four review findings were **dropped** rather than fixed:

- *"mypy reports 45 errors in 17 files."* False. `python -m mypy interview_prep_recall` returns
  *"Success: no issues found in 62 source files"*, and `ruff check` returns *"All checks passed!"*.
  The reviewer referred to PyQt5; the project uses PySide6 6.11.2.
- *"`audio/` and `platform/` should be discarded as Windows-only."* Windows is the target (D-U15).
  Windows-specific is the requirement, not a defect.
- *"`notes/`, `ui/`, `report/` and `matching/` need major redesign because they cite the guardrail."*
  Most citations are comments. D-U14 leaves the recall lane unchanged and D-U24 leaves `ContextSet`
  unchanged, so the work is additive.
- *"D-U25, D-U26 and FR112 are not implemented in the code."* They are requirements in a feature
  request. Reporting that a requirement is unbuilt is not a finding.

Line counts in this document are measured, not estimated: **14,570** lines under
`interview_prep_recall/`, **15,206** under `tests/`, across 35 test files.
