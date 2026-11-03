"""python -m examples.noa.files --room 123 --local-file ./report.pdf"""
import base64
import mimetypes
from pathlib import Path

from ._common import client, parser, show


def main():
    cli = parser("로컬 파일 또는 Android 기기의 파일 전송", room=True)
    source = cli.add_mutually_exclusive_group(required=True)
    source.add_argument("--local-file", type=Path, help="이 Python 프로그램이 읽을 로컬 파일")
    source.add_argument("--android-path", help="Android 기기의 절대 경로")
    cli.add_argument("--media-object", action="store_true", help="로컬 파일을 Iris 미디어 객체로 전송")
    args = cli.parse_args()
    if args.android_path and args.media_object:
        cli.error("--media-object는 --local-file과 함께 사용합니다")
    api = client()
    if args.android_path:
        show(api.reply_file(args.room, path=args.android_path))
    else:
        mime = mimetypes.guess_type(args.local_file.name)[0] or "application/octet-stream"
        encoded = base64.b64encode(args.local_file.read_bytes()).decode("ascii")
        if args.media_object:
            # Iris v0.33 handles media objects instead of Noa's string/file hook.
            data = {"name": args.local_file.name, "mime": mime, "data": encoded}
        else:
            # Noa handles a Base64 Data URI when its file hook is enabled.
            data = f"data:{mime};base64,{encoded}"
        show(api.reply_file(args.room, data=data))


if __name__ == "__main__":
    main()
