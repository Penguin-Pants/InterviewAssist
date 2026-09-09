# Handy — external reference review

**Reviewed:** 2026-09-09, against `github.com/cjpais/handy` at 836 commits (last commit 2026-09-08).
**Why:** [Handy](https://github.com/cjpais/handy) is an actively maintained, shipping, open-source
local-only dictation app (a Wispr Flow / Superwhisper alternative). It has already solved the
problem D-U12 just committed us to — a product that works at startup with no account, no key and
no network — so its choices are worth reading before we write `_build_application`.

**Read this as evidence, not as a plan.** Nothing here is a decision. The two decisions it feeds
are OQ-10 and OQ-11 in `implementation/00-decisions-and-assumptions.md`.

---

## 0. What it is, and the one thing it is not

Tauri 2.11.5 desktop app: Rust backend, React/Vite/Tailwind frontend. Push-to-talk dictation —
the user holds a hotkey, speaks, and the transcript is typed into whatever app has focus.

**It captures the microphone only. There is no loopback or system-audio capture anywhere in it**
(`grep -i loopback` across the repo returns nothing functional; `list_output_devices()` in
`src-tauri/src/audio_toolkit/audio/device.rs` enumerates outputs only for muting and for playing
audio cues, and is never passed to `build_input_stream`).

That halves its usefulness to us. D-U2 makes both streams mandatory, and the interviewer's audio
is the harder half — it is where D-68 (an idle WASAPI loopback endpoint delivers *no callbacks*,
not frames of silence) lives. **Handy offers us nothing on loopback. That work stays ours.**

## 1. Licensing — reusable

MIT (`LICENSE:1-3`, `src-tauri/Cargo.toml:9`). No GPL anywhere in the crate or its stated
dependencies. Code and design may be reused in this project, including a literal translation to
Python, provided the copyright notice and licence text travel with any substantial portion.

Two caveats before copying anything wholesale:

- Several dependencies are **forks pulled from git rather than crates.io** (`hf-hub`, `rodio`,
  `tao`, `vad-rs`, `tauri-nspanel`). Upstreams are MIT/Apache-2.0, so the risk is low, but each
  wants its own check if we lift code that came from them.
- **Model weights are separately licensed and are not covered by the app's MIT.** The repo states
  no licence for the weights it serves. Whisper's are MIT upstream; Parakeet, Canary and GigaAM
  are NVIDIA-licensed. Any weight we bundle into our installer needs its own licence check.

## 2. Their STT stack, for reference

Two inference paths (`src-tauri/Cargo.toml:75-80`):

- `transcribe-cpp 0.2.0` — whisper.cpp/ggml, for the Whisper family (GGUF/ggml files).
- `transcribe-rs 0.3.8` with `features = ["onnx"]` — ONNX Runtime, for Parakeet, Moonshine,
  SenseVoice, GigaAM, Canary, Cohere.

Their **recommended default is Parakeet V3** (`parakeet-tdt-0.6b-v3-int8`,
`src-tauri/src/managers/model.rs:787`), not Whisper. Catalog spans Whisper Small (465 MB),
Whisper Medium q4_1 (469 MB), Whisper Turbo (1549 MB), Whisper Large q5_0 (1031 MB), and the
int8 ONNX models (`model.rs:557-1099`).

Acceleration: Metal on macOS, Vulkan plus per-ISA dynamic backends on Windows x64, CPU-only
static on Windows ARM64 (immature Adreno Vulkan drivers). **The ONNX path is CPU-only on every
platform**, and DirectML was explicitly rejected because it "crashes at process startup on any
pre-Haswell CPU" (`Cargo.toml:101-110`).

## 3. Model acquisition — the most useful part, and it feeds OQ-11

**Correction, 2026-09-09.** An earlier revision of this section said Handy does not depend on
Hugging Face at runtime, and that every entry points at `blob.handy.computer`. That was wrong at
current HEAD. Verified directly against the catalog rather than taken from a summary:

- **Hugging Face is the primary source, pinned to a commit.** Catalog entries carry an `id` that
  is an HF repo (`handy-computer/parakeet-unified-en-0.6b-gguf`) plus a `revision` pinned to a
  full git SHA. `ModelSource::HuggingFace { repo_id, revision }` (`managers/model.rs:44-58`)
  fetches through a forked `hf-hub` into the shared HF cache, so other tools on the machine
  reuse the same weights.
- **Their own host is the mirror, not the origin.** `catalog.json`'s top-level
  `"mirrors": ["https://blob.handy.computer"]`, consumed by
  `catalog::mirror_fallbacks(model_id) -> Vec<MirrorFile>` (`catalog/mod.rs:143`). HF is tried
  with 4 retries first, then the mirrors; the failure message is literally "Download failed from
  Hugging Face (…) and N mirror(s)" (`model.rs:2110-2116`). `ModelSource::Url` still exists and
  its doc comment calls it "current blob.handy.computer hosting", so both routes are live.
- **A test enforces that the mirror is always usable:**
  `every_catalog_model_has_mirror_fallbacks_with_hashes` (`catalog/mod.rs:253`).

That is a better design than the one I first described, and the three properties are separable:
**reproducibility** from the pinned HF revision, **integrity** from per-file SHA-256, and
**availability** from a mirror they control. Note also that each catalog entry carries a
`license` field, which is how they keep per-model weight licensing straight.

The catalog itself needs no network: `include_str!("catalog.json")` compiles it into the binary,
with the stated reason that "Handy ships a complete model list with zero network access"
(`catalog/mod.rs:1-7`, `:118`). So the picker and its explanations render offline; only the
weights need connectivity.

Their downloader (`src-tauri/src/managers/model/download.rs`) is worth copying as a design:

| Property | How | Line |
|---|---|---|
| Resumable | HTTP `Range: bytes=N-`, handling 206, 200-ignoring-range and 416 | `download.rs:186-215` |
| Integrity | SHA-256 pinned **per quantisation file**, not per model; partial deleted on mismatch | `download.rs:64-72` |
| Cheap re-check | a `.partial` already at the expected size is SHA-verified rather than re-downloaded | `download.rs:189-198` |
| Never hangs | `DOWNLOAD_STALL_TIMEOUT = 60s`; no data for 60 s aborts, keeping the partial for resume | `download.rs:26` |
| Cancel is non-destructive | cancelling flips a token and **keeps** the partial; only a hash mismatch deletes | `model.rs:2129`, `:2557-2589` |
| Escape hatch | verification skipped when `sha256` is `None` (user's own custom models) | `download.rs:55` |
| Failure is recoverable | a `DownloadCleanup` RAII guard resets `is_downloading`, the card reverts to "downloadable", and the user can retry indefinitely without restarting | `model.rs:505-517` |

**One weakness worth not copying.** On a later launch, "is this model present and valid?" is a
bare `model_path.exists()` (`model.rs:1439`). Content is SHA-verified only at the moment a
download completes, so corruption *after* that point is never detected. For us the same shortcut
would surface as an unexplained transcription failure mid-interview, which is the worst possible
place to discover it. Verify on load, or at least record the verified hash and re-check cheaply.

**A measured caution before we assume this solves our blocker.** It does not solve it *here*. I
tested this container's proxy on 2026-09-09:

```
huggingface.co        CONNECT tunnel failed, 403
blob.handy.computer   CONNECT tunnel failed, 403
api.anthropic.com     405   (i.e. reachable)
```

The proxy is an allowlist, not a Hugging Face block, so **adding a mirror we control changes
nothing about local development or CI** — neither host is reachable from here. Its value is for
shipped users, where it removes Hugging Face as a single point of failure. AS-9 stays blocked in
this container either way. Keep testing against doubles here and verify on the Windows target
machine, exactly as `06-progress.md` already prescribes.

### The bundle/fetch split, confirmed

This is the direct answer to OQ-11, and Handy splits it by size and by whether the user gets a
choice:

- **Bundled at build time:** `resources/models/silero_vad_v4.onnx`, 1.8 MB, git-tracked, shipped
  via `tauri.conf.json:30` (`"resources": ["resources/**/*"]`) and loaded through
  `BaseDirectory::Resource` (`managers/audio.rs:287-292`). Never downloaded at runtime.
  `BUILD.md:121` treats it as a build prerequisite. The `curl` in `AGENTS.md:45-47` is a
  developer bootstrap step, not an end-user path.
- **Fetched at runtime:** all 69 STT catalog entries, always, into the models dir. No STT model
  ships in the installer, and `default_settings.json` has no `selected_model`.

Mandatory and small is bundled. Large and chosen is downloaded. That is the shape to copy.

### The cheaper half of OQ-11, already available to us

`faster-whisper`'s `WhisperModel.__init__` accepts both `download_root` and `local_files_only`
(verified by introspection on 2026-09-09 against the installed package, not read from docs):

```
model_size_or_path, device='auto', device_index=0, compute_type='default',
cpu_threads=0, num_workers=1, download_root=None, local_files_only=False,
files=None, revision=None, use_auth_token=None, model_kwargs
```

`FasterWhisperTranscriber` (`stt/local_whisper.py:151-178`) passes neither today, which is why a
first launch with no network fails inside `_ensure_model()`. **A configurable model directory plus
`local_files_only=True` makes the existing adapter offline-capable with no library swap, no new
runtime, and no change to the `Transcriber` Protocol the tests are built on.** That is a much
smaller move than adopting whisper.cpp, and it should be tried first.

## 4. What to take, ranked

1. **Bundle Silero v4 VAD instead of thresholding energy.** They run Silero v4 through ONNX
   (`resources/models/silero_vad_v4.onnx`, `vad/silero.rs`) at `SILERO_VAD_THRESHOLD = 0.3`
   (`managers/audio.rs:20`), with `earshot` as a WebRTC-style alternative at 0.5. The file is
   small enough to ship in the installer, so it costs no download and no network. Energy VAD is
   the weakest link in a pipeline whose whole job is knowing when a question ended.
2. **Add a pre-roll buffer.** `SmoothedVad` (`vad/smoothed.rs:56-92`) keeps a ring of buffered
   frames and, on confirmed speech onset, emits the buffered prefill *and* the current frame, so
   the attack of a word is never clipped. Their constants (`vad/mod.rs:5-8`) are a starting point:
   `VAD_PREFILL_MS 450`, `VAD_ONSET_MS 60`, `VAD_OFFLINE_HANGOVER_MS 450`,
   `VAD_STREAMING_HANGOVER_MS 1650`. Note they are expressed in **milliseconds and converted to
   frame counts per backend, rounding up**, so swapping VAD cannot silently shorten the tail.
3. **Do not force the capture device's sample rate.** They deliberately open at the device's
   native rate and resample in software, "to avoid forcing hardware into a non-native rate which
   can cause issues on some devices (Bluetooth codecs, certain ALSA drivers, etc.)"
   (`recorder.rs:470-523`). Worth confirming our capture does the same.
4. **A "capture is actually flowing" readiness handshake.** `RecordingReadiness`/`ready_tx`
   (`recorder.rs:22-26`, `:370-385`) exists because `stream.play()` returning does not mean audio
   is arriving — "some Bluetooth and USB devices take much longer to begin delivering callbacks."
   This is the same class of defect as **D-68**, found independently in a different product. Our
   keep-alive fixes the cause on loopback; a readiness signal would catch the symptom generally,
   including on the mic stream, and belongs with T1.4.
5. **Log a real-time factor after every transcription.** `speedup = audio_secs / elapsed_secs`,
   logged as "Xs for Ys of audio (Zx real-time)" (`managers/transcription.rs:1500-1509`). Nearly
   free, and it turns every session into a data point for the AS-1 / T2.4 latency gate.
6. **Keep the model resident, unload on an idle timeout.** A background thread checks every 10 s
   (`transcription.rs:302-370`), with an "unload immediately" option for memory-conscious users.
   Reloading a model mid-interview would blow the NFR1 budget outright.
7. **Contain failures around the engine, and fail open on text transforms.** Transcription runs
   inside `catch_unwind`, and on panic the engine is deliberately *not* returned to the pool
   (`transcription.rs:1292`, `:1425-1464`) rather than risk a poisoned engine. Separately, all
   output post-processing is wrapped so a bug in it "never discards the model's raw text"
   (`transcription.rs:1807-1825`). Both translate straight into Python.

### Their bug list is free QA for our M1 work

Each of these is a real defect they hit and fixed, in code we are about to write the equivalent of:

- **Command polling ordered after chunk processing dropped one buffer period of audio at every
  recording start** — ~10 ms built in, up to ~100 ms on Bluetooth (`recorder.rs:838-841`).
- **The block that first observes the stop flag must still be forwarded**, or up to a callback
  period of tail audio is lost (`recorder.rs:530-534`, with a dedicated test at `:667-697`).
- **The FFT resampler's delay line must be drained on finish** or the tail is truncated
  (`resampler.rs:97-120`), **and reset between sessions** or overlap from the previous recording
  leaks into the next (`resampler.rs:135-143`). Both unit-tested.
- **Windows microphone denial surfaces as HRESULT `0x80070005`** text from WASAPI, which they
  string-match to distinguish permission denial from device failure (`recorder.rs:593-598`).
- **A feature flag advertised by a model can still be rejected by it.** Non-Whisper architectures
  advertise `Feature::InitialPrompt` then reject the Whisper run extension with `INVALID_ARG`, so
  they gate on `arch() == "whisper"` rather than on the advertised capability
  (`transcription.rs:1232-1238`).

## 5. What does not transfer

- **Loopback capture.** Covered above. Nothing to take.
- **Rust and Tauri.** Design only, no code reuse. A port is not on the table against 1231 passing
  Python tests and a working PySide6 surface.
- **Their segmentation model.** Handy is hotkey-bounded: recording starts and stops on a keypress,
  VAD only filters which frames are kept, and there is **no max-duration force-cut anywhere**.
  We are always-on for the length of an interview, so we are VAD-bounded and our `max_span_s`
  force-cut is a requirement, not an inefficiency. Do not simplify toward their model.
- **Their queueing.** Audio rides an unbounded `mpsc` channel with no backpressure; a stalled
  consumer just grows the queue. Our drop-oldest backpressure is the right choice for a 60-minute
  session under NFR5's flat-memory requirement. We are ahead here.
- **Text injection.** `enigo` typing, six selectable paste methods, and a clever
  `WM_RENDERFORMAT`-based "reliable paste" that waits for the target app to consume the clipboard
  before restoring it (`paste_tx/mod.rs`, fixing their issue #502). We render to an overlay and
  inject nothing, so none of this applies — though it is the best writeup of that problem I have
  seen if we ever add a "copy this snippet" affordance.
- **Parakeet as our STT engine.** Faster and their default, but it means a second ML runtime.
  Our Whisper path is built and tested behind a Protocol. Revisit only if the AS-1 gate fails.

## 6. What it tells us about our open gates

- **AS-1 (local STT p95 < 900 ms inference tail, CPU-only).** Handy's *recommended default* is an
  int8 model on a CPU-only ONNX runtime, on every platform, and their users' baseline expectation
  is faster-than-real-time. That is real-world evidence that a CPU-only local default is a
  reasonable bet. It is not a measurement of our pipeline and does not substitute for T2.4.
- **NFR2 (runs without a discrete GPU).** Their DirectML rejection is a concrete warning: a GPU
  acceleration path that crashes at process start on older CPUs is worse than no GPU path. Reinforces
  measuring CPU-only first, per the D-U6 discipline.
- **OQ-1 (does stage 2 beat stage-1-only?).** D-U12 already makes stage-1-only the default
  experience for a keyless user. Handy's analogous feature — LLM post-processing of the transcript
  — is off by default, opt-in, and uses the user's own OpenAI-compatible `base_url`/`api_key`
  (`src-tauri/src/llm_client.rs`). Same shape as what D-U12 asks of us.

## 7. Product posture worth matching

Confirmed local-first with evidence, not just marketing: no account or login flow anywhere in
`src/` or `src-tauri/src`, and no telemetry, analytics or crash reporting library at all (no
Sentry, PostHog, Mixpanel or Amplitude). The only outbound paths are model downloads, an updater
gated behind a setting and overridable by `HANDY_DISABLE_UPDATER`, and the opt-in LLM
post-processing above. Their onboarding is `accessibility → model → done`, permissions are polled
rather than enforced behind a blocking modal, and a denial leaves the app running in a visibly
degraded state instead of refusing to start.

Two smaller things done well:

- **A failed subsystem falls back *and persists the fallback*,** so it does not retry the broken
  path every launch (`shortcut/mod.rs:38-51`).
- **A failed rebind restores the previous binding,** so "a failure leaves the user's shortcut
  working exactly as before" (`shortcut/mod.rs:200-230`).
