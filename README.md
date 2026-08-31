# irispy-noa-client

[`irispy-client`](https://github.com/dolidolih/irispy-client)를 기반으로 하며,
[Noa](https://github.com/entworacy/noa)의 Iris 확장 엔드포인트를 바로 사용할 수 있도록
기능을 추가한 Python 클라이언트입니다. 기존 `iris` import와 일반 Iris API는 그대로
호환됩니다.

## 설치

```bash
pip install git+https://github.com/entworacy/irispy-noa-client.git
```

Python 3.10 이상이 필요합니다.

## 기존 `irispy-client`에서 전환

두 패키지는 모두 `iris` import 네임을 사용하므로, 기존 패키지를
먼저 제거한 뒤 Noa 클라이언트를 설치합니다.

```bash
pip uninstall -y irispy-client
pip install "irispy-noa-client @ git+https://github.com/entworacy/irispy-noa-client.git"
```

`pyproject.toml`에서는 기존 의존성을:

```toml
dependencies = [
  "irispy-client @ git+https://github.com/dolidolih/irispy-client.git@11d8720df558cc7a45c76f37b75ce7e1f6002f8a",
]
```

다음과 같이 교체합니다.

```toml
dependencies = [
  "irispy-noa-client @ git+https://github.com/entworacy/irispy-noa-client.git",
]
```

기존 import와 일반 Iris 사용 코드는 변경할 필요가 없습니다.

```python
from iris import Bot, ChatContext, IrisAPI, Mention

bot = Bot("127.0.0.1:3000")
```

강퇴, 오픈채팅 입장, 접근성 custom 재전송처럼 시간이 걸릴 수 있는
Noa 작업을 사용한다면 HTTP timeout을 늘리는 것을 권장합니다.

```python
bot = Bot(
    "127.0.0.1:3000",
    noa_prefix="/noa",
    timeout=130.0,
)
```

기존에 `/reply`로 `custom` JSON을 직접 전송했다면 `ChatContext`의
편의 메서드로 교체할 수 있습니다.

```python
# 기존: requests.post(..., json={"type": "custom", ...})

# 변경 후: 현재 채팅방 ID가 자동 사용됩니다.
chat.custom_reply(
    message_type=1,
    message="메시지",
    attachment={},
)
```

멘션의 `attachment.mentions`, 멘션 순번 `at`, UTF-16 길이 `len`을 직접 계산했다면
`custom_text` 템플릿으로 교체합니다.

```python
chat.custom_text(
    "{sender} 님 안녕하세요!",
    mentions={"sender": chat.sender},
)
```

설치된 버전을 확인합니다.

```bash
python -c "import iris; print(iris.__version__)"
```

`0.5.0`이 출력되면 정상입니다. 실행 중인 봇은 패키지 교체 후
반드시 재시작해야 합니다.

## Noa 확장 API

`Bot.api` 또는 직접 생성한 `IrisAPI`에서 다음 메서드를 사용할 수 있습니다.

- `kick_member(room_id, user_id=..., nickname=...)`
- `reply_markdown(room_id, markdown)`
- `custom_text(room_id, template, mentions=...)`
- `custom_reply(room_id, message_type, message, ...)`
- `noa_health()`
- `get_open_chat_profiles()`
- `share_open_profile(link_id, mode="auto")`
- `share_member_open_profile(room_id, user_id, mode="auto")`
- `join_open_chat(url, profile_id=None)`
- `leave_room(room_id)`
- `vox_status()`
- `vox_start_voice_talk(room_id, peer_ids=None)`
- `vox_create_voice_room(room_id, title=None)`
- `vox_join_voice_room(room_id)`
- `vox_leave(room_id, kind=...)`
- `vox_audio_start(mode=None)`
- `vox_audio_push(pcm)`
- `vox_audio_stream(source, mode=None, kind=None, room_id=None)`
- `vox_audio_stop()`

큰 KakaoTalk ID가 JSON 숫자 정밀도로 손상되지 않도록 방, 사용자, 프로필 ID는
요청 본문에서 문자열로 전송됩니다. 오픈프로필 공유의 `mode`는 `auto`, `hook`,
`accessibility` 중 하나이며, VOX 오디오의 `mode`는 `replace` 또는 `mix`입니다.

```python
from iris import IrisAPI

api = IrisAPI("http://127.0.0.1:3000")

# userId 기준 강퇴
api.kick_member("18422091737011039", user_id="7626329973288865709")

# Markdown 전송
api.reply_markdown("18422091737011039", "**안녕하세요**")

# KakaoTalk custom message 삽입 및 재전송
api.custom_reply(
    "18422091737011039",
    message_type=1,
    message="메시지",
    attachment={},
)

# 멘션에서 구한 userId의 오픈프로필 링크 공유
result = api.share_member_open_profile(
    "18422091737011039",
    "7626329973288865709",
    mode="hook",
)
print(result["url"])
```

### VOX 보이스톡과 PCM 송출

일반 보이스톡은 대상 채팅방에서 시작합니다. `peer_ids`를 생략하면 Noa가
채팅방 참여자를 기준으로 대상을 결정합니다.

```python
api.vox_start_voice_talk(
    "18422091737011039",
    peer_ids=["7626329973288865709"],
)
```

오픈채팅 보이스룸의 제목을 비롯한 값은 봇 코드에서 직접 지정할 수 있습니다.

```python
api.vox_create_voice_room(
    "18422091737011039",
    title="음악 테스트",
)
api.vox_join_voice_room("18422091737011039")
api.vox_leave("18422091737011039", kind="voiceroom")
```

오디오는 헤더 없는 signed 16-bit little-endian, 48 kHz, mono PCM이어야 합니다.
한 번에 파일을 재생할 때는 Noa가 재생 속도와 큐를 관리하는 스트림 API를
사용합니다.

```python
with open("audio.pcm", "rb") as pcm:
    api.vox_audio_stream(
        pcm,
        mode="replace",
        kind="voiceroom",
        room_id="18422091737011039",
    )
```

Iris 게이트웨이는 스트림 요청 본문을 받은 뒤 Noa로 전달하므로, 긴 파일은
충분한 `timeout`을 지정해야 합니다. `timeout=None`을 사용하면 HTTP 읽기 제한을
두지 않습니다.

```python
api = IrisAPI("http://127.0.0.1:3000", timeout=None)
```

실시간 생성 오디오처럼 각 청크를 즉시 보내야 할 때는 `audio/start`, 반복
`audio`, `audio/stop` 흐름을 사용합니다. 각 청크는 최대 96,000바이트이며
완전한 16-bit 샘플 단위여야 합니다. 송출 속도는 호출 측에서 PCM 재생 시간에
맞춰 조절합니다.

```python
import time

api.vox_audio_start(mode="replace")
with open("audio.pcm", "rb") as pcm:
    while chunk := pcm.read(9_600):  # 48 kHz mono s16le 기준 100 ms
        api.vox_audio_push(chunk)
        time.sleep(len(chunk) / 96_000)
api.vox_audio_stop()
```

### 노래봇 예제

아래 예제는 오픈채팅 보이스룸을 열고 YouTube URL 또는 검색어의 오디오를
재생합니다. `yt-dlp`와 `ffmpeg` 실행 파일이 `PATH`에 있어야 합니다.

```bash
pip install yt-dlp
```

```python
import subprocess
import threading
import time

from iris import Bot


IRIS_URL = "127.0.0.1:3000"
VOICE_ROOM_TITLE = "노래봇"
AUDIO_MODE = "replace"  # 원래 통화 음성과 섞으려면 "mix"
PCM_BYTES_PER_SECOND = 96_000  # 48 kHz * mono * signed 16-bit
PCM_CHUNK_BYTES = 9_600        # 100 ms

bot = Bot(
    IRIS_URL,
    max_workers=4,             # 재생 중에도 !정지 명령 처리
    timeout=130.0,
)

playback_lock = threading.Lock()
stop_playback = threading.Event()


def stop_process(process):
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


def play(chat, query):
    if not playback_lock.acquire(blocking=False):
        chat.reply("이미 노래를 재생하고 있습니다. 먼저 !정지를 사용해 주세요.")
        return

    downloader = None
    decoder = None
    stop_playback.clear()
    try:
        source = query if "://" in query else f"ytsearch1:{query}"
        downloader = subprocess.Popen(
            [
                "yt-dlp",
                "--no-playlist",
                "--no-progress",
                "-f",
                "bestaudio/best",
                "-o",
                "-",
                source,
            ],
            stdout=subprocess.PIPE,
        )
        decoder = subprocess.Popen(
            [
                "ffmpeg",
                "-nostdin",
                "-loglevel",
                "error",
                "-i",
                "pipe:0",
                "-vn",
                "-ac",
                "1",
                "-ar",
                "48000",
                "-f",
                "s16le",
                "pipe:1",
            ],
            stdin=downloader.stdout,
            stdout=subprocess.PIPE,
        )
        downloader.stdout.close()

        chat.vox_audio_start(mode=AUDIO_MODE)
        deadline = time.monotonic()
        while not stop_playback.is_set():
            chunk = decoder.stdout.read(PCM_CHUNK_BYTES)
            if not chunk:
                break
            chat.vox_audio_push(chunk)
            deadline += len(chunk) / PCM_BYTES_PER_SECOND
            stop_playback.wait(max(0, deadline - time.monotonic()))

        if not stop_playback.is_set() and decoder.wait() != 0:
            raise RuntimeError("ffmpeg 오디오 변환에 실패했습니다")
    except Exception as error:
        chat.reply(f"재생 실패: {error}")
    finally:
        stop_playback.set()
        try:
            chat.vox_audio_stop()
        finally:
            stop_process(decoder)
            stop_process(downloader)
            playback_lock.release()


@bot.on_event("message")
def on_message(chat):
    command = chat.message.command

    if command == "!보이스":
        chat.vox_create_voice_room(title=VOICE_ROOM_TITLE)
        chat.reply(f"보이스룸을 열었습니다: {VOICE_ROOM_TITLE}")
    elif command == "!입장":
        chat.vox_join_voice_room()
        chat.reply("보이스룸에 입장했습니다.")
    elif command == "!재생":
        if not chat.message.has_param:
            chat.reply("사용법: !재생 <YouTube URL 또는 검색어>")
            return
        play(chat, chat.message.param)
    elif command == "!정지":
        stop_playback.set()
        chat.vox_audio_stop()
        chat.reply("재생을 중지했습니다.")
    elif command == "!나가기":
        stop_playback.set()
        chat.vox_audio_stop()
        chat.vox_leave(kind="voiceroom")
        chat.reply("보이스룸에서 나갔습니다.")


bot.run()
```

명령어 예시는 `!보이스`, `!재생 ELEVATE`, `!정지`, `!나가기` 순서입니다.
오픈채팅방에 이미 생성된 보이스룸이 있다면 `!입장`을 사용합니다. 저작권 및
서비스 이용약관상 재생할 수 있는 음원만 사용해야 합니다.

### 멘션을 자동 생성하는 `custom_text`

일반 텍스트에 멘션을 넣을 때는 `custom_reply`의 `attachment`를 직접
만들 필요 없이 템플릿 플레이스홀더를 사용할 수 있습니다.

```python
chat.custom_text(
    "{sender} 님 안녕하세요!",
    mentions={"sender": chat.sender},
)
```

위 코드는 `chat.sender.id`와 `chat.sender.name`을 읽어 다음을 자동
처리합니다.

- `{sender}`를 `@<닉네임>`으로 치환
- KakaoTalk `attachment.mentions` 생성
- `@` 등장 순서에 따른 `at`와 이모지를 포함한 UTF-16 `len` 자동 계산
- 같은 사용자가 여러 번 등장해도 각 위치를 독립 멘션으로 생성

여러 사용자도 각각 이름을 붙여 멘션할 수 있습니다.

```python
chat.custom_text(
    "{sender} 님과 {manager} 님, 확인해 주세요.",
    mentions={
        "sender": chat.sender,
        "manager": manager_user,
    },
)
```

`User` 객체가 없으면 `Mention` 객체로 ID와 표시 닉네임을 직접
지정합니다.

```python
from iris import Mention

chat.custom_text(
    "{target} 님 반갑습니다.",
    mentions={
        "target": Mention(
            user_id="7626329973288865709",
            nickname="사용자😀",
        )
    },
)
```

문자열에 실제 `{` 또는 `}`를 넣으려면 `{{`, `}}`로 작성합니다.
플레이스홀더가 누락되었거나 사용되지 않은 멘션 대상이 있으면
잘못된 사용자를 멘션하지 않도록 전송 전에 `ValueError`를 발생시킵니다.

### `custom_reply` 저수준 파라미터

`custom_reply`는 KakaoTalk `chat_sending_logs`에 들어가는 필드를 기준으로 받습니다.
멘션의 순번을 직접 제어해야 하는 경우에만 이 저수준 메서드를 사용하면 됩니다.
각 인자와 실제 Noa `custom` 데이터의 대응은 다음과 같습니다.

| Python 인자 | Noa `data` 필드 | 필수 | 설명 |
|---|---|---:|---|
| `room_id` | `chat_id` | 예 | 대상 채팅방 ID. 외부 `room`에도 같은 값이 들어갑니다. |
| `message_type` | `type` | 예 | KakaoTalk 메시지 타입. 일반 텍스트는 `1`입니다. |
| `message` | `message` | 아니오 | 말풍선에 표시할 문자열. |
| `attachment` | `attachment` | 아니오 | 멘션 등 메시지 타입별 첨부 JSON. 기본값은 `{}`. |
| `supplement` | `supplement` | 아니오 | KakaoTalk supplement JSON. 보통 `None`. |
| `thread_id` | `thread_id` | 아니오 | 스레드 메시지 ID. 보통 `None`. |
| `scope` | `scope` | 아니오 | 메시지 scope. 기본값 `1`. |
| `v` | `v` | 아니오 | KakaoTalk 메타데이터 JSON. 보통 `None`. |
| `is_silence` | `is_silence` | 아니오 | 조용한 메시지 표시. 기본값 `0`. |
| `created_at` | `created_at` | 아니오 | Unix 초 단위 생성 시각. 생략 시 Noa가 현재 시각을 사용합니다. |
| `client_message_id` | `client_message_id` | 아니오 | 양수이며 기존 값과 중복되지 않아야 합니다. 보통 생략하여 Noa가 생성하게 합니다. |

예를 들어 발신자 `@사용자😀`를 실제 KakaoTalk 멘션으로 표시하려면
`attachment.mentions` 안에 사용자 ID, 멘션 순번, UTF-16 기준 닉네임 길이를 넣습니다.

```python
def utf16_length(text: str) -> int:
    return len(text.encode("utf-16-le")) // 2


nickname = chat.sender.name
mention = f"@{nickname}"

chat.custom_reply(
    message_type=1,
    message=f"{mention} 님 안녕하세요!",
    attachment={
        "mentions": [
            {
                "user_id": int(chat.sender.id),
                # 메시지에서 첫 번째로 등장하는 멘션
                "at": [1],
                # @를 제외한 닉네임의 UTF-16 길이
                "len": utf16_length(nickname),
            }
        ]
    },
    supplement=None,
    thread_id=None,
    scope=1,
    v=None,
    is_silence=0,
)
```

위 호출은 Iris `/reply`에 다음 형태로 전송됩니다. `ChatContext`를
사용하면 `room`/`chat_id`는 현재 채팅방 ID로 자동 설정됩니다.

```json
{
  "type": "custom",
  "room": "18422091737011039",
  "data": {
    "type": 1,
    "message": "@사용자😀 님 안녕하세요!",
    "attachment": {
      "mentions": [{"user_id": 7626329973288865709, "at": [1], "len": 5}]
    },
    "supplement": null,
    "chat_id": "18422091737011039",
    "thread_id": null,
    "scope": 1,
    "v": null,
    "is_silence": 0
  }
}
```

`attachment`, `supplement`, `v`는 Python `dict` 또는 유효한 JSON 문자열을
받습니다. `attachment`의 세부 스키마는 `message_type`에 따라 다르며,
Noa가 임의의 KakaoTalk 첨부 형식을 변환해 주지는 않습니다.

`ChatContext`에서도 현재 채팅방을 자동으로 사용하는 편의 메서드를 제공합니다.

```python
@bot.on_event("message")
def on_message(chat):
    if chat.message.command == "!markdown":
        chat.reply_markdown("**Noa Markdown**")
    elif chat.message.command == "!kick":
        chat.kick_member(user_id="7626329973288865709")
    elif chat.message.command == "!hide":
        # 현재 명령 메시지를 가립니다. 다른 메시지는 log_id를 넘깁니다.
        chat.hide_message()
    elif chat.message.command == "!profile":
        result = chat.share_member_open_profile(
            "7626329973288865709",
            mode="hook",
        )
        chat.reply(result["url"])

# 현재 채팅방에서 나가기
# chat.leave_room()
```

오픈채팅 메시지 가리기는 Noa의 KakaoTalk 후킹 모드와 방장 권한이 필요합니다.
API 객체에서는 `api.hide_message(room_id, log_id)`, 이벤트 컨텍스트에서는
`chat.hide_message()` 또는 `chat.hide_message(log_id)`를 사용합니다.

Noa prefix를 변경해 설치했다면 클라이언트에도 동일하게 지정합니다.

```python
api = IrisAPI("http://127.0.0.1:3000", noa_prefix="/custom-noa")
bot = Bot("127.0.0.1:3000", noa_prefix="/custom-noa")
```

## `iris.Bot`

Iris 봇을 생성하고 관리하기 위한 메인 클래스입니다.

**초기화:**

```python
Bot(
    iris_url: str,
    *,
    max_workers: int = None,
    noa_prefix: str = "/noa",
    timeout: float | tuple[float, float] | None = 30.0,
)
```

- `iris_url` (str): Iris 서버의 URL (예: "127.0.0.1:3000").
- `max_workers` (int, optional): 이벤트를 처리하는 데 사용할 최대 스레드 수.
- `noa_prefix` (str, optional): Iris에 연결된 Noa 확장 경로. 기본값은 `"/noa"`.
- `timeout` (float, tuple, None, optional): Iris/Noa HTTP 요청 타임아웃. 기본값은 `30.0`.
  `(connect, read)` 튜플 또는 제한을 두지 않는 `None`도 사용할 수 있습니다.

**메서드:**

- `run()`: 봇을 시작하고 Iris 서버에 연결합니다. 이 메서드는 블로킹 방식입니다.
- `on_event(name: str)`: 이벤트 핸들러를 등록하기 위한 데코레이터입니다.

**이벤트:**

- `chat`: 수신된 모든 메시지에 대해 트리거됩니다.
- `message`: 표준 메시지에 대해 트리거됩니다.
- `new_member`: 새 멤버가 채팅방에 참여할 때 트리거됩니다.
- `del_member`: 멤버가 채팅방을 나갈 때 트리거됩니다.
- `unknown`: 알 수 없는 이벤트 유형에 대해 트리거됩니다.
- `error`: 이벤트 핸들러에서 오류가 발생할 때 트리거됩니다.

---

## `iris.bot.models.Message`

채팅방의 메시지를 나타냅니다.

**속성:**

- `id` (int): 메시지 ID.
- `type` (int): 메시지 유형.
- `msg` (str): 메시지 내용.
- `attachment` (dict): 메시지 첨부 파일.
- `v` (dict): 추가 메시지 데이터.
- `command` (str): 메시지의 명령어 부분 (첫 번째 단어).
- `param` (str): 메시지의 매개변수 부분 (나머지 메시지).
- `has_param` (bool): 메시지에 매개변수가 있는지 여부.
- `image` (ChatImage): 메시지가 이미지인 경우 `ChatImage` 객체, 그렇지 않으면 `None`.

---

## `iris.bot.models.Room`

채팅방을 나타냅니다.

**속성:**

- `id` (int): 방 ID.
- `name` (str): 방 이름.
- `type` (str): 방 유형 (예: "MultiChat", "DirectChat"). 이 속성은 캐시됩니다.

---

## `iris.bot.models.User`

사용자를 나타냅니다.

**속성:**

- `id` (int): 사용자 ID.
- `name` (str): 사용자 이름. 이 속성은 캐시됩니다.
- `avatar` (Avatar): 사용자의 `Avatar` 객체.
- `type` (str): 채팅방에서의 사용자 유형 (예: "HOST", "MANAGER", "NORMAL"). 이 속성은 캐시됩니다.

---

## `iris.bot.models.Avatar`

사용자의 아바타를 나타냅니다.

**속성:**

- `url` (str): 아바타 이미지의 URL. 이 속성은 캐시됩니다.
- `img` (bytes): 아바타 이미지 데이터 (바이트). 이 속성은 캐시됩니다.

---

## `iris.bot.models.ChatImage`

채팅 메시지의 이미지를 나타냅니다.

**속성:**

- `url` (list[str]): 이미지의 URL 목록.
- `img` (list[Image.Image]): 이미지의 `PIL.Image.Image` 객체 목록. 이 속성은 캐시됩니다.

---

## `iris.bot.models.ChatContext`

채팅 이벤트의 컨텍스트를 나타냅니다.

**속성:**

- `room` (Room): 이벤트가 발생한 `Room`.
- `sender` (User): 메시지를 보낸 `User`.
- `message` (Message): `Message` 객체.
- `raw` (dict): 원시 이벤트 데이터.
- `api` (IrisAPI): Iris 서버와 상호 작용하기 위한 `IrisAPI` 인스턴스.

**메서드:**

- `reply(message: str, room_id: int = None)`: 채팅방에 답장을 보냅니다.
- `reply_media(files: list, room_id: int = None)`: 채팅방에 미디어 파일을 보냅니다.
- `hide_message(log_id: int | str | None = None)`: 지정한 메시지를 가립니다. 생략하면 현재 메시지를 사용합니다.
- `get_source()`: 답장하는 메시지의 `ChatContext`를 반환합니다.
- `get_next_chat(n: int = 1)`: 채팅 기록에서 다음 메시지의 `ChatContext`를 반환합니다.
- `get_previous_chat(n: int = 1)`: 채팅 기록에서 이전 메시지의 `ChatContext`를 반환합니다.

---

## `iris.bot.models.ErrorContext`

오류 이벤트의 컨텍스트를 나타냅니다.

**속성:**

- `event` (str): 오류가 발생한 이벤트의 이름.
- `func` (Callable): 오류를 발생시킨 이벤트 핸들러 함수.
- `exception` (Exception): 예외 객체.
- `args` (list): 이벤트 핸들러에 전달된 인수.

---

## `iris.kakaolink.IrisLink`

카카오링크 메시지를 보내기 위한 클래스입니다.

**초기화:**

```python
IrisLink(iris_url: str)
```

- `iris_url` (str): Iris 서버의 URL.

**메서드:**

- `send(receiver_name: str, template_id: int, template_args: dict, **kwargs)`: 카카오링크 메시지를 보냅니다.

**예제:**

```python
from iris import IrisLink

link = IrisLink("127.0.0.1:3000")
link.send(
    receiver_name="내 채팅방",
    template_id=12345,
    template_args={"key": "value"}
)
```

---

## `iris.util.PyKV`

SQLite를 사용하는 간단한 키-값 저장소입니다. 이 클래스는 싱글톤입니다.

**메서드:**

- `get(key: str)`: 저장소에서 값을 검색합니다.
- `put(key: str, value: any)`: 키-값 쌍을 저장합니다.
- `delete(key: str)`: 키-값 쌍을 삭제합니다.
- `search(searchString: str)`: 값에서 문자열을 검색합니다.
- `search_json(valueKey: str, searchString: str)`: JSON 객체의 값에서 문자열을 검색합니다.
- `search_key(searchString: str)`: 키에서 문자열을 검색합니다.
- `list_keys()`: 모든 키의 목록을 반환합니다.
- `close()`: 데이터베이스 연결을 닫습니다.

## `iris.decorators`

함수에 추가적인 기능을 제공하는 데코레이터입니다.

- `@has_param`: 메시지에 파라미터가 있는 경우에만 함수를 실행합니다.
- `@is_reply`: 메시지가 답장일 경우에만 함수를 실행합니다. 답장이 아닐 경우 "메세지에 답장하여 요청하세요."라는 메시지를 자동으로 보냅니다.
- `@is_admin`: 메시지를 보낸 사용자가 관리자인 경우에만 함수를 실행합니다.
- `@is_not_banned`: 메시지를 보낸 사용자가 차단되지 않은 경우에만 함수를 실행합니다.

## Special Thanks
Irispy2 and Kakaolink by @ye-seola
