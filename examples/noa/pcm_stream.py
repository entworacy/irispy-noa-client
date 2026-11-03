"""python -m examples.noa.pcm_stream --room 123 --kind voiceroom --file audio.pcm"""
from pathlib import Path

from ._common import client, parser, show


def main():
    cli = parser("활성 음성 세션으로 48 kHz mono s16le PCM 스트리밍", room=True)
    cli.add_argument("--kind", required=True, choices=("cecall", "voiceroom"))
    cli.add_argument("--file", required=True, type=Path, help="WAV 헤더가 없는 raw PCM 파일")
    cli.add_argument("--mode", choices=("replace", "mix"), default="replace")
    args = cli.parse_args()
    if args.file.stat().st_size == 0 or args.file.stat().st_size % 2:
        cli.error("PCM 파일은 비어 있지 않고 크기가 2바이트 단위여야 합니다")
    # Establish the voice session first with voice_talk or voice_room.
    # Noa checks the target session, paces playback and stops injection on completion.
    with args.file.open("rb") as pcm:
        show(client(streaming=True).vox_audio_stream(
            pcm, mode=args.mode, kind=args.kind, room_id=args.room))


if __name__ == "__main__":
    main()
