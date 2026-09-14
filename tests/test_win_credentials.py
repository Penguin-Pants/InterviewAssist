"""T0.5's OS half — the real Windows Credential Manager backend (FR19).

`tests/test_credentials.py` exercises every rule (`CredentialStore`'s validation, the
diagnostic guard, `repr`) against `InMemoryCredentialBackend`, by design — that is
what lets the Linux dev container run the whole suite. What none of those tests touch
is `_default_backend()` actually resolving to `keyring`'s real Windows vault, or a
secret surviving a round trip through it. That is the one thing this file checks.

**Runs against the real, shared Windows Credential Manager, under a test-only service
name.** `SERVICE_NAME` is patched to `TEST_SERVICE_NAME` for the round-trip test, so it
writes to a vault entry the real application can never read, overwrite, or collide
with — not the production `InterviewPrepRecall`/`deepgram` entry a real API key would
live under. An earlier version of this test wrote to the real account directly with a
save/restore `finally`; Codex review on PR #43 pointed out that a killed test process
or a crash between the write and the restore would permanently corrupt a developer's
actual stored key. A separate namespace removes the risk instead of just narrowing it.
"""

from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.windows

if os.name != "nt":
    pytest.skip("Windows Credential Manager is a Windows API", allow_module_level=True)

# `keyring` lives in the `[windows]` extra, not `[dev,ui]` — CI's windows-latest runner
# installs only the latter (see .github/workflows/ci.yml), so a hard `import keyring`
# here crashed collection for the *entire* suite on a real CI run, not just this file.
pytest.importorskip("keyring", reason="requires the [windows] extra's keyring")

from interview_prep_recall.platform import credentials  # noqa: E402
from interview_prep_recall.platform.credentials import (  # noqa: E402
    CredentialStore,
    InMemoryCredentialBackend,
    _default_backend,
)

TEST_SERVICE_NAME = "InterviewPrepRecallTest"
"""Distinct from the real `credentials.SERVICE_NAME`. No account under this name is
ever read by the shipped app, so this test cannot touch a real stored key."""

PROBE_ACCOUNT = "deepgram"
"""A real `KNOWN_ACCOUNTS` entry, required by `CredentialStore._check` — but paired
with `TEST_SERVICE_NAME` above, not the production service name, so it addresses a
throwaway vault entry rather than the real deepgram key."""

SECRET = "sk-test-probe-only-000111222333444555"


def test_default_backend_is_the_real_vault_on_windows() -> None:
    """Not the in-memory fallback — that would mean `keyring` failed to import."""
    assert not isinstance(_default_backend(), InMemoryCredentialBackend)


def test_round_trip_through_the_real_credential_manager(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(credentials, "SERVICE_NAME", TEST_SERVICE_NAME)
    store = CredentialStore(backend=_default_backend())

    store.set(PROBE_ACCOUNT, SECRET)
    try:
        assert store.get(PROBE_ACCOUNT) == SECRET
        assert store.has(PROBE_ACCOUNT)
    finally:
        store.delete(PROBE_ACCOUNT)

    assert store.get(PROBE_ACCOUNT) is None
