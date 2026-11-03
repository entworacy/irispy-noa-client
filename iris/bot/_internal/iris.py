import base64
import string
import typing as t
from collections.abc import Mapping
from dataclasses import dataclass
from io import BufferedIOBase, BufferedReader, BytesIO
from urllib.parse import urlsplit

import requests
from PIL import Image

from iris.bot._internal.loco import LocoMixin
from iris.bot._internal.vox import VoxAudioSource, VoxMixin

FileReplyData = bytes | bytearray | memoryview | str | dict | list


class IrisError(RuntimeError):
    """Raised when Iris or a Noa extension endpoint rejects a request."""


@dataclass(frozen=True)
class Mention:
    """A KakaoTalk mention target used by :meth:`IrisAPI.custom_text`."""

    user_id: int | str
    nickname: str


class _MentionUser(t.Protocol):
    @property
    def id(self) -> int | str: ...

    @property
    def name(self) -> str | None: ...


@dataclass
class IrisRequest:
    msg: str
    room: str
    sender: str
    raw: dict


class IrisAPI(VoxMixin, LocoMixin):
    def __init__(
        self,
        iris_endpoint: str,
        *,
        noa_prefix: str = "/noa",
        noa_url: str | None = None,
        noa_token: str | None = None,
        timeout: float | tuple[float, float] | None = 30.0,
    ):
        self.iris_endpoint = iris_endpoint.rstrip("/")
        self.noa_prefix = "/" + noa_prefix.strip("/")
        self.timeout = timeout
        self.noa_url = None if noa_url is None else _noa_base_url(noa_url)
        if noa_token is not None:
            if self.noa_url is None:
                raise ValueError("noa_token requires noa_url")
            if (
                not isinstance(noa_token, str)
                or not noa_token
                or any(c.isspace() for c in noa_token)
            ):
                raise ValueError("noa_token must be a non-empty token without whitespace")
        self._noa_token = noa_token

    def __parse(self, res: requests.Response) -> dict | list:
        try:
            data = res.json()
        except Exception:
            raise IrisError(f"Iris 응답 JSON 파싱 오류: {res.text}")

        failed = isinstance(data, dict) and (
            data.get("success") is False or data.get("ok") is False
        )
        if not 200 <= res.status_code <= 299 or failed:
            message = (
                (data.get("error") or data.get("message"))
                if isinstance(data, dict) else None
            )
            message = message or "알 수 없는 오류"
            raise IrisError(f"Iris 오류 ({res.status_code}): {message}")

        if not isinstance(data, (dict, list)):
            raise IrisError("Iris 응답은 JSON 객체 또는 배열이어야 합니다")
        return data

    def __noa_direct_url(self, path: str) -> str:
        if self.noa_url is None:
            raise ValueError("this API requires noa_url, for example http://127.0.0.1:4000")
        return f"{self.noa_url}/{path.lstrip('/')}"

    def __noa_headers(self) -> dict[str, str]:
        if self._noa_token is None:
            return {}
        return {"Authorization": f"Bearer {self._noa_token}"}

    def _get_noa_direct(self, path: str, *, params: dict | None = None) -> dict | list:
        res = requests.get(
            self.__noa_direct_url(path),
            params=params,
            headers=self.__noa_headers(),
            timeout=self.timeout,
            allow_redirects=False,
        )
        return self.__parse(res)

    def _post_noa_direct(self, path: str, data: dict) -> dict:
        res = requests.post(
            self.__noa_direct_url(path),
            json=data,
            headers=self.__noa_headers(),
            timeout=self.timeout,
            allow_redirects=False,
        )
        return self.__parse(res)

    def __noa_url(self, path: str) -> str:
        return f"{self.iris_endpoint}{self.noa_prefix}/{path.lstrip('/')}"

    def _get_noa(self, path: str) -> dict:
        res = requests.get(self.__noa_url(path), timeout=self.timeout)
        return self.__parse(res)

    def _post_noa(self, path: str, data: dict | None = None) -> dict:
        res = requests.post(
            self.__noa_url(path),
            json=data,
            timeout=self.timeout,
        )
        return self.__parse(res)

    def _post_noa_binary(
        self,
        path: str,
        data: VoxAudioSource,
        *,
        params: dict[str, str] | None = None,
    ) -> dict:
        res = requests.post(
            self.__noa_url(path),
            params=params,
            data=data,
            headers={"Content-Type": "application/octet-stream"},
            timeout=self.timeout,
        )
        return self.__parse(res)

    def reply(self, room_id: int, msg: str, thread_id: int | None = None):
        json_data = {"type": "text", "room": str(room_id), "data": str(msg)}
        if thread_id is not None:
            json_data["threadId"] = str(thread_id)
        res = requests.post(
            f"{self.iris_endpoint}/reply",
            json=json_data,
            timeout=self.timeout,
        )
        return self.__parse(res)

    def reply_markdown(self, room_id: int | str, markdown: str):
        """Submit Markdown using Noa's version-specific transport.

        KakaoTalk 26.9+ uses RichText and requires Noa's Kakao hook.
        Older versions use the original Markdown Intent without a Kakao hook.
        Iris v0.33 returns an enqueue acknowledgement, not delivery confirmation.
        """
        if not isinstance(markdown, str) or not markdown.strip():
            raise ValueError("markdown must be a non-empty string")
        res = requests.post(
            f"{self.iris_endpoint}/reply",
            json={"type": "markdown", "room": str(room_id), "data": markdown},
            timeout=self.timeout,
        )
        return self.__parse(res)

    def reply_file(
        self,
        room_id: int | str,
        *,
        data: FileReplyData | None = None,
        path: str | None = None,
    ) -> dict:
        """Send bytes, Base64/Data URI, an Iris media object, or an Android path.

        Objects/arrays use Iris v0.33's media handler. Strings and explicit
        Android paths use Noa when the file hook is enabled. Select one input.
        """
        if (data is None) == (path is None):
            raise ValueError("provide exactly one of data or path")
        payload = {"type": "file", "room": str(room_id)}
        if path is not None:
            if not isinstance(path, str) or not path.startswith("/") or "\0" in path:
                raise ValueError("path must be an absolute Android file path")
            payload["path"] = path
        else:
            if isinstance(data, (bytes, bytearray, memoryview)):
                data = base64.b64encode(data).decode("ascii")
            if not isinstance(data, (str, dict, list)):
                raise TypeError("data must be bytes, Base64/Data URI, a media object or array")
            if not data:
                raise ValueError("data must not be empty")
            payload["data"] = data
        res = requests.post(
            f"{self.iris_endpoint}/reply",
            json=payload,
            timeout=self.timeout,
        )
        return self.__parse(res)

    def custom_reply(
        self,
        room_id: int | str,
        message_type: int,
        message: str = "",
        *,
        attachment: dict | str | None = None,
        supplement: dict | str | None = None,
        thread_id: int | str | None = None,
        scope: int = 1,
        v: dict | str | None = None,
        is_silence: int = 0,
        created_at: int | None = None,
        client_message_id: int | None = None,
    ):
        """Submit a custom message; Iris's Enqueued response is not DB verification."""
        if not isinstance(message_type, int) or not 1 <= message_type <= 65_535:
            raise ValueError("message_type must be between 1 and 65535")
        data = {
            "type": message_type,
            "message": str(message),
            "attachment": {} if attachment is None else attachment,
            "chat_id": str(room_id),
            "thread_id": None if thread_id is None else str(thread_id),
            "scope": scope,
            "supplement": supplement,
            "v": v,
            "is_silence": is_silence,
        }
        if created_at is not None:
            data["created_at"] = created_at
        if client_message_id is not None:
            data["client_message_id"] = client_message_id
        res = requests.post(
            f"{self.iris_endpoint}/reply",
            json={"type": "custom", "room": str(room_id), "data": data},
            timeout=self.timeout,
        )
        return self.__parse(res)

    def custom_text(
        self,
        room_id: int | str,
        template: str,
        *,
        mentions: Mapping[str, Mention | _MentionUser] | None = None,
        attachment: dict | None = None,
        **kwargs,
    ):
        """Send custom text while generating KakaoTalk mention ranges."""
        message, generated_mentions = _render_mentions(template, mentions or {})
        if attachment is not None and not isinstance(attachment, dict):
            raise TypeError("attachment must be a dict")
        payload = dict(attachment or {})
        if generated_mentions:
            if "mentions" in payload:
                raise ValueError(
                    "attachment must not contain mentions when mentions are provided"
                )
            payload["mentions"] = generated_mentions
        return self.custom_reply(
            room_id,
            message_type=1,
            message=message,
            attachment=payload,
            **kwargs,
        )

    def noa_health(self):
        res = requests.get(self.__noa_url("health"), timeout=self.timeout)
        return self.__parse(res)

    def kick_member(
        self,
        room_id: int | str,
        *,
        user_id: int | str | None = None,
        nickname: str | None = None,
    ):
        """Kick an open-chat user; Noa selects the path by current membership."""
        if user_id is None and (nickname is None or not nickname.strip()):
            raise ValueError("user_id or nickname is required")
        room = _positive_id("room_id", room_id)
        data = {}
        if user_id is not None:
            data["userId"] = str(_positive_id("user_id", user_id))
        if nickname is not None:
            data["nickname"] = nickname.strip()
        return self._post_noa(f"rooms/{room}/kick", data)

    def hide_message(self, room_id: int | str, log_id: int | str):
        """Hide an open-chat message through Noa's KakaoTalk hook."""
        room = _positive_id("room_id", room_id)
        log = _positive_id("log_id", log_id)
        return self._post_noa(f"rooms/{room}/messages/{log}/hide")

    def leave_room(self, room_id: int | str):
        return self._post_noa(f"rooms/{room_id}/leave")

    def get_open_chat_profiles(self):
        res = requests.get(
            self.__noa_url("open-chat/profiles"),
            timeout=self.timeout,
        )
        return self.__parse(res)

    def share_open_profile(
        self,
        link_id: int | str,
        *,
        mode: str = "auto",
    ):
        self.__validate_mode(mode)
        return self._post_noa(
            "open-chat/profiles/share",
            {"linkId": str(link_id), "mode": mode},
        )

    def share_member_open_profile(
        self,
        room_id: int | str,
        user_id: int | str,
        *,
        mode: str = "auto",
    ):
        self.__validate_mode(mode)
        return self._post_noa(
            "open-chat/profiles/share-member",
            {"chatId": str(room_id), "userId": str(user_id), "mode": mode},
        )

    def join_open_chat(
        self,
        url: str,
        *,
        profile_id: int | str | None = None,
    ):
        data = {"url": url}
        if profile_id is not None:
            data["profileId"] = str(profile_id)
        return self._post_noa("open-chat/join", data)

    @staticmethod
    def __validate_mode(mode: str):
        if mode not in {"auto", "accessibility", "hook"}:
            raise ValueError("mode must be auto, accessibility, or hook")

    def reply_media(
        self,
        room_id: int,
        files: t.List[BufferedIOBase | bytes | Image.Image | str],
        thread_id: int | None = None,
    ):
        if type(files) is not list:
            files = [files]
        data = []
        for file in files:
            try:
                if isinstance(file, BufferedIOBase):
                    data.append(base64.b64encode(file.read()).decode())
                elif isinstance(file, bytes):
                    data.append(base64.b64encode(file).decode())
                elif isinstance(file, Image.Image):
                    image_bytes_io = BytesIO()
                    img = file.convert("RGBA")
                    img.save(image_bytes_io, format="PNG")
                    image_bytes_io.seek(0)
                    buffered_reader = BufferedReader(image_bytes_io)
                    data.append(base64.b64encode(buffered_reader.read()).decode())
                elif isinstance(file, str):
                    try:
                        if file.startswith("http"):
                            res = requests.get(file)
                            if res.status_code == 200:
                                file = res.content
                            else:
                                print(f"이미지 다운로드 실패: {res.status_code}")
                        else:
                            with open(file, "rb") as f:
                                file = f.read()
                        data.append(base64.b64encode(file).decode())
                    except Exception as e:
                        print(f"이미지 처리 중 오류 발생: {e}")
                else:
                    print(f"지원하지 않는 형식입니다: {type(file)}")
            except TypeError as e:
                print(f"이미지 처리 중 오류 발생: {e}")
                continue
        if len(data) > 0:
            json_data = {"type": "image_multiple", "room": str(room_id), "data": data}
            if thread_id is not None:
                json_data["threadId"] = str(thread_id)
            res = requests.post(
                f"{self.iris_endpoint}/reply",
                json=json_data,
                timeout=self.timeout,
            )
            return self.__parse(res)
        else:
            print(
                "이미지 전송이 모두 실패하였습니다. "
                "이미지 전송 요청 부분을 확인해주세요."
            )

    def decrypt(self, enc: int, b64_ciphertext: str, user_id: int) -> str | None:
        res = requests.post(
            f"{self.iris_endpoint}/decrypt",
            json={"enc": enc, "b64_ciphertext": b64_ciphertext, "user_id": user_id},
            timeout=self.timeout,
        )

        res = self.__parse(res)
        return res.get("plain_text")

    def query(self, query: str, bind: list[t.Any] | None = None) -> list[dict]:
        res = requests.post(
            f"{self.iris_endpoint}/query",
            json={"query": query, "bind": bind or []},
            timeout=self.timeout,
        )
        res = self.__parse(res)
        return res.get("data", [])

    def get_info(self):
        res = requests.get(f"{self.iris_endpoint}/config", timeout=self.timeout)
        return self.__parse(res)

    def get_aot(self):
        res = requests.get(f"{self.iris_endpoint}/aot", timeout=self.timeout)
        return self.__parse(res)


def _noa_base_url(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("noa_url must be a non-empty HTTP(S) URL")
    value = value.strip()
    if "://" not in value:
        value = "http://" + value
    parsed = urlsplit(value)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or any(c.isspace() for c in value)
    ):
        raise ValueError("noa_url must be an HTTP(S) base URL without credentials, query or fragment")
    # Validate the port before any request is made.
    _ = parsed.port
    return value.rstrip("/")


def _render_mentions(
    template: str,
    mentions: Mapping[str, Mention | _MentionUser],
) -> tuple[str, list[dict]]:
    if not isinstance(template, str):
        raise TypeError("template must be a string")

    parts = []
    at_count = 0
    used = set()
    rendered_mentions = []
    parsed = string.Formatter().parse(template)
    for literal, field_name, format_spec, conversion in parsed:
        parts.append(literal)
        at_count += literal.count("@")
        if field_name is None:
            continue
        if not field_name or format_spec or conversion:
            raise ValueError("mention placeholders cannot use formatting or conversion")
        if field_name not in mentions:
            raise ValueError(f"mention target is missing: {field_name}")

        target = _coerce_mention(mentions[field_name])
        used.add(field_name)
        at_count += 1
        rendered_mentions.append(
            {
                "user_id": target.user_id,
                "at": [at_count],
                "len": _utf16_length(target.nickname),
            }
        )

        rendered = f"@{target.nickname}"
        parts.append(rendered)
        at_count += target.nickname.count("@")

    unused = set(mentions) - used
    if unused:
        raise ValueError(f"unused mention targets: {', '.join(sorted(unused))}")
    return "".join(parts), rendered_mentions


def _positive_id(name: str, value: int | str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise ValueError(f"{name} must be a positive 64-bit integer")
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a positive 64-bit integer") from None
    if not 1 <= parsed <= 9_223_372_036_854_775_807:
        raise ValueError(f"{name} must be a positive 64-bit integer")
    return parsed


def _coerce_mention(value: Mention | _MentionUser) -> Mention:
    if isinstance(value, Mention):
        user_id = value.user_id
        nickname = value.nickname
    else:
        user_id = getattr(value, "id", None)
        nickname = getattr(value, "name", None)

    try:
        parsed_user_id = int(user_id)
    except (TypeError, ValueError):
        raise ValueError("mention user_id must be a positive 64-bit integer") from None
    if (
        isinstance(user_id, bool)
        or not 1 <= parsed_user_id <= 9_223_372_036_854_775_807
    ):
        raise ValueError("mention user_id must be a positive 64-bit integer")
    if not isinstance(nickname, str) or not nickname.strip():
        raise ValueError("mention nickname must be a non-empty string")
    return Mention(parsed_user_id, nickname)


def _utf16_length(value: str) -> int:
    return len(value.encode("utf-16-le")) // 2
