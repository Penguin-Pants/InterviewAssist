# v2 Feature Request — from recall tool to interview copilot

**Status:** Feature request. Not yet a build plan.
**Date:** 2026-09-14
**Supersedes:** nothing. It extends `interviewpreprecallprd.md` and reverses three of its guardrails,
each named below with the decision that reverses it.
**Reader:** anyone who has read `docs/implementation/06-progress.md`. If you have not, read §2 first.

---

## 1. What this asks for

Today the product is **Interview Prep Recall**: a Windows overlay that hears the interviewer and
resurfaces a sentence you already wrote. It never writes anything itself. That is a deliberate,
architecturally enforced guarantee, not a shortcut.

v2 keeps that and adds a second job. The app becomes an **interview copilot**:

1. **A workspace.** You create a company you applied to. Everything about that application lives
   inside it: the job ad, your resume, company research, interviewer notes, prep notes, and every
   interview you ran against it, transcripts included.
2. **A suggester.** When the interviewer asks something, the app can also propose a tailored
   answer, built from your resume, the job ad, and what has already been said in this interview.
   Not a generic answer. This specific answer, for this question, in this conversation.
3. **A copilot, not a lookup.** It watches the whole conversation, not just the last sentence, and
   raises things on its own: a job-ad requirement you have not evidenced, a story you prepared and
   have not used, a contradiction against your own resume, a question worth asking back.

The comparison points, stated plainly because they set the bar:

| Reference | What we take from it | What we do not take |
|---|---|---|
| Granola | External listener, no bot joins the call, no video, works with any meeting app | Its post-hoc note-taking focus |
| Contact-centre agent assist | Proactive analysis, next-best-action, surfacing before you ask | Its supervisor and QA tooling |
| Claude / ChatGPT Projects | A named container that owns files and conversations | Chat as the primary surface |

---

## 2. What already exists

This matters more than usual, because a large amount of what the request describes is already
written, tested, and in the repository. Accurate as of `3c8485c`.

### 2.1 Built and passing tests

| Capability | Where | Note |
|---|---|---|
| Platform-agnostic audio capture | `audio/capture.py` | WASAPI loopback + mic, bounded 3 s queue. No meeting-app integration, by design |
| Pluggable streaming STT | `stt/` | Local `faster-whisper`, Deepgram, ElevenLabs behind one Protocol, with a conformance suite |
| Utterance assembly | `stt/assembler.py` | Finalised spans, silence-terminated |
| Two-stage matching | `matching/` | Local MiniLM prefilter, then a forced-tool Claude selector |
| Five typed context sources | `notes/model.py` | `COMPANY`, `ROLE` (the job ad), `INTERVIEWER`, `PREP`, `RESUME` |
| Multiple named context sets | `notes/store.py` | Atomic write, 5-deep backup rotation, schema migration v1 to v2 |
| Overlay | `ui/overlay.py` | Frameless, always-on-top, drag, resize, opacity, brightness, lock, capture-excluded |
| Progress checklist | `tracker/progress.py` | Marks prepared points as covered, from your mic only, with echo suppression |
| Encrypted transcript store | `report/store.py`, `platform/win_dpapi.py` | DPAPI, per-session, 30-day retention default |
| Post-interview report | `report/` | Four rubric dimensions, every finding must cite its utterance |
| Session state machine | `session/manager.py` | Explicit states, health as an orthogonal attribute |
| Diagnostics ring | `diagnostics/ring.py` | Structural events only, field allowlist, never transcript |
| Design system | `docs/prism-design-system.md` | PRISM, hand-implemented in the Qt chrome |

**560 tests pass.** A further 12 Qt modules need a display and run on Windows CI.

### 2.2 Not built

| Gap | Evidence |
|---|---|
| **The app does not start** | `__main__.py:83` `_build_application` raises `NotImplementedError` on purpose (T9.6a) |
| No real embedding model | `notes/index.py` defines an `Embedder` Protocol; no implementation exists |
| Audio capture never validated on Windows | M1 blockers in `06-progress.md`; D-68 records that an idle loopback endpoint emits no callbacks at all |
| No packaging | T9.4 PyInstaller build not done. No installer, no signing, no update path |
| No first-run setup wizard | T9.3 |
| No company or project container | Context sets are flat and unnamed above set level |
| Sessions are not linked to anything | `report/store.py` keys sessions by session id only |
| No PDF or DOCX ingest | `notes/importer.py` handles `.txt` and `.md` |
| No generated text anywhere live | Forbidden by FR10, FR42, FR79 and D-5 |
| No proactive behaviour of any kind | The pipeline is strictly request-response per utterance |
| No calendar or meeting-platform integration | Confirmed absent across the tree |

### 2.3 Already delivered, contrary to the request

The request lists post-interview scoring as a future roadmap item. **It shipped in M11.**
`report/generator.py` produces prep coverage, job-description fit, resume utilisation and interview
craft, plus what went well and what to do differently, and rejects any finding that cannot cite the
utterance it rests on (FR78, FR31). It is descriptive with evidence, not a single score.

**Decision: keep as built.** It is removed from the roadmap and extended only to cover the new
suggestion lane (FR106).

---

## 3. Decisions

Continuing the log in `docs/implementation/00-decisions-and-assumptions.md`. D-U13 is the last
existing entry.

| ID | Decision | Consequence |
|---|---|---|
| **D-U14** | **Two lanes on the overlay: recall and suggest.** Recall keeps the verbatim guarantee unchanged. Suggest is generated, always visually distinct, and can be switched off. | Reverses D-5 and FR42 for the suggest lane only. FR79's separation stays: a report still cannot reach the overlay. |
| **D-U15** | **Windows first. A platform abstraction layer lands before macOS is attempted.** | D-U4 stands for v2. `platform/` gains a Protocol seam per capability so macOS is a port, not a rewrite. No macOS code in v2. |
| **D-U16** | **`Company` is a new container above `ContextSet`.** It owns structured fields, many context sets, and many interview sessions. | Schema v3 and a migration. `report/store.py` gains a company key. |
| **D-U17** | **Meeting data is entered by hand in v2.** No calendar OAuth, no Meet API. | The Google Meet integration in the request is deferred whole. Audio capture already works with every meeting app, which is the part that matters. |
| **D-U18** | **PDF and DOCX are accepted at import.** | Reverses D-U1's deferral of `.docx`. Adds a layout-free chunking strategy, because neither format carries the header structure the current splitter needs. |
| **D-U19** | **Proactive assistance is scoped to three behaviours**: next-best-action, gap and risk alerts, and a rolling conversation state. **No live web or company search during an interview.** | Keeps the in-interview network surface to exactly the calls already accounted for. Live search is deferred. |
| **D-U20** | **Bring your own Anthropic key.** No hosted backend, no accounts, no billing. | Confirms D-U12's local-first startup. The key is optional: without it the app still captures, transcribes, matches on the prefilter and recalls. Suggest, report and stage-2 selection need it. |
| **D-U21** | **PRISM stays. The app shell is rebuilt around it.** | The main window becomes a workspace, not a settings panel. The overlay's D-U7 neutral-gray exemption is unchanged. |
| **D-U22** | **The composition root is finished before any v2 feature is built.** | The app must launch before it grows. Sequencing in §8 follows from this and nothing may jump the queue. |

---

## 4. New functional requirements

Numbering starts at FR90. FR1 to FR87 are taken.

### 4.1 Company workspace

| ID | Requirement |
|---|---|
| **FR90** | A **Company** is a named, persisted container created by the user. It owns structured fields, source files, context sets and interview sessions. Deleting a company deletes everything it owns, after one confirmation that names the counts. |
| **FR91** | A company carries structured fields, each optional: display name, careers or website URL, LinkedIn URL, role title, application date, status, free-text notes. URLs are stored and displayed only. Nothing fetches them (D-U19). |
| **FR92** | A company owns **one or more context sets**. A set is the context for one interview round. A new set may be seeded by copying an existing set in the same company, so round two does not start empty. |
| **FR93** | The **resume is user-level, not company-level.** It is imported once and referenced by every company. A company may override it with a tailored version. The override, not the shared copy, is what a session is graded against (D-58 applies unchanged). |
| **FR94** | Every saved session is filed under exactly one company and one context set. The session list is filterable by company. Existing unfiled sessions from v1 migrate to a single `Unfiled` company. |
| **FR95** | A session may carry meeting metadata entered before it starts: title, scheduled time, and named participants with optional role and LinkedIn URL. Participants are written into the context set as `INTERVIEWER` chunks, so they reach matching through the path that already exists. |

### 4.2 Ingestion

| ID | Requirement |
|---|---|
| **FR96** | Import accepts `.pdf` and `.docx` in addition to `.txt` and `.md`. Extraction is text-only. Images, and text recoverable only by OCR, are not extracted. |
| **FR97** | When a document carries no usable heading structure, a **semantic chunking strategy** is offered alongside the existing three. It is named and switchable before saving, exactly like the others (T3.7a), and every chunk stays editable before it is written. |
| **FR98** | A file that yields no extractable text is **rejected with the reason at import**, never saved as an empty or partial source. A PDF of scanned images is the expected case and must say so. |

### 4.3 The suggest lane

| ID | Requirement |
|---|---|
| **FR99** | On an interviewer utterance the app may render a **generated suggested answer** in a lane that is visually distinct from the recall lane at a glance, without reading the text. |
| **FR100** | The suggestion is generated from: the utterance, the rolling conversation state (FR103), the matched context chunks, the job ad, and the resume. It carries the ids of the sources it drew on, and the overlay shows them. |
| **FR101** | The suggest lane is **off by default** and is enabled per company. Enabling it requires a one-time acknowledgement that generated text is being shown, and that it is not something you wrote. This is a separate acknowledgement from FR63 and FR85, for the same reason FR85 is separate. |
| **FR102** | With no API key, on API failure, or on timeout, the suggest lane **renders nothing and says why in one line.** It never falls back to unmarked recall text, and the recall lane is unaffected. This mirrors D-U3's degraded rule rather than inventing a second one. |

### 4.4 Proactive assistance

| ID | Requirement |
|---|---|
| **FR103** | The app maintains a **rolling conversation state** for the live session: topics covered, questions asked, points made, time elapsed. It is in-memory session state, updates on each finalised utterance from either stream, and dies with the session unless the report feature is on, in which case it follows FR74's record. |
| **FR104** | The app raises **next-best-action prompts** unprompted: a prepared point not yet used, a question worth asking back, a job-ad requirement not yet evidenced. Each carries the source chunk it came from. Rate-limited, and never while the interviewer is speaking. |
| **FR105** | The app raises **gap and risk alerts**: a job-ad requirement just raised with no matching evidence in your sources, a statement that contradicts a `RESUME` chunk, a single answer running long. Each alert names the chunk or utterance that triggered it. An alert that cannot cite one is not shown, on the FR78 principle. |
| **FR106** | The post-interview report gains a **fifth section covering the suggest lane**: what was suggested, what you used, what you ignored. Same evidence rule as the other four. It is omitted, not faked, when the lane was off. |

### 4.5 Product surface

| ID | Requirement |
|---|---|
| **FR107** | The main window is a **workspace**: companies on the left, the selected company's sources and interviews in the middle, session controls always reachable. Settings, reports and diagnostics move out of the top level and into the shell. |
| **FR108** | A **first-run wizard** covers, in order: the FR63 disclosure, STT model choice and download (D-U13), audio device selection and test, optional API key entry, and resume import. It is skippable at every step after the disclosure and resumable later. |
| **FR109** | The app ships as a **signed Windows installer** that installs, launches, and uninstalls cleanly without a Python toolchain on the machine. |
| **FR110** | **Platform-specific capabilities sit behind Protocols**: audio capture, credential storage, at-rest encryption, screen-capture exclusion, crash reporting. Windows is the only implementation in v2. There is exactly one place to add a second (D-U15). |

---

## 5. Non-goals for v2

Named so they do not creep in.

- **No macOS or Linux build.** The seam is built (FR110). No second implementation.
- **No calendar, Zoom, Teams or Meet integration** (D-U17).
- **No live web search during an interview** (D-U19).
- **No hosted backend, accounts, or billing** (D-U20).
- **No video capture, ever.** Audio only. This is not a scope call, it is what the product is.
- **No speaker diarization.** Stream separation plus echo detection stands (D-8, AS-5).
- **No use in someone else's interview.** Unchanged from the original non-goals.
- **No single overall interview score.** The report stays descriptive with evidence.

---

## 6. Data model

### 6.1 Shape

```
User
├── resume (shared, RESUME chunks)                     FR93
└── Company                                            FR90
    ├── fields: name, url, linkedin, role, applied, status, notes   FR91
    ├── resume override (optional)                     FR93
    ├── ContextSet[]   one per interview round         FR92
    │   └── Note[] carrying SourceKind                 unchanged
    └── Session[]                                      FR94
        ├── meeting metadata                           FR95
        ├── encrypted transcript                       unchanged
        └── report                                     unchanged
```

### 6.2 Migration, v2 to v3

The existing store already does versioned forward-only migration with backup rotation
(`notes/store.py`), so this follows a path that exists rather than inventing one.

1. Every current context set becomes its own company, named from the set.
2. Every unfiled session joins a company named `Unfiled`.
3. `RESUME` chunks are **copied**, not moved, to the user-level resume. The company keeps its copy
   as an override, because a v1 user may well have tailored it. Nothing is lost by guessing wrong.
4. The v2 file is retained as a backup, as v1 to v2 already does.

**Note ids are preserved.** Embedding caches are keyed on note id and content hash, so a migration
that renumbers ids silently invalidates every cached vector.

---

## 7. Architecture changes

| Area | Change | Risk |
|---|---|---|
| `matching/` | A third stage, `Suggester`, runs beside the selector, not inside it. Unconstrained output, unlike the selector. | Must not be able to write into the recall lane's render path. Enforce structurally, the way `report/separation.py` already enforces FR79. |
| `session/` | Owns `ConversationState` (FR103). Feeds the suggester, the proactive engine and the report. | It is the first component holding both streams' meaning rather than their text. Purge must clear it; add it to the purge hook list. |
| new `proactive/` | Detectors for FR104 and FR105. Each returns a prompt with a citation or returns nothing. | Rate limiting and the never-interrupt rule live here, not in the UI. |
| `notes/importer.py` | Two extractors and one chunking strategy. | PDF extraction quality varies wildly. FR98 is the guard. |
| `notes/model.py`, `store.py` | `Company` entity, schema v3. | Touches every store test. Do it before features, not after. |
| `report/store.py` | Sessions key on company. | Migration only. |
| `platform/` | Protocol per capability (FR110). | Pure refactor. Should not change behaviour, and the tests should prove it did not. |
| `ui/` | New shell (FR107), wizard (FR108), company editor, suggest lane, proactive tray. | Largest single block of work in v2. |
| `__main__.py` | Finish `_build_application`. Real embedder. No-API-key policy. | Blocks everything. |

---

## 8. Sequencing

One pull request per block. Each must leave the app runnable and CI green.

| PR | Contents | Why here |
|---|---|---|
| **1. Make it run** | Finish `_build_application`, real sentence-transformers embedder, no-API-key policy, first-run wizard (FR108). | D-U22. Nothing else is testable by a human until this lands. |
| **2. Windows reality** | Validate M1 audio capture on real hardware, D-68 keep-alive, latency gate T2.4, device enumeration. | The core assumption of the whole product is still unverified on a real machine. |
| **3. Data model** | `Company` (FR90 to FR95), schema v3 migration, session filing. | Every later feature reads this model. Migrating twice is the avoidable cost. |
| **4. Ingestion** | PDF and DOCX (FR96 to FR98). | Independent. Unblocks realistic resume and job-ad content for the lanes below. |
| **5. App shell** | Workspace UI (FR107), company editor, PRISM applied. | Makes 3 and 4 usable. |
| **6. Conversation state** | FR103. | Prerequisite for 7 and 8 being tailored rather than per-question. |
| **7. Suggest lane** | FR99 to FR102, plus the structural separation guard. | The headline feature. Depends on 6. |
| **8. Proactive** | FR104, FR105, rate limiting. | Depends on 6 and 7's plumbing. |
| **9. Report extension** | FR106. | Depends on 7. |
| **10. Platform seam** | FR110 Protocols. | Pure refactor. Safest at the end, when behaviour is settled. |
| **11. Packaging** | FR109, signed installer. | Last. Packaging a moving target wastes the effort. |

---

## 9. Risks

| Risk | Why it is real | Mitigation |
|---|---|---|
| **The verbatim guarantee is the product's spine, and FR99 cuts into it** | Retrieval-only is enforced in four places and cited by dozens of tests. A generated lane is not an additive feature, it is a second, weaker contract living beside a strong one. | Two lanes, never merged, never able to render into each other's path, enforced the way FR79 already is. Generation off by default and per company. |
| **The Windows audio assumption is still unproven** | M1 has never run on the target machine. D-68 already found that an idle loopback endpoint delivers no callbacks at all, which breaks silence-based utterance finalisation. | PR 2 exists for this and nothing downstream of it should be trusted until it passes. |
| **Suggestion latency stacks on top of STT latency** | The budget is 2 to 3 seconds end to end. Local STT alone was estimated at 2 to 3 seconds and has never been measured on the target laptop. A generated answer is far more output tokens than a selector's enum. | Measure in PR 2 before designing PR 7's budget. Stream the suggestion. Consider a faster model for this lane specifically. |
| **Reading a generated answer on camera is visible** | Recall shows a bullet you wrote and already know. A generated paragraph must be read, and reading is obvious to the interviewer. | The suggest lane is bullets and fragments, never prose. Carry D-6's sentence-boundary discipline across. |
| **Proactive assistance competes with the interview for attention** | An alert that fires while you are thinking is worse than no alert. | FR104's never-while-they-are-speaking rule, hard rate limits, and a global mute. |
| **Ethics and disclosure get harder, not easier** | Recall is defensible: it is your own notes. A tailored generated answer is a different claim, and the original non-goals already ruled out using this in someone else's interview. | FR101's separate acknowledgement must say plainly what the lane does. Do not soften it. |
| **PDF extraction quality is unpredictable** | Multi-column resumes and design-heavy templates extract as interleaved nonsense. Bad chunks poison the index silently. | FR98 rejects empties. The FR97 review step is mandatory, not skippable. |
| **Scope** | Eleven pull requests, on a codebase that cannot currently start. | The sequencing is not negotiable at the top. PRs 1 and 2 come first. |

---

## 10. Open questions

| ID | Question | Blocks |
|---|---|---|
| **OQ-12** | Which model serves the suggest lane? The selector's Haiku is tuned for a one-token enum, not for drafting. | PR 7's latency and cost budget |
| **OQ-13** | Does the suggest lane need its own confidence floor, or does it inherit the prefilter's τ? | PR 7 |
| **OQ-14** | Is the shared resume (FR93) one document or a library of documents? | PR 3's schema |
| **OQ-15** | How does a proactive alert and a recall snippet share the overlay when both fire? | PR 8 |
| **OQ-16** | What signs the installer, and at what cost? | PR 11 |
