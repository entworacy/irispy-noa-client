"""python -m examples.noa.voice_room create --room 123 --title '음성 대화'"""
from ._common import client, parser, positive_id, show


def main():
    cli = parser("오픈채팅 보이스룸 생성, 입장 또는 퇴장")
    commands = cli.add_subparsers(dest="action", required=True)
    create = commands.add_parser("create")
    create.add_argument("--room", required=True, type=positive_id)
    create.add_argument("--title")
    for action in ("join", "leave"):
        command = commands.add_parser(action)
        command.add_argument("--room", required=True, type=positive_id)
    args = cli.parse_args()
    api = client()
    if args.action == "create":
        show(api.vox_create_voice_room(args.room, title=args.title))
    elif args.action == "join":
        show(api.vox_join_voice_room(args.room))
    else:
        show(api.vox_leave(args.room, kind="voiceroom"))


if __name__ == "__main__":
    main()
