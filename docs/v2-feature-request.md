# v2 Feature Request — from recall tool to interview copilot

**Status:** Feature request. Not a build plan.
**Date:** 2026-09-14
**Revision:** 9. Each revision was reviewed against the codebase rather than against the progress
log. Revision 1 had eleven confirmed errors, revision 2 had ten. Revision 4 answers OQ-14 and
corrects two claims that `main` overtook. §11, §12 and §13 record every change, so the corrections
are not silently absorbed.
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

**573 tests pass** in the non-GUI subset. A further 12 Qt modules need a display and run on Windows CI.

### 2.2 Not built

| Gap | Evidence |
|---|---|
| No company-wide memory | Matching reads one `ContextSet`. `Prefilter.note_set` is singular, and `report/store.py` transcripts are never indexed at all |
| No transcript distillation | Transcripts are stored whole and read whole |
| Anthropic only | `platform/credentials.py` `KNOWN_ACCOUNTS` is `{deepgram, elevenlabs, anthropic}` |
| No prompt caching anywhere | Neither `matching/selector.py` nor `report/generator.py` sets `cache_control` |
| **No session can start** | T9.6a landed on `main` at `13df252`, so `_build_application` is real and the app now launches. But there is still no audio capture (M1) and no overlay wiring (M5), and `model_present` blocks a session until the weights exist. Launching is not running |
| **Screen-capture exclusion is a stub** | `platform/win_capture_exclusion.py` is a docstring saying "Not yet implemented". **FR14 and FR14a are v1 requirements and are not met.** The overlay is currently visible in a screen share |
| The embedder has never encoded anything | `notes/embedder.py` now implements the Protocol (T9.6a). AS-10 records that it has never loaded weights: `all-MiniLM-L6-v2` comes from huggingface.co, which the dev container answers 403 to. The adapter is written from documentation, not against the library |
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
| **D-U27** | **The resume library holds many named documents, and each one is a `ContextSet` stored through a second `NotesStore`.** | Answers OQ-14. A library document is a name plus a list of chunks, which is exactly `ContextSet`'s shape, so the library inherits atomic write, five-generation backup rotation, corrupt-file recovery and the migration hook without a line of new persistence code. `NotesStore.__init__` hardcodes `root / "notesets"`, so the only change is to make that subdirectory a parameter. |
| **D-U28** | **A copy into a context set mints fresh note ids and records its origin in `Note.tags`.** | `Note` and `ContextSet` are not touched (D-U24 holds). Fresh ids keep every copy independent, so editing the copy in one interview cannot reach another, and `validate_id`'s FR41 guarantee still holds. `tags` already exists and is already used by matching, so provenance costs no schema change. |
| **D-U29** | **Retrieval scope is the company, not the interview round.** Every context set the company owns is searched, plus its distilled transcripts. | The round-scoped design was wrong: interview 3 at a company could not recall interview 1. Implemented as a **union of the per-set indexes**, not one merged index — cache files are already per set, so editing round 2's notes re-embeds round 2 only. `Prefilter` takes a list of sets instead of one. |
| **D-U30** | **A past interview's transcript is conservatively distilled and indexed. The raw transcript is never discarded and never replaced.** | Distillation is additive and loss-averse: filler, false starts, repetition and backchannel go; every factual claim, name, number, commitment and question asked stays. Small details are kept on the assumption they may matter later. Raw stays encrypted and readable as it is today. |
| **D-U31** | **No Haiku for anything involving analysis.** Report generation, transcript distillation, the suggest lane and the proactive engine run on Sonnet 5 at high effort or Opus 5. | The stage-2 selector is the single exception, revisited once PR 2 measures latency: it picks one id from a closed enum of at most five and is the only call inside the live budget. Supporting fact: **Haiku 4.5 cannot take an `effort` parameter at all** — it still uses `budget_tokens` — which is itself evidence it is the wrong tool for the other four. |
| **D-U32** | **v2 is multi-provider.** `MessagesClient` generalises into a provider Protocol with an Anthropic implementation and an OpenAI implementation. | `credentials.py`'s `KNOWN_ACCOUNTS` gains `openai`. Model choice becomes per lane, not per app. Both providers can refuse a request, so a refusal path is required on both — OpenAI's strict mode explicitly does not suppress refusals. |
| **D-U33** | **FR10's guarantee is restated provider-agnostically: the selector's output must be constrained by the decoder, not by the prompt.** Two mechanisms are verified as satisfying it. | Anthropic: forced `tool_choice` with an enum schema. OpenAI: `strict: true`, which uses constrained decoding — after each token the engine masks invalid tokens to probability zero, so an invalid enum value cannot be produced. **A provider without such a mechanism may not host the selector**, because the guarantee would silently degrade into a prompt request. Note that forced tool use is *removed* on Claude Fable 5.1, which returns a 400, so that model would need the `strict` route instead. |
| **D-U34** | **The suggest lane caches its stable prefix at the default 5-minute TTL.** Never the 1-hour TTL. | Resume, job ad and company research are byte-identical for a whole interview; the utterance and conversation state go after the breakpoint. A cache read refreshes the timer for free and calls land roughly every 30 seconds, so the 5-minute entry stays warm for the session. The 1-hour TTL costs a 2× write and buys nothing here. |
| **D-U35** | **Adding the transcript kind bumps `ContextSet` to schema v3, with a no-op migration.** | **This amends D-U24.** That decision said note-set files stay at v2, and the *container* part of it holds — a company still is not stored in the note-set file. But a new `SourceKind` member is a schema concern: an older build reading a file containing it raises `NoteSetCorruptError` through `SourceKind(...)`. Bumping the version makes it raise `SchemaTooNewError` instead, which is the refusal the store already has for exactly this. |
| **D-U36** | **Provider and model are chosen per lane, and the STT choice is independent of every LLM choice.** Opus 5 for proactive work alongside Deepgram for transcription is a supported combination, not a special case. | STT already works this way: `SttBackend` is a Protocol with three implementations and an automatic fallback. This decision extends the same shape to the LLM lanes rather than inventing a second pattern. |
| **D-U37** | **The model list is fetched live from each provider and curated before it is shown.** Model ids are never hardcoded. | Extends D-9, which already made the Anthropic model id configuration rather than a constant. Anthropic's Models API returns id, display name, creation date and a `capabilities` field; OpenAI has an equivalent endpoint. A bundled list ships as the offline fallback, because D-U12 requires the app to start with no network. |
| **D-U38** | **There is no text-to-speech in this product.** | Recorded as a decision rather than an omission so it does not drift back in. The product listens and displays; it never emits audio. Any future audio output would be captured by the app's own loopback and mic streams, so it would need echo suppression against itself before it could be considered at all. |
| **D-U39** | **A catalogue refresh never changes a lane's saved model. Only the user does.** | FR134's fallback is therefore **runtime-only and never written to config**: a lane whose model is briefly unavailable falls back for that run, reports it, and resumes on the saved model when the provider serves it again. Writing the fallback to disk would turn a transient outage into a permanent silent downgrade. |
| **D-U40** | **The Anthropic floor is a per-family minimum, not a date cutoff: Opus 4.7 and later, Sonnet 4.5 and later.** | **A date cutoff would be wrong here.** Sonnet 4.5 was released before Opus 4.7, so any single date that admits Opus 4.7 excludes Sonnet 4.5, and any date that admits Sonnet 4.5 also admits Opus models the floor is meant to hide. The floor is expressed as one minimum per family, and a family the floor does not name is admitted on its own merits rather than blocked by default. |
| **D-U41** | **A newer model is signalled by a passive marker in the picker, and nowhere else.** No notification, no dialog, no badge, nothing outside the settings surface. | Answers OQ-24 and completes D-U39: if nothing auto-upgrades, the user needs a way to notice, and the quietest one that works is a mark beside the model they are already looking at. The marker never prompts and never preselects. |
| **D-U42** | **The floors, the per-lane model defaults and the distillation setting are all configuration, not constants.** They ship with defaults and the user may change every one. | Extends D-9, which already made the model id configuration. It also stops the floors going stale on the day a new generation ships: a floor written into the build is wrong the moment the world moves, and a floor in config is not. |
| **D-U43** | **One guarantee is not configurable: FR127's decode-time constraint on the selector.** Everything else in D-U42 may be overridden. | This is the line, and it is worth stating rather than assuming. Lowering a floor changes which models are *offered*; it must never change whether the selector's output is *constrained*. A setting that let the selector run on a model with no decode-time enforcement would turn FR10's structural guarantee into a prompt request, silently, with nothing on screen to say the product stopped being what it claims. FR124's preference against Haiku-tier models for analysis **is** overridable, because it is a quality preference. FR127 is not, because it is a correctness property. |
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
| **FR93** | A **resume library** exists at app-root scope and holds **many named documents** — a resume tailored per role, a work history, a cover letter, anything of kind `RESUME` (D-U27). Each is created, edited, renamed and deleted independently. The library is where you maintain them; a context set is what an interview is matched and graded against. |
| **FR115** | Creating or editing a context set **copies chosen library documents into it** (D-U25). Selection defaults to **the documents the most recent context set in the same company used**; a company's first set preselects nothing and requires an explicit choice. Copied chunks skip the FR97 import review, because they were reviewed when they entered the library. |
| **FR116** | A copied chunk carries a tag naming the library document it came from, so the overlay and the report can say which resume version a point came from (D-U28). Editing a library document **does not** retro-update sets that already copied from it: a past interview must stay graded against what you actually had (D-58). |
| **FR94** | Every saved session is filed under exactly one company and one context set. The session list filters by company. Sessions that exist before the backfill move to a company named `Unfiled`. |
| **FR95** | A session may carry meeting metadata entered beforehand: title, scheduled time, and named participants with optional role and LinkedIn URL. Participants are written into the context set as `INTERVIEWER` chunks, so they reach matching by the path that already exists. |
| **FR111** | Switching company is an explicit operation with the same guarantees as FR43's set switch: **refused while a session is running**. It rebuilds the four things `activate_context_set` rebuilds — the active `ContextSet`, `EmbeddingIndex.build()`, the prefilter's set reference, and the tracker's set reference plus its reset — and one new one, the session list's company filter (FR94). A company's **most recently used context set** becomes active; if it has none, the switch creates an empty one rather than leaving no active set. |

### 4.1a Company-wide memory

| ID | Requirement |
|---|---|
| **FR117** | **Retrieval is scoped to the company.** Matching searches every context set the company owns plus its distilled transcripts, not only the active set (D-U29). The active set decides what new material is written to; it does not narrow what can be recalled. |
| **FR118** | The index for a company is the **union of its per-set indexes**. Editing one set re-embeds that set alone. No merged index file is created, because `index/<set_id>.<model>.npz` is already the right granularity and a merged file would re-embed everything on every edit. |
| **FR119** | After an interview, its transcript is **conservatively distilled** into chunks and added to the company's retrieval scope (D-U30). Distillation removes filler, false starts, verbatim repetition and backchannel, and **nothing else**. Every factual claim, name, number, date, commitment, and question asked is retained. When in doubt the material is kept. |
| **FR120** | Each distilled chunk **cites the utterance indices it came from**, on the FR78 principle, so it can be audited against the raw record and the user can jump back to what was actually said. A chunk that cannot cite its source is not written. |
| **FR121a** | **Distillation aggressiveness is a user setting** (D-U42), on a scale whose **default is the most conservative** end: drop filler, false starts, verbatim repetition and backchannel, and nothing else. Raising it drops more, and the setting says plainly what each level gives up. Three properties hold at **every** level and are not part of the scale: every chunk still cites its utterances (FR120), the raw transcript is still never touched (FR121), and a chunk that cannot cite its source is still not written. The setting therefore cannot make the result unauditable, only shorter. |
| **FR121** | **The raw transcript is never modified, replaced or deleted by distillation.** It stays in the encrypted session store under its existing retention rule (FR84). Distillation is additive. |
| **FR122** | Distilled transcripts carry a new `SourceKind`, **`TRANSCRIPT`**, which is **not trackable** (FR70): things you said in a past interview are not talking points to cover in this one. Each past interview's distilled chunks are stored as their own read-only `ContextSet` in the company, named for the interview, so the existing store, index, prefilter and verify path all apply unchanged. |
| **FR123** | `TRANSCRIPT` gets its own `KIND_TAU_OFFSET` entry, set **above** the user's floor rather than below it. Transcript material is recall support, not prepared content, and should clear a higher bar before it displaces a prep note. D-30's cap of two stage-2 candidates per kind applies to it unchanged. |

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

### 4.4a Models and providers

| ID | Requirement |
|---|---|
| **FR124** | **Model is configured per lane, not per app.** Report generation, transcript distillation, the suggest lane and the proactive engine default to **Sonnet 5 at high effort, or Opus 5**, and the picker does not offer Haiku-tier models for them (D-U31). This is a **quality preference and is overridable** through FR132a's "show everything" path, with the trade stated at the point of choosing. Contrast FR127, which is not overridable (D-U43). |
| **FR125** | The **stage-2 selector** keeps a fast model as its default, as the single exception to FR124, and the exception is **time-boxed**: it is re-decided once PR 2 reports real end-to-end latency. It classifies against a closed enum of at most five candidates and is the only call inside the live 2-3 second budget. |
| **FR126** | **The model client is a provider Protocol** with an Anthropic implementation and an OpenAI implementation (D-U32). `KNOWN_ACCOUNTS` in `platform/credentials.py` gains `openai`. A key for either provider is optional and its absence degrades exactly as D-U12 already specifies. |
| **FR127** | **A provider may host the stage-2 selector only if it can constrain the output structurally at decode time** (D-U33). Two mechanisms are verified: Anthropic's forced `tool_choice` with an enum schema, and OpenAI's `strict: true`, which masks invalid tokens to zero probability so an invalid enum value cannot be emitted. Prompt-only instruction to "answer with one id" does **not** satisfy this and may not be used. |
| **FR128** | **Both providers can refuse a request**, and a refusal is not an error to swallow. The suggest lane treats a refusal as FR102's no-content case and states it in one line. The selector treats it as a stage-2 failure and falls back per D-U3. Note that OpenAI's strict mode constrains the schema but does **not** suppress refusals. |
| **FR129** | The suggest lane **caches its stable prefix** — resume, job ad, company research — at the default 5-minute TTL, with the utterance and conversation state placed after the cache breakpoint (D-U34). The app **verifies the cache is working** by checking that cached-read tokens are non-zero across a session, and records the result to the diagnostics ring; a silently cold cache is a cost bug that reports no error. |

### 4.4b Choosing providers and models

| ID | Requirement |
|---|---|
| **FR130** | **Every lane is assigned a provider and a model independently**: stage-2 selection, the suggest lane, the proactive engine, report generation, transcript distillation, and STT. Mixing is the expected case, not an edge case — for example Opus 5 for proactive suggestions and Deepgram for transcription. |
| **FR131** | The model list is **fetched live from each configured provider** and cached. When no provider key is present, or the fetch fails, the app falls back to a **bundled list** and says which it is showing. The app must remain usable offline (D-U12), so the picker never blocks startup. |
| **FR132** | The list is **curated before display**. Three rules: a **floor**, expressed as a minimum per model family rather than a cutoff date (D-U40); **non-conversational models are filtered out entirely**, because a provider's model endpoint also returns embedding, moderation and audio models that are not candidates for any lane here; and the remainder is sorted newest first. A **"show everything"** toggle reveals the unfiltered list for a user who wants a model the floor hides. |
| **FR132a** | The floors **ship as defaults and are user-editable** (D-U42), stored in `config.json` under the existing schema-versioned, forward-only migration. Shipped values: **OpenAI** — nothing before GPT-5. **Anthropic** — Opus 4.7 and later, Sonnet 4.5 and later. A family neither floor names is admitted and judged by FR133's per-lane rules. **STT providers carry no floor**: each serves a small number of current models, so a floor would filter nothing. Editing a floor changes which models are **offered** and never which constraints apply (D-U43). |
| **FR132b** | Each lane's **default model is a setting**, not a constant baked into the build (D-U42). The app still ships an opinion for first run, because something has to be selected before the user has chosen; changing the default never rewrites a lane the user has already set (D-U39). |
| **FR133** | A lane only offers models it can actually use. The **stage-2 selector** offers only models whose provider can constrain output at decode time for that model (FR127) — notably excluding any model where forced tool use has been withdrawn — and the **analysis lanes** exclude Haiku-tier models per FR124. A model the lane cannot use is not shown for that lane rather than shown and then rejected. **The selector's half of this filter survives every setting, including "show everything"** (D-U43): a floor is a preference, a decode-time guarantee is not. |
| **FR135** | The picker shows a **passive marker** beside a lane whose family has a newer model than the one saved (D-U41). It is informational: it never prompts, never preselects, and appears on no surface other than the picker. **It is suppressed while the bundled fallback list is in use** (FR131), because a stale list can as easily invent a newer model as miss one, and a marker that is sometimes wrong is worse than none. |
| **FR134** | **A configured model that is no longer served is a handled state, not a crash.** On a model-not-found error the app names the model, says it is unavailable, and falls back to that lane's default for that run, recording it to the diagnostics ring. **The saved configuration is not rewritten** (D-U39): if the model is served again, the lane resumes on it without the user touching anything. Only the user changes a lane's saved model. |

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
- **No text-to-speech, and no audio output of any kind** (D-U38).
- **No single overall interview score.** The report stays descriptive with evidence.

---

## 6. Data model

### 6.1 Shape

"App root" below is `%APPDATA%\InterviewPrepRecall`. This is a single-user desktop app. There is no
user identity, no tenancy and no isolation boundary, and none is being introduced.

```
App root
├── library/notesets/<uuid>.json   many named RESUME documents   FR93, D-U27
│                                   a ContextSet each, same store
├── companies/<uuid>.json        NEW STORE, own schema version  D-U24
│   └── fields, ordered context-set ids, last-used set id       FR91, FR111
├── notesets/<uuid>.json         schema v3 (one new SourceKind)  D-U35
│     ├── editable sets, one per interview round              FR92
│     └── read-only TRANSCRIPT sets, one per past interview   FR122
├── index/<uuid>.<model>.npz     UNCHANGED, caches survive
└── sessions/<id>.transcript     gains a company id             FR94
```

A company **references** context sets by id. It does not contain them. That is what lets the
existing note-set store, its atomic write, its backup rotation and its embedding cache carry on
untouched.

**Retrieval reads every set the company references** (FR117), as a union of their per-set index
files. A distilled transcript is just another set in that list, marked read-only and carrying
`TRANSCRIPT` chunks. That is the whole of the company-wide memory: no new store, no new index type,
no new retrieval path.

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
| `matching/prefilter.py` | Takes a **list** of context sets rather than one, and gains a `TRANSCRIPT` entry in `KIND_TAU_OFFSET` (FR117, FR123) | The union is the whole of D-U29's implementation. Resist adding a merged index |
| `matching/selector.py` | `MessagesClient` generalises into the provider Protocol (FR126). Anthropic and OpenAI implementations behind it | FR127 is the constraint that matters: a provider without decode-time enforcement may not host the selector |
| new distiller | Post-interview, offline, one call per interview. Reads the session record, writes a read-only `ContextSet` of `TRANSCRIPT` chunks | Loss-aversion is the whole specification (FR119). It is easier to write a distiller that summarises well than one that drops nothing important |
| `notes/model.py` | One new `SourceKind` member, and `SCHEMA_VERSION` to 3 with a no-op migration (D-U35) | This is the one place v2 touches `model.py`, and D-U24's "stays at v2" is amended rather than quietly broken |
| `platform/credentials.py` | `KNOWN_ACCOUNTS` gains `openai` | One line, but it is the seam the second provider hangs from |
| new model catalogue | Fetches and caches each provider's model list, applies FR132's curation, ships a bundled fallback | The curation is the substance. An uncurated provider listing includes embedding, moderation and audio models, which are not candidates for any lane here |
| `config.py` | A provider and model per lane (FR130), replacing the single `llm_model_id` | Forward-only migration, as the store already does. An old config names one model; the new one names six |
| `ui/settings.py` | Per-lane provider and model pickers beside the existing STT backend choice | The STT half of this already exists and should be the pattern the LLM half copies, not a second one |
| `report/separation.py` | Generalised from one hardcoded pair to a checkable rule, then given FR113's second pair | It is the only structural guarantee in the product. Changing it needs its own tests first |
| `session/` | Owns `ConversationState` (FR103), cleared by a sixth purge hook (FR112) | `PurgeHooks` is a frozen dataclass and `_purge` iterates a hardcoded tuple whose order is FR59. Both change together, and FR59's text changes with them |
| new `proactive/` | Detectors for FR104 and FR105. Each returns a cited prompt or nothing | Rate limiting and the never-interrupt rule live here, not in the UI |
| `tracker/` and mic routing | The mic stream gains a second consumer (D-U23) | D-10 said "exclusively". The amendment is explicit so a later reader does not read it as drift |
| `notes/importer.py` | Two extractors, one chunking strategy | PDF extraction quality varies wildly. FR98 is the guard |
| new company store | New module beside `notes/store.py`, reusing its atomic-write and rotation shape | Do not fold it into the note-set schema (D-U24) |
| resume library | **No new store.** A second `NotesStore` rooted at `library/`, which needs its subdirectory name to become a parameter instead of the hardcoded `"notesets"` | The one-line change is in a file whose durability guarantees the safety review called the highest risk in the product. Change it with its tests, not around them |
| `report/store.py` | Company id in the index, plus §6.3's backfill | Encrypted index. A failed read must stop, not rebuild |
| `app.py` | `activate_company` beside `activate_context_set` (FR111) | Must refuse mid-session, as FR43 already does for sets |
| `platform/win_capture_exclusion.py` | Implement it (FR114) | Currently a docstring. A v1 requirement, unmet |
| `platform/` | Protocol per capability (FR110) | Pure refactor. Tests should prove behaviour did not change |
| `ui/` | **`main_window.py` is rewritten into a workspace shell. Every other dialog is kept and embedded as a component** — `overlay.py`, `editor.py`, `report_view.py`, `settings.py`, `indicators.py`, `diagnostics_view.py`, `import_notes.py`, `restore.py`, `checklist.py`, `match_feed.py`. Plus the wizard (FR108), company editor, suggest panel and proactive tray | `ui/` is 5,741 of the app's 14,873 lines. Confining the rewrite to the one window that is currently a settings panel keeps the overlay's contrast sweeps, its geometry work and the PRISM tokens, and keeps their tests meaningful |
| `__main__.py` | Finish `_build_application`. Real embedder. No-API-key policy | Blocks everything |

---

## 8. Sequencing

One pull request per block. Each leaves the app runnable and CI green.

**Two of these cannot be finished by an agent.** Every row therefore splits the work. Sizes are
rough and are for ordering, not for planning.

| PR | Agent can do | Only you can do | Size |
|---|---|---|---|
| **1. Make it run** | ~~Composition root, no-API-key policy, embedder behind its Protocol~~ **Landed on `main` at `13df252` (T9.6a).** Remaining: the wizard (FR108) | **Run the first-launch model download** (huggingface.co is blocked here, AS-9 and AS-10) | S, was L |
| **2. Windows reality** | Latency harness, device-enumeration code, D-68 keep-alive wiring | **Run M1 on your Windows 11 machine with a real audio device.** Nothing downstream is trustworthy until this passes | M + hardware |
| **3. Capture exclusion** | `SetWindowDisplayAffinity` via ctypes (FR114, FR14, FR14a) | **Verify on a real screen share.** Headless cannot test this | S + hardware |
| **3b. UI shell decision** | — | Already taken: new shell, existing dialogs kept as components (§7) | — |
| **4. Company store** | New store, FR90 to FR92, FR111, FR117, FR118 company-wide retrieval, §6.2 backfill | — | L |
| **5. Session filing** | FR94, FR95, §6.3 record backfill | **Run the backfill.** Windows-only: `default_cipher()` raises elsewhere (D-40) | M + hardware |
| **6. Resume library** | FR93, FR115, FR116, the `NotesStore` subdirectory parameter, copy-into-set, library editor | — | M |
| **7. Ingestion** | PDF and DOCX, FR96 to FR98, multi-document import into the library | Supply real resumes and job ads as fixtures | M |
| **8. App shell** | Workspace UI (FR107), company editor, PRISM applied | Judge it at a glance, as with FR72's 1 m test | L |
| **9. Separation wall** | Generalise `separation.py`, add FR113's assertions, with tests first | — | S |
| **10. Conversation state** | FR103, FR112 sixth purge hook, FR59 amended | — | M |
| **11. Suggest lane** | `suggest/`, `ui/suggest_panel.py`, FR99 to FR102, FR129's caching and its cold-cache check | **Approve FR101's disclosure wording.** An ethics decision, not copy | L |
| | *Depends on PR 3 (FR114) **and** PR 2: OQ-12 and §9 both need PR 2's latency numbers before this lane's budget can be set* | | |
| **12. Proactive** | `proactive/`, FR104, FR105, D-U23 mic routing, rate limits | Judge whether the alerts help or intrude, live | L |
| **13. Report extension** | FR106, plus moving the report off Haiku per FR124 | **An API key.** T4.7 has never run against one | S |
| **16. Transcript distillation** | FR119 to FR123, the `TRANSCRIPT` kind, schema v3, the distiller | **Judge the output on a real transcript** (OQ-21). Only you can say whether it dropped something that mattered | M |
| **17. Provider abstraction** | FR126 to FR128, Anthropic and OpenAI implementations, refusal paths | **An OpenAI key** to verify the second implementation | M |
| **18. Model catalogue and picker** | FR130 to FR135, live fetch, curation, bundled fallback, per-lane assignment UI, editable floors and defaults (FR132a, FR132b), and the FR127 filter that survives them | Set the floors and defaults to taste once it runs | M |
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
| ~~**OQ-12**~~ | **RESOLVED 2026-09-14 by D-U42: it is a setting.** Sonnet 5 at high effort ships as the default; you change it. PR 2's latency numbers now inform the shipped default rather than block a decision | — | Answered |
| ~~**OQ-20**~~ | **RESOLVED 2026-09-14 by D-U42: it is a setting**, subject to FR133's filter, which is not (D-U43). PR 2 informs the default | — | Answered |
| ~~**OQ-21**~~ | **RESOLVED 2026-09-14 by D-U42: it is a setting** (FR121a), defaulting to the most conservative end. A real transcript now tunes a dial rather than settling a requirement | — | Answered |
| ~~**OQ-22**~~ | **RESOLVED 2026-09-14.** OpenAI: nothing before GPT-5. Anthropic: Opus 4.7 and later, Sonnet 4.5 and later, as per-family minimums (D-U40). STT providers: no floor. Became FR132a | — | Answered |
| ~~**OQ-23**~~ | **RESOLVED 2026-09-14: never.** A refresh never changes a saved model, and FR134's fallback is runtime-only (D-U39) | — | Answered |
| ~~**OQ-24**~~ | **RESOLVED 2026-09-14: a passive marker in the picker, no notification.** Became D-U41 and FR135 | — | Answered |
| **OQ-13** | Does the suggest lane need its own confidence floor, or does it inherit the prefilter's τ? | Design | PR 11 |
| ~~**OQ-14**~~ | **RESOLVED 2026-09-14: many documents.** Became D-U27, D-U28, FR93, FR115 and FR116 | — | Answered |
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

Line counts in this document are measured, not estimated. As of `13df252`: **14,873** lines under
`interview_prep_recall/`, **15,483** under `tests/`, across 36 test files, 573 passing in the
non-GUI subset.

---

## 13. What changed in revision 4

Two causes: OQ-14 was answered, and `main` moved underneath revision 3.

### OQ-14 answered: the resume library holds many documents

This was the cheap question with the expensive consequence, and the consequence turned out to be
cheaper than expected, because the shape already exists.

- **D-U27.** A library document is a name plus a list of chunks. That is exactly `ContextSet`, so
  the library is a second `NotesStore` rooted at `library/` rather than a new store. It inherits
  atomic write, five-generation backup rotation, corrupt-file recovery and the migration hook. The
  only code change is making `NotesStore`'s hardcoded `"notesets"` subdirectory a parameter.
- **D-U28.** A copy mints fresh note ids and records its origin in `Note.tags`. `tags` already
  exists and matching already reads it, so provenance needs no schema change and D-U24's promise
  that `Note` and `ContextSet` stay untouched still holds.
- **FR115** settles selection. Defaulting to *every* library document would be actively wrong once
  the library holds several tailored resumes: you would be matched against a version you did not
  send. So the default is what the company's most recent set used, and a company's first set
  preselects nothing.
- **FR116** settles the direction of change. Editing a library document does not reach back into
  sets that already copied from it, because D-58 grades a past interview against what you actually
  had at the time.

### Two claims `main` overtook

Revision 3 was written against `3c8485c`. `main` is now at `13df252`, and T9.6a landed in between.

| Claim in revision 3 | Now |
|---|---|
| "The app does not start. `__main__.py:83` raises `NotImplementedError` on purpose" | **`_build_application` is implemented and the app launches.** No session can start yet: no audio capture (M1), no overlay wiring (M5), and `model_present` blocks until the weights exist. Launching is not running |
| "No real embedding model. Only test fakes implement the Protocol" | **`notes/embedder.py` implements it.** AS-10 records that it has never loaded weights, for the same 403 as AS-9 |

PR 1's agent half is therefore done, and it is re-sized from L to S. The split in §8 held up: what
remains of PR 1 is the first-run download, which was already marked as yours.

The app could not be launched here to confirm, because PySide6 needs `libEGL` and this container
lacks it — the same reason the 12 Qt test modules do not run here. **Stated rather than claimed.**

---

## 14. What changed in revision 5

Two directives, and both reached further than they first appeared.

### "The bucket should hold everything, and be used in all future talks"

Revision 4 scoped retrieval to one interview round. **That was wrong**, and it is the kind of wrong
that only shows up on the third interview at a company, when nothing from the first two comes back.

- **D-U29, FR117, FR118.** Retrieval scope becomes the company. Implemented as a **union of the
  per-set indexes**, not a merged index, because the cache files are already one per set and merging
  them would re-embed everything whenever one note changes.
- **D-U30, FR119 to FR123.** Past transcripts are conservatively distilled and join the scope.
  **Loss-aversion is the specification**: filler, false starts, repetition and backchannel go, and
  nothing else does. Every claim, name, number, date, commitment and question stays, and when in
  doubt the material is kept. Each chunk cites the utterances it came from, so it can be audited
  against the raw record.
- **The raw transcript is never touched.** Distillation is additive (FR121).
- Distilled transcripts get their own kind so they cannot become talking points to "cover" (FR70's
  failure mode), their own threshold offset **above** the user's floor, and the per-kind cap of two
  stage-2 candidates that D-30 already enforces.
- **D-U35 amends D-U24.** A new `SourceKind` is a schema concern even though the company container
  is not: an older build reading the new member raises `NoteSetCorruptError`. Bumping `ContextSet`
  to v3 makes it raise `SchemaTooNewError`, which is the refusal the store already has for this.
  Revision 4 said note-set files stay at v2; the container half of that holds, the kind half does not.

### "No Haiku for anything involving thinking and analysis"

- **D-U31, FR124.** Report generation, transcript distillation, the suggest lane and the proactive
  engine run on Sonnet 5 at high effort or Opus 5. A supporting fact rather than a preference:
  **Haiku 4.5 cannot accept an `effort` parameter at all** — it still takes `budget_tokens`.
- **FR125.** The stage-2 selector is the one exception, and it is time-boxed rather than permanent.
  It classifies against a closed enum of at most five and is the only call inside the live budget.
  OQ-20 re-decides it on PR 2's measurements.

### Multi-provider, and the guarantee that had to survive it

- **D-U32, FR126.** `MessagesClient` generalises into a provider Protocol with Anthropic and OpenAI
  implementations. GPT-5.6 Sol and Terra were verified as real and current before designing against
  them.
- **D-U33, FR127.** FR10's anti-fabrication guarantee is restated provider-agnostically: **the
  output must be constrained at decode time, not by the prompt.** Two mechanisms verified as
  satisfying it — Anthropic's forced `tool_choice` with an enum, and OpenAI's `strict: true`, which
  masks invalid tokens to zero probability so an invalid enum value cannot be produced. A provider
  without such a mechanism may not host the selector.
- Worth knowing before anyone reaches for the newest model: **forced tool use is removed on Claude
  Fable 5.1**, which returns a 400. That model would have to take the `strict` route instead.
- **FR128.** Both providers can refuse, and OpenAI's strict mode explicitly does not suppress
  refusals, so a refusal path is required on both rather than assumed away.

### Caching

- **D-U34, FR129.** The suggest lane caches resume, job ad and company research at the **default
  5-minute TTL**, never the 1-hour one: a read refreshes the timer for free and calls land roughly
  every 30 seconds, so the short entry stays warm all session while the long one costs a 2× write
  for nothing. The app checks that cached reads are actually non-zero, because a cold cache raises
  no error and just quietly costs money.
- The stage-2 selector is **not** cached: its prefix is a few hundred tokens and changes every
  utterance. This is also where the Haiku floor bites — 4,096 tokens minimum to cache on Haiku 4.5
  against 1,024 on Sonnet 5 and 512 on Opus 5 — which is a second, independent argument for FR124.

---

## 15. What changed in revision 6

One clarification, and it turned out that a third of it was already built.

### Already built: STT provider choice

`stt/interface.py` defines `SttBackend` as a Protocol. `DeepgramBackend`, `ElevenLabsBackend` and
`LocalWhisperBackend` all implement it, `FallbackSttBackend` degrades automatically when a cloud
backend drops (FR21), a conformance suite lets a fourth backend inherit every test, and
`ui/settings.py` already offers the backend choice. FR17 and FR18 specified this in v1 and it
shipped. **Nothing to build; the work is to keep the LLM half consistent with it rather than
inventing a second pattern.**

### New: per-lane assignment

- **D-U36, FR130.** Provider and model are chosen per lane, and the STT choice is independent of
  every LLM choice. Opus 5 for proactive suggestions alongside Deepgram for transcription is an
  ordinary configuration, not a special case.
- `config.py`'s single `llm_model_id` becomes a provider and model per lane, through the
  forward-only migration the config store already has.

### New: a live, curated model catalogue

- **D-U37, FR131.** The list is fetched live. Anthropic's Models API returns id, display name,
  creation date and a `capabilities` field; OpenAI has an equivalent endpoint. A bundled list is the
  offline fallback, because D-U12 requires the app to start with no network, and the app says which
  list it is showing.
- **FR132.** Curation is the substance, not a nicety. A provider's raw model endpoint returns
  embedding, moderation and audio models alongside the conversational ones, so filtering is
  mandatory rather than cosmetic. Three rules: a per-provider floor (OpenAI: nothing before GPT-5),
  drop non-conversational models entirely, sort newest first. A "show everything" toggle exists for
  anyone who wants a model the floor hides.
- **FR133.** A lane only offers models it can use. The selector offers only models whose provider
  can constrain output at decode time for that model (FR127) — which excludes any model where forced
  tool use has been withdrawn — and the analysis lanes exclude Haiku-tier models (FR124). Filtering
  at the picker beats accepting a choice and then refusing it at runtime.
- **FR134.** A saved configuration outlives the model it names. A model that is no longer served is
  named, reported, and falls back to the lane's default rather than crashing.

### Settled: no text-to-speech

**D-U38.** Recorded as a decision rather than left as an omission. The product listens and displays;
it never emits audio. Worth writing down because any future audio output would be picked up by the
app's own loopback and mic capture and would need echo suppression against itself before it could
even be discussed.

---

## 16. What changed in revision 7

Two answers, and one of them exposed a trap worth writing down.

### A refresh never changes a saved model (D-U39)

Settled: **only the user changes a lane's model.** The consequence needed spelling out, because
FR134 as written could have quietly broken it. A model-not-found fallback is now **runtime-only and
never written to config**. A lane whose model is briefly unavailable falls back for that run, says
so, and **resumes on the saved model** once the provider serves it again.

Persisting that fallback would turn a transient outage into a permanent silent downgrade — the user
would come back to a lane running something they never chose, with nothing on screen to say when it
changed.

Follow-on question, OQ-24: since nothing auto-upgrades, the user needs some way to notice a newer
model exists. A passive marker in the picker is the cheap answer.

### The Anthropic floor is per family, not a date (D-U40, FR132a)

"Nothing older than Opus 4.7 or Sonnet 4.5" cannot be implemented as a cutoff date, and the reason
is worth recording so nobody simplifies it later:

**Sonnet 4.5 was released before Opus 4.7.** So any single date that admits Opus 4.7 also excludes
Sonnet 4.5, and any date that admits Sonnet 4.5 also admits the Opus models the floor exists to
hide. A date cutoff gets this wrong in both directions at once.

The floor is therefore one minimum per family:

| Provider | Floor |
|---|---|
| OpenAI | Nothing before GPT-5 |
| Anthropic | Opus 4.7 and later; Sonnet 4.5 and later |
| A family neither names | Admitted, then judged by FR133's per-lane rules |
| STT providers | No floor — each serves a small number of current models, so a floor would filter nothing |

FR133 still applies on top: the selector lane hides any model whose provider cannot constrain output
at decode time for it, and the analysis lanes hide Haiku-tier models per FR124. The floor decides
what is old; FR133 decides what a given lane can actually use.

---

## 17. What changed in revision 8

OQ-24 answered: **a passive marker in the picker, and nothing else.** No notification, no dialog, no
badge, no surface outside settings. It informs; it never prompts and never preselects (D-U41,
FR135).

One condition on it. **The marker is suppressed while the bundled fallback list is in use.** An
offline or stale list can invent a newer model as easily as it can miss one, and a marker that is
sometimes wrong is worse than no marker — it would teach the user to ignore the one signal the
design gives them.

That closes every open question raised in this document except the three that need measurement:
OQ-12 and OQ-20 wait on PR 2's latency numbers, and OQ-21 waits on a real transcript.

---

## 18. What changed in revision 9

The floors, the per-lane model defaults and the distillation setting all become configuration
(D-U42). They ship with defaults and you change any of them, stored in `config.json` under the
schema-versioned, forward-only migration the config store already has.

This closes three open questions by turning them from decisions the plan had to make into settings
you adjust. **PR 2's latency numbers now inform a shipped default rather than block a requirement**,
which is a better place for them to sit: a measurement should tune a dial, not gate a document.

### The one thing that is not configurable

**D-U43 draws the line, and it is worth stating rather than assuming.**

Lowering a floor changes which models are **offered**. It must never change whether the selector's
output is **constrained**. A setting that let the stage-2 selector run on a model with no
decode-time enforcement would turn FR10's structural guarantee into a prompt request — silently,
with nothing on screen to say the product had stopped being what it claims.

So the two look similar and are not:

| Rule | Kind | Overridable |
|---|---|---|
| Model floors (FR132a) | Preference about age | **Yes** |
| No Haiku-tier for analysis (FR124) | Preference about quality | **Yes**, with the trade stated |
| Per-lane defaults (FR132b) | Preference about starting point | **Yes** |
| Distillation aggressiveness (FR121a) | Preference about compression | **Yes** |
| Decode-time constraint on the selector (FR127) | **Correctness property** | **No** |

The distillation setting has the same shape internally. Three things hold at every level of the
scale and are not part of it: every chunk cites its utterances, the raw transcript is never touched,
and an uncitable chunk is never written. **The setting can make the result shorter. It cannot make
it unauditable.**
