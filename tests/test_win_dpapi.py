"""T11.2 — the DPAPI cipher binding itself (FR82).

Everything around `DpapiCipher` — the store, the envelope, listing, deletion — is
tested elsewhere behind the `Cipher` Protocol with `ReversingCipher`/`CountingCipher`
doubles. This file is the one piece that needed the real Windows target machine:
`CryptProtectData`/`CryptUnprotectData` against the actual account, not a fake.

Marked `windows` (pyproject's marker, unused until now) so the suite still collects
and skips cleanly anywhere else. The cross-account half of FR82's acceptance criterion
— "cross-account decryption fails" — cannot run as a single-process unit test; what is
verified here is the half that can be: `CryptUnprotectData` refuses ciphertext it did
not produce, which is the same code path a foreign account's blob would hit.
"""

from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.windows

if os.name != "nt":
    pytest.skip("DPAPI is a Windows API", allow_module_level=True)

from interview_prep_recall.platform.win_dpapi import DpapiCipher  # noqa: E402
from interview_prep_recall.report.store import default_cipher  # noqa: E402


def test_roundtrip_recovers_the_plaintext() -> None:
    cipher = DpapiCipher()
    plaintext = b"an interviewer's words, bound to this account"

    assert cipher.decrypt(cipher.encrypt(plaintext)) == plaintext


def test_roundtrip_survives_empty_and_binary_plaintext() -> None:
    cipher = DpapiCipher()

    assert cipher.decrypt(cipher.encrypt(b"")) == b""
    binary = bytes(range(256))
    assert cipher.decrypt(cipher.encrypt(binary)) == binary


def test_ciphertext_is_not_the_plaintext() -> None:
    """FR82 is broken if the "encryption" is a pass-through nobody would notice."""
    cipher = DpapiCipher()
    plaintext = b"plainly readable if this failed"

    assert cipher.encrypt(plaintext) != plaintext


def test_decrypting_garbage_raises_rather_than_returning_nonsense() -> None:
    """The property FR82 actually needs: unrecognised ciphertext refuses to open. A
    cross-account blob takes the same `CryptUnprotectData` failure path as this does.
    """
    cipher = DpapiCipher()

    with pytest.raises(OSError):
        cipher.decrypt(b"not something CryptProtectData ever produced")


def test_default_cipher_is_dpapi_on_windows() -> None:
    assert isinstance(default_cipher(), DpapiCipher)
