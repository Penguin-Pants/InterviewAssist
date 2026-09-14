"""T0.5's OS half — the real Windows Credential Manager backend (FR19).

`tests/test_credentials.py` exercises every rule (`CredentialStore`'s validation, the
diagnostic guard, `repr`) against `InMemoryCredentialBackend`, by design — that is
what lets the Linux dev container run the whole suite. What none of those tests touch
is `_default_backend()` actually resolving to `keyring`'s real Windows vault, or a
secret surviving a round trip through it. That is the one thing this file checks.

**Runs against the real, shared Windows Credential Manager**, not a fixture — the same
store a real API key would live in. Every test here restores whatever was in a probed
account before it ran, in a `finally`, so a developer's actual stored keys are never
left altered even if an assertion fails.
"""

from __future__ import annotations

import contextlib
import os
from collections.abc import Iterator

import pytest

pytestmark = pytest.mark.windows

if os.name != "nt":
    pytest.skip("Windows Credential Manager is a Windows API", allow_module_level=True)

import keyring  # noqa: E402

from interview_prep_recall.platform.credentials import (  # noqa: E402
    SERVICE_NAME,
    CredentialStore,
    InMemoryCredentialBackend,
    _default_backend,
)

PROBE_ACCOUNT = "deepgram"
"""A real `KNOWN_ACCOUNTS` entry, required by `CredentialStore._check`. Its prior
value (if any) is saved and restored around every test that touches it."""

SECRET = "sk-test-probe-only-000111222333444555"


def test_default_backend_is_the_real_vault_on_windows() -> None:
    """Not the in-memory fallback — that would mean `keyring` failed to import."""
    assert not isinstance(_default_backend(), InMemoryCredentialBackend)


@pytest.fixture
def _restore_probe_account() -> Iterator[None]:
    """Saves and restores whatever `PROBE_ACCOUNT` held before the test ran."""
    original = keyring.get_password(SERVICE_NAME, PROBE_ACCOUNT)
    try:
        yield
    finally:
        if original is None:
            # Already absent — the test's own cleanup got there first.
            with contextlib.suppress(keyring.errors.PasswordDeleteError):
                keyring.delete_password(SERVICE_NAME, PROBE_ACCOUNT)
        else:
            keyring.set_password(SERVICE_NAME, PROBE_ACCOUNT, original)


@pytest.mark.usefixtures("_restore_probe_account")
def test_round_trip_through_the_real_credential_manager() -> None:
    store = CredentialStore(backend=_default_backend())

    store.set(PROBE_ACCOUNT, SECRET)
    try:
        assert store.get(PROBE_ACCOUNT) == SECRET
        assert store.has(PROBE_ACCOUNT)
    finally:
        store.delete(PROBE_ACCOUNT)

    assert store.get(PROBE_ACCOUNT) is None
