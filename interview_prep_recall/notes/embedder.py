"""The real `Embedder` (T9.6a — BC-1, D-U13, design §5).

`notes/index.py` has specified this Protocol since T3.6 and **nothing has ever
implemented it**. Every test supplies its own deterministic fake, which is the right
shape for testing similarity arithmetic and the wrong shape for shipping: with no
concrete embedder, `EmbeddingIndex.build` produced no vectors, `Prefilter.candidates`
returned `[]` for every utterance, and the overlay matched nothing — model or no model.
That is why T9.6a's blocker was never really "a model download".

**Unavailability is a state, not a crash.** D-U13 makes the weights a first-run download,
so "installed but not yet downloaded" is a configuration a user will genuinely be in.
`readiness()` is what preflight's `model_present` check asks, and `encode` raises
`EmbedderUnavailableError` rather than whatever the underlying library happens to throw,
so the caller has one thing to catch and the user gets one explanation.
"""

from __future__ import annotations

import importlib.util
from importlib.metadata import PackageNotFoundError, version
from typing import Any

import numpy as np

from interview_prep_recall.notes.index import DEFAULT_EMBED_MODEL_ID

DISTRIBUTION = "sentence-transformers"

VERSION_UNKNOWN = "absent"
"""`model_version` when the library is not installed.

Never keys a real cache: `encode` cannot succeed in that state, so no vectors are ever
written under it. It exists so `model_version` stays a plain attribute the index can read
before anything is loaded — and so installing the library later reads as a version change
and re-embeds, which is the safe direction of BC-1.
"""


class EmbedderUnavailableError(RuntimeError):
    """The embedding model cannot be loaded on this machine.

    Distinct from a bad result: matching is *unavailable*, not empty. `Prefilter` returns
    `[]` for "nothing is similar enough" (FR50), and a missing model reported the same way
    would be indistinguishable from a corpus that simply did not match.
    """


class SentenceTransformerEmbedder:
    """`sentence-transformers` behind `notes.index.Embedder`.

    **The user never chooses this model** (D-U13). `EmbeddingIndex` keys its cache on
    `embed_model_id` and `embed_model_version`, so a changed embedder invalidates every
    note's vectors and forces a full re-embed — an asymmetry with the Whisper model, which
    *is* a user choice, and the reason only one of the two is offered in the picker.
    """

    def __init__(self, model_id: str = DEFAULT_EMBED_MODEL_ID) -> None:
        self.model_id = model_id
        self.model_version = _distribution_version()
        """The installed library version, not the weights' revision.

        The weights are identified by `model_id`; what this adds is the encoder around
        them — pooling and normalisation defaults live in the library, and a change there
        shifts the vectors while the id stays identical. That is BC-1 exactly, and it is
        silent. Over-invalidating costs one re-embed; under-invalidating costs matching
        quality nobody can see.
        """
        self._model: Any | None = None
        self._failure: str | None = None

    def readiness(self) -> tuple[bool, str]:
        """Preflight's `model_present` probe. **Never touches the network.**

        Reports what this process can actually establish without a download: whether the
        library is importable, and whether a load already failed. A probe that answered
        "present" by *fetching* the model would turn a readiness check into a 90 MB
        transfer at startup — which is the first-run wizard's job (D-U13), with the user
        watching and able to cancel it.
        """
        if importlib.util.find_spec("sentence_transformers") is None:
            return False, "not_installed"
        if self._failure is not None:
            return False, self._failure
        return True, "ready"

    def encode(self, texts: list[str]) -> np.ndarray:
        """(n, d) float32. Unnormalised — `EmbeddingIndex` owns that (its Protocol says so)."""
        model = self._ensure_model()
        vectors = model.encode(list(texts), convert_to_numpy=True)
        encoded: np.ndarray = np.asarray(vectors, dtype=np.float32)
        return encoded

    def _ensure_model(self) -> Any:
        """Loaded on first use, and the failure is remembered.

        Lazy for `FasterWhisperTranscriber`'s reason: constructing the composition root
        must not pull weights over the network. Remembered because `readiness()` is asked
        after the fact — a failure that left no trace would report as ready and fail again
        at the next utterance, mid-interview.
        """
        if self._model is not None:
            return self._model
        try:
            from sentence_transformers import SentenceTransformer  # noqa: PLC0415 — lazy
        except ImportError as exc:
            self._failure = "not_installed"
            raise EmbedderUnavailableError(
                f"{DISTRIBUTION} is not installed, so notes cannot be matched. "
                "Install the [embeddings] extra."
            ) from exc
        try:
            self._model = SentenceTransformer(self.model_id)
        except Exception as exc:  # noqa: BLE001 — every load failure means the same thing
            # Broad on purpose. A missing download, a denied network, a half-written
            # cache and a corrupt file all arrive as different exception types from two
            # libraries, and every one of them means "this machine cannot match notes".
            # Narrowing would only decide which of them reaches the user as a traceback.
            self._failure = "load_failed"
            raise EmbedderUnavailableError(
                f"The matching model {self.model_id} could not be loaded. Run setup "
                "while online to download it."
            ) from exc
        self._failure = None
        return self._model


def _distribution_version() -> str:
    try:
        return version(DISTRIBUTION)
    except PackageNotFoundError:
        return VERSION_UNKNOWN
