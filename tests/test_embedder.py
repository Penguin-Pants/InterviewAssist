"""T9.6a — the concrete `Embedder` (BC-1, D-U13).

`sentence-transformers` is in the `[embeddings]` extra and is **not installed here**, by
the same policy that keeps torch out of CI. That is not a gap in this suite: the states
worth testing are the ones a user is actually in — the library absent, the weights not
downloaded yet — and every one of them is reachable without it.

What cannot be tested here is a successful `encode`, which needs the library and the
weights. It is AS-9's neighbour and belongs on the target machine.
"""

from __future__ import annotations

import importlib.util

import pytest

from interview_prep_recall.notes.embedder import (
    VERSION_UNKNOWN,
    EmbedderUnavailableError,
    SentenceTransformerEmbedder,
)
from interview_prep_recall.notes.index import DEFAULT_EMBED_MODEL_ID

installed = importlib.util.find_spec("sentence_transformers") is not None


def test_construction_is_cheap_and_loads_nothing() -> None:
    """The composition root builds one of these, so construction must not be a download.

    Asserting on the private handle rather than on a timing: the observable difference
    between lazy and eager here is a 90 MB transfer, and a test that waited to find out
    would be the thing it is testing against.

    The id is the fixed one — D-U13 makes the Whisper model a user choice and this one
    never, because changing it invalidates every cached vector (BC-1).
    """
    embedder = SentenceTransformerEmbedder()

    assert embedder.model_id == DEFAULT_EMBED_MODEL_ID
    assert embedder._model is None


@pytest.mark.skipif(installed, reason="the library is installed in this environment")
def test_readiness_reports_the_missing_library_rather_than_guessing() -> None:
    """Preflight's `model_present` probe. Never touches the network to answer."""
    ok, detail = SentenceTransformerEmbedder().readiness()

    assert ok is False
    assert detail == "not_installed"


@pytest.mark.skipif(installed, reason="the library is installed in this environment")
def test_encode_raises_one_error_type_rather_than_the_library_s() -> None:
    """One thing for the caller to catch, and one explanation for the user."""
    embedder = SentenceTransformerEmbedder()

    with pytest.raises(EmbedderUnavailableError, match="embeddings"):
        embedder.encode(["anything"])


@pytest.mark.skipif(installed, reason="the library is installed in this environment")
def test_an_absent_library_never_keys_a_real_cache() -> None:
    """`model_version` has to be readable before anything is loaded, because
    `EmbeddingIndex` reads it to find the cache file. The sentinel is safe because no
    vectors can be written while it is the answer."""
    assert SentenceTransformerEmbedder().model_version == VERSION_UNKNOWN


@pytest.mark.skipif(installed, reason="the library is installed in this environment")
def test_a_failed_load_is_remembered_so_readiness_stops_claiming_ready() -> None:
    """A failure that left no trace would report ready and fail again mid-interview."""
    embedder = SentenceTransformerEmbedder()

    with pytest.raises(EmbedderUnavailableError):
        embedder.encode(["anything"])

    assert embedder.readiness() == (False, "not_installed")
