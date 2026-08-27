import base64
import string
import typing as t
from collections.abc import Mapping
from dataclasses import dataclass
from io import BufferedIOBase, BufferedReader, BytesIO

import requests
from PIL import Image


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


class IrisAPI:
    def __init__(
        self,
        iris_endpoint: str,
        *,
        noa_prefix: str = "/noa",
        timeout: float = 30.0,
    ):
        self.iris_endpoint = iris_endpoint.rstrip("/")
        self.noa_prefix = "/" + noa_prefix.strip("/")
        self.timeout = timeout

    def __parse(self, res: requests.Response) -> dict:
        try:
            data: dict = res.json()
        except Exception:
            raise IrisError(f"Iris 응답 JSON 파싱 오류: {res.text}")

        if not 200 <= res.status_code <= 299:
            message = data.get("error") or data.get("message") or "알 수 없는 오류"
            raise IrisError(f"Iris 오류 ({res.status_code}): {message}")

        return data

    def __noa_url(self, path: str) -> str:
        return f"{self.iris_endpoint}{self.noa_prefix}/{path.lstrip('/')}"

    def __post_noa(self, path: str, data: dict | None = None) -> dict:
        res = requests.post(
            self.__noa_url(path),
            json=data,
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
        """Send Markdown through Noa's Iris reply interception."""
        if not isinstance(markdown, str) or not markdown.strip():
            raise ValueError("markdown must be a non-empty string")
        res = requests.post(
            f"{self.iris_endpoint}/reply",
            json={"type": "markdown", "room": str(room_id), "data": markdown},
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
        """Insert and send a KakaoTalk custom message through Noa."""
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
        """Kick an open-chat member using Noa's configured hook/accessibility mode."""
        if user_id is None and (nickname is None or not nickname.strip()):
            raise ValueError("user_id or nickname is required")
        data = {}
        if user_id is not None:
            data["userId"] = str(user_id)
        if nickname is not None:
            data["nickname"] = nickname.strip()
        return self.__post_noa(f"rooms/{room_id}/kick", data)

    def leave_room(self, room_id: int | str):
        return self.__post_noa(f"rooms/{room_id}/leave")

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
        return self.__post_noa(
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
        return self.__post_noa(
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
        return self.__post_noa("open-chat/join", data)

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


def _render_mentions(
    template: str,
    mentions: Mapping[str, Mention | _MentionUser],
) -> tuple[str, list[dict]]:
    if not isinstance(template, str):
        raise TypeError("template must be a string")

    parts = []
    mention_index = 0
    used = set()
    rendered_mentions = {}
    parsed = string.Formatter().parse(template)
    for literal, field_name, format_spec, conversion in parsed:
        parts.append(literal)
        if field_name is None:
            continue
        if not field_name or format_spec or conversion:
            raise ValueError("mention placeholders cannot use formatting or conversion")
        if field_name not in mentions:
            raise ValueError(f"mention target is missing: {field_name}")

        target = _coerce_mention(mentions[field_name])
        used.add(field_name)
        mention_index += 1
        key = (target.user_id, target.nickname)
        rendered_mentions.setdefault(
            key,
            {
                "user_id": target.user_id,
                "at": [],
                "len": _utf16_length(target.nickname),
            },
        )["at"].append(mention_index)

        rendered = f"@{target.nickname}"
        parts.append(rendered)

    unused = set(mentions) - used
    if unused:
        raise ValueError(f"unused mention targets: {', '.join(sorted(unused))}")
    return "".join(parts), list(rendered_mentions.values())


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
