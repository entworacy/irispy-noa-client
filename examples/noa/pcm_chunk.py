"""python -m examples.noa.pcm_chunk --file one-second.pcm --mode mix"""
import time
from pathlib import Path

from ._common import client, parser, show


def main():
    cli = parser("현재 활성 음성 세션으로 단일 PCM 청크 송출")
    cli.add_argument("--file", required=True, type=Path, help="48 kHz mono s16le, 최대 96,000바이트")
    cli.add_argument("--mode", choices=("replace", "mix"), default="replace")
    args = cli.parse_args()
    pcm = args.file.read_bytes()
    if not pcm or len(pcm) % 2 or len(pcm) > 96_000:
        cli.error("PCM 청크는 2바이트 단위이며 1~96,000바이트여야 합니다")
    api = client()
    show(api.vox_status())
    show(api.vox_audio_start(mode=args.mode))
    try:
        show(api.vox_audio_push(pcm))
        # Stop clears queued audio; allow this short chunk time to play first.
        time.sleep(len(pcm) / 96_000 + 0.1)
    finally:
        api.vox_audio_stop()


if __name__ == "__main__":
    main()
