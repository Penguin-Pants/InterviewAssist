"""M1 — capture-stream behaviour that needs no device (PR #19 review findings, T1.5)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from helpers import FakePyAudio, raw_endpoint

from interview_prep_recall.audio import capture
from interview_prep_recall.audio.capture import (
    FRAME_BYTES,
    FRAME_S,
    SAMPLE_RATE,
    BoundedFrameQueue,
    CaptureStream,
)
from interview_prep_recall.audio.devices import DeviceError, DeviceInfo, DeviceKind


def _device(rate: int = SAMPLE_RATE, channels: int = 1) -> DeviceInfo:
    return DeviceInfo(
        index=0, name="Fake", kind=DeviceKind.LOOPBACK, channels=channels, sample_rate=rate
    )


def _stream(**kwargs: Any) -> tuple[CaptureStream, BoundedFrameQueue]:
    queue = BoundedFrameQueue(maxlen=500)
    stream = CaptureStream(
        stream_id="interviewer", queue=queue, device=_device(**kwargs), clock=lambda: 100.0
    )
    return stream, queue


def test_frames_from_one_callback_get_consecutive_timestamps() -> None:
    """Frames from a single callback are consecutive 20 ms spans, not simultaneous.

    Stamping them all with the arrival time collapses their timeline, which surfaces
    downstream as early `t_end` values, mis-anchored cloud clocks and echo windows
    compared against the wrong instant. Long driver buffers are an explicitly supported
    path, so this is a normal case rather than an edge one.
    """
    stream, queue = _stream()

    stream._callback(b"\x00" * (FRAME_BYTES * 3), 0, {}, 0)  # noqa: SLF001

    stamps = [t for _frame, t in queue.drain()]
    assert stamps == pytest.approx([100.0, 100.0 + FRAME_S, 100.0 + 2 * FRAME_S])


def test_a_single_frame_keeps_the_arrival_timestamp() -> None:
    stream, queue = _stream()
    stream._callback(b"\x00" * FRAME_BYTES, 0, {}, 0)  # noqa: SLF001
    assert [t for _f, t in queue.drain()] == [100.0]


def test_the_callback_never_imports_the_vendor_module() -> None:
    """The one line guaranteed to run on every callback must not depend on an import that
    fails everywhere except Windows — otherwise no machine used to test the rest of the
    pipeline could run it at all."""
    stream, queue = _stream()
    result = stream._callback(b"\x00" * FRAME_BYTES, 0, {}, 0)  # noqa: SLF001
    assert result == (None, 0)
    assert stream.error is None


def test_stop_discards_buffered_audio() -> None:
    """Restarting would otherwise open the new interview with a fragment of the last one,
    and FR16's purge means audio must not outlive the session that captured it."""
    stream, _queue = _stream()
    partial = b"\x01" * (FRAME_BYTES - 4)
    stream._callback(partial, 0, {}, 0)  # noqa: SLF001
    assert stream._assembler.pending_bytes == len(partial)  # noqa: SLF001

    stream.stop()

    assert stream._assembler.pending_bytes == 0  # noqa: SLF001


def test_stop_is_safe_before_start() -> None:
    stream, _queue = _stream()
    stream.stop()


def test_a_callback_exception_is_recorded_not_raised() -> None:
    """An exception escaping a PortAudio callback crosses into C and takes the process."""
    stream, _queue = _stream(channels=2)

    result = stream._callback(b"\x00" * 3, 0, {}, 0)  # noqa: SLF001

    assert result == (None, 0)


# ---------- keep-alive (T1.5, D-68) ----------
#
# `render_device_for` has its own five tests in test_audio_devices.py; this is the half
# of the keep-alive that has none — `CaptureStream` deciding whether to open one, and in
# what order it tears one down. `FakePyAudio` and `raw_endpoint` come from `helpers`,
# shared with those tests rather than duplicated.


def _loopback(index: int = 7, name: str = "Speakers [Loopback]") -> DeviceInfo:
    return DeviceInfo(
        index=index, name=name, kind=DeviceKind.LOOPBACK, channels=2, sample_rate=48_000
    )


def _mic(index: int = 3, name: str = "Microphone") -> DeviceInfo:
    return DeviceInfo(
        index=index, name=name, kind=DeviceKind.MICROPHONE, channels=1, sample_rate=48_000
    )


def _render_table(loopback: DeviceInfo, render_name: str = "Speakers") -> list[dict[str, Any]]:
    """The loopback's own row (for the host-API lookup) plus a render endpoint that
    `render_device_for` can match it to."""
    return [
        raw_endpoint(loopback.index, loopback.name, inputs=loopback.channels),
        raw_endpoint(loopback.index + 1, render_name, outputs=2),
    ]


def _keep_alive_stream(device: DeviceInfo, pa: FakePyAudio) -> CaptureStream:
    return CaptureStream(stream_id="interviewer", queue=BoundedFrameQueue(), device=device, pa=pa)


def _patch_vendor_module(monkeypatch: pytest.MonkeyPatch) -> None:
    """`start()` calls `_load_pyaudiowpatch()` unconditionally for `paInt16`. `FakePyAudio`
    never inspects the value, so any placeholder does — the point is not importing the
    real package, which has no Linux distribution."""
    monkeypatch.setattr(capture, "_load_pyaudiowpatch", lambda: SimpleNamespace(paInt16=8))


def test_a_loopback_device_opens_a_keep_alive_stream(monkeypatch: pytest.MonkeyPatch) -> None:
    """D-68: an idle loopback endpoint delivers no frames at all unless something holds
    its render side open."""
    _patch_vendor_module(monkeypatch)
    loopback = _loopback()
    pa = FakePyAudio(table=_render_table(loopback))
    stream = _keep_alive_stream(loopback, pa)

    stream.start()

    assert stream.keep_alive_active is True
    assert stream.keep_alive_error is None


def test_a_microphone_does_not_open_a_keep_alive_stream(monkeypatch: pytest.MonkeyPatch) -> None:
    """Microphones stream continuously on their own; D-68 is a loopback-only defect."""
    _patch_vendor_module(monkeypatch)
    pa = FakePyAudio()
    stream = _keep_alive_stream(_mic(), pa)

    stream.start()

    assert stream.keep_alive_active is False
    assert stream.keep_alive_error is None
    assert not any(call.get("output") for call in pa.opened)


def test_stop_closes_the_capture_stream_before_the_keep_alive(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Closing the keep-alive first would let the endpoint go idle while capture is still
    open — the exact defect the keep-alive exists to prevent, reproduced during teardown."""
    _patch_vendor_module(monkeypatch)
    loopback = _loopback()
    pa = FakePyAudio(table=_render_table(loopback))
    stream = _keep_alive_stream(loopback, pa)
    stream.start()
    assert stream.keep_alive_active is True  # sanity: both streams are actually open

    stream.stop()

    assert pa.events == [
        "start:output",
        "start:input",
        "stop:input",
        "close:input",
        "stop:output",
        "close:output",
    ]


def test_a_failed_keep_alive_open_is_recorded_not_raised(monkeypatch: pytest.MonkeyPatch) -> None:
    """Capture without a keep-alive still transcribes; refusing to open the whole device
    over a missing render endpoint would cost the interview instead."""
    _patch_vendor_module(monkeypatch)
    loopback = _loopback()
    pa = FakePyAudio(table=[])  # no render device anywhere matches
    stream = _keep_alive_stream(loopback, pa)

    stream.start()  # must not raise

    assert stream.keep_alive_active is False
    assert isinstance(stream.keep_alive_error, DeviceError)
    assert pa.events == ["start:input"]
