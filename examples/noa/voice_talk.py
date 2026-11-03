"""python -m examples.noa.voice_talk start --room 123 --peer 456"""
from ._common import client, parser, positive_id, show


def main():
    cli = parser("보이스톡 시작 또는 종료")
    commands = cli.add_subparsers(dest="action", required=True)
    start = commands.add_parser("start")
    start.add_argument("--room", required=True, type=positive_id)
    start.add_argument("--peer", action="append", type=positive_id, help="여러 대상이면 반복 지정")
    leave = commands.add_parser("leave")
    leave.add_argument("--room", required=True, type=positive_id)
    args = cli.parse_args()
    api = client()
    if args.action == "start":
        show(api.vox_start_voice_talk(args.room, peer_ids=args.peer))
    else:
        show(api.vox_leave(args.room, kind="cecall"))


if __name__ == "__main__":
    main()
