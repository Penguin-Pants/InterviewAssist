"""Doubles shared by more than one test module.

Imported as bare `helpers`, never `tests.helpers`: `tests/` has no `__init__.py`, so
pytest puts the test directory on `sys.path` while the repo root only lands there under
`python -m pytest`, which adds the cwd. CI runs the `pytest` console script, which does
not. This broke CI once, was recorded in the progress doc, and was then written the wrong
way again in the very next milestone — which is why the pre-push check runs under
`PYTHONSAFEPATH=1`.

Imported as bare `helpers`, never `tests.helpers`: `tests/` has no `__init__.py`, so
pytest puts the test directory on `sys.path` and the repo root only appears there under
`python -m pytest`, which adds the cwd. CI runs the `pytest` console script, which does
not. Recorded in the progress doc after it broke CI once — and then written the wrong way
again in the very next milestone, which is why the pre-push check runs `PYTHONSAFEPATH=1`.

Extracted when `test_app.py` needed the same cipher and model client `test_report.py`
already had. Two copies of a double drift, and the divergence shows up as one suite
passing against behaviour the other has already ruled out.

`FakeStream`, `FakePyAudio` and `raw_endpoint` extracted the same way when
`test_audio_capture.py`'s T1.5 keep-alive tests needed the same PortAudio double
`test_audio_devices.py`'s render-device tests already had.
"""

from __future__ import annotations

from typing import Any


class ReversingCipher:
    """Obviously not encryption, so no test can accidentally depend on it being one.
    Satisfies the same Protocol the real DPAPI cipher does."""

    def encrypt(self, plaintext: bytes) -> bytes:
        return plaintext[::-1]

    def decrypt(self, ciphertext: bytes) -> bytes:
        return ciphertext[::-1]


def tool_response(payload: dict):  # type: ignore[no-untyped-def]
    """Shaped like a real forced-tool reply: a `tool_use` block carrying parsed input.

    The generator forces `tool_choice`, so this is the only response shape it can
    legitimately receive. A double returning a text block would test a path the API is
    configured never to take.
    """

    class _Block:
        type = "tool_use"
        input = payload

    class _Response:
        content = [_Block()]

    return _Response()


class ScriptedClient:
    """Returns a canned response and records what it was sent."""

    def __init__(self, payload: dict | None = None, boom: Exception | None = None) -> None:
        self.payload = payload if payload is not None else {"findings": []}
        self.boom = boom
        self.requests: list[dict] = []

    def create(self, **kwargs):  # type: ignore[no-untyped-def]
        self.requests.append(kwargs)
        if self.boom is not None:
            raise self.boom
        return tool_response(self.payload)


def raw_endpoint(
    index: int,
    name: str,
    *,
    host_api: int = 2,
    inputs: int = 0,
    outputs: int = 0,
    rate: int = 48_000,
) -> dict[str, Any]:
    """One row of the flat device table `get_device_info_by_index` walks."""
    return {
        "index": index,
        "name": name,
        "hostApi": host_api,
        "maxInputChannels": inputs,
        "maxOutputChannels": outputs,
        "defaultSampleRate": float(rate),
    }


class FakeStream:
    """A PortAudio stream handle, recording its lifecycle into a shared event list so
    ordering between two streams is assertable."""

    def __init__(self, label: str, events: list[str]) -> None:
        self.label = label
        self._events = events
        self.started = False
        self.closed = False

    def start_stream(self) -> None:
        self.started = True
        self._events.append(f"start:{self.label}")

    def stop_stream(self) -> None:
        self._events.append(f"stop:{self.label}")

    def close(self) -> None:
        self.closed = True
        self._events.append(f"close:{self.label}")


class FakePyAudio:
    """The slice of `pyaudiowpatch` the device and capture layers touch."""

    def __init__(
        self,
        loopbacks: list[dict[str, Any]] | None = None,
        mic: dict[str, Any] | None = None,
        default_output: dict[str, Any] | None = None,
        *,
        has_convenience_getter: bool = True,
        table: list[dict[str, Any]] | None = None,
        open_error: Exception | None = None,
    ) -> None:
        self._loopbacks = loopbacks or []
        self._mic = mic
        self._default_output = default_output
        self._table = table or []
        self._open_error = open_error
        self.opened: list[dict[str, Any]] = []
        self.events: list[str] = []
        if has_convenience_getter:
            self.get_default_wasapi_loopback = self._default_wasapi_loopback  # type: ignore[method-assign]

    def get_device_count(self) -> int:
        """One past the highest index, not the row count.

        PortAudio indices are positional, and these tables use the real machine's sparse
        numbering for readability — so the gaps have to be walkable. Lookups into a gap
        raise, which is the path `render_device_for` skips over.
        """
        return max((int(d["index"]) for d in self._table), default=-1) + 1

    def get_device_info_by_index(self, index: int) -> dict[str, Any]:
        for device in self._table:
            if int(device["index"]) == index:
                return device
        raise OSError(f"no device at index {index}")

    def open(self, **kwargs: Any) -> FakeStream:
        if self._open_error is not None and kwargs.get("output"):
            raise self._open_error
        self.opened.append(kwargs)
        return FakeStream("output" if kwargs.get("output") else "input", self.events)

    def _default_wasapi_loopback(self) -> dict[str, Any] | None:
        return self._loopbacks[0] if self._loopbacks else None

    def get_loopback_device_info_generator(self):  # type: ignore[no-untyped-def]
        yield from self._loopbacks

    def get_default_output_device_info(self) -> dict[str, Any]:
        return self._default_output or {}

    def get_default_input_device_info(self) -> dict[str, Any] | None:
        return self._mic
