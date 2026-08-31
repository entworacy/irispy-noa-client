import typing as t
from collections.abc import Iterable

VoxAudioSource = bytes | bytearray | memoryview | t.BinaryIO | Iterable[bytes]


class VoxMixin:
    """Noa VOX API methods mixed into :class:`IrisAPI`."""

    def vox_status(self) -> dict:
        """Return the current voice-talk, voice-room, and audio injector state."""
        return self._get_noa("vox/status")

    def vox_start_voice_talk(
        self,
        room_id: int | str,
        *,
        peer_ids: t.Iterable[int | str] | None = None,
    ) -> dict:
        """Start a normal or open-chat voice call in ``room_id``."""
        data = {"chatId": str(room_id)}
        if peer_ids is not None:
            if isinstance(peer_ids, (str, bytes)):
                raise TypeError("peer_ids must be an iterable of user IDs")
            data["peerIds"] = [str(peer_id) for peer_id in peer_ids]
        return self._post_noa("vox/voice-talk", data)

    def vox_create_voice_room(
        self,
        room_id: int | str,
        *,
        title: str | None = None,
    ) -> dict:
        """Create an open-chat voice room, optionally overriding its title."""
        data = {"chatId": str(room_id)}
        if title is not None:
            if not isinstance(title, str):
                raise TypeError("title must be a string")
            data["title"] = title
        return self._post_noa("vox/voice-rooms", data)

    def vox_join_voice_room(self, room_id: int | str) -> dict:
        """Join the active open-chat voice room in ``room_id``."""
        return self._post_noa(
            "vox/voice-rooms/join",
            {"chatId": str(room_id)},
        )

    def vox_leave(self, room_id: int | str, *, kind: str) -> dict:
        """Leave a ``cecall`` or ``voiceroom`` VOX session."""
        _validate_kind(kind)
        return self._post_noa(
            "vox/leave",
            {"chatId": str(room_id), "kind": kind},
        )

    def vox_audio_start(self, *, mode: str | None = None) -> dict:
        """Start PCM injection in ``replace`` or ``mix`` mode."""
        data = {}
        if mode is not None:
            _validate_mode(mode)
            data["mode"] = mode
        return self._post_noa("vox/audio/start", data)

    def vox_audio_push(self, pcm: bytes | bytearray | memoryview) -> dict:
        """Push one complete, even-sized s16le PCM chunk of at most 96,000 bytes."""
        data = _pcm_bytes(pcm, maximum=96_000)
        return self._post_noa_binary("vox/audio", data)

    def vox_audio_stream(
        self,
        source: VoxAudioSource,
        *,
        mode: str | None = None,
        kind: str | None = None,
        room_id: int | str | None = None,
    ) -> dict:
        """Upload an s16le PCM source to Noa's paced stream endpoint."""
        if mode is not None:
            _validate_mode(mode)
        if kind is not None:
            _validate_kind(kind)
        if isinstance(source, (bytes, bytearray, memoryview)):
            source = _pcm_bytes(source)
        elif isinstance(source, str) or not (
            hasattr(source, "read") or isinstance(source, Iterable)
        ):
            raise TypeError("source must be bytes, a binary file, or an iterable of bytes")

        params = {}
        if mode is not None:
            params["mode"] = mode
        if kind is not None:
            params["kind"] = kind
        if room_id is not None:
            params["chatId"] = str(room_id)
        return self._post_noa_binary(
            "vox/audio/stream",
            source,
            params=params or None,
        )

    def vox_audio_stop(self) -> dict:
        """Stop PCM injection and clear the pending audio queue."""
        return self._post_noa("vox/audio/stop")


def _validate_mode(mode: str):
    if mode not in {"replace", "mix"}:
        raise ValueError("mode must be replace or mix")


def _validate_kind(kind: str):
    if kind not in {"cecall", "voiceroom"}:
        raise ValueError("kind must be cecall or voiceroom")


def _pcm_bytes(
    pcm: bytes | bytearray | memoryview,
    *,
    maximum: int | None = None,
) -> bytes:
    if not isinstance(pcm, (bytes, bytearray, memoryview)):
        raise TypeError("pcm must be bytes-like")
    data = bytes(pcm)
    if not data:
        raise ValueError("pcm must not be empty")
    if len(data) % 2:
        raise ValueError("pcm must contain complete 16-bit samples")
    if maximum is not None and len(data) > maximum:
        raise ValueError(f"pcm must not exceed {maximum} bytes")
    return data
