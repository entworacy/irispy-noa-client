"""python -m examples.noa.reactions --room 123 --log 456 --reaction-type 1"""
from ._common import client, parser, show


def main():
    cli = parser("메시지에 기본 리액션 또는 이모티콘 추가", room=True, log=True)
    selector = cli.add_mutually_exclusive_group(required=True)
    selector.add_argument("--reaction-type", type=int, choices=range(1, 7))
    selector.add_argument("--emoticon-id", help="카카오톡 이모티콘 항목 ID, Unicode 이모지 문자열과 구분")
    cli.add_argument("--emoticon-type", type=int, choices=(1, 2), default=1,
                     help="1: 일반 이모티콘 리액션, 2: 미니 이모티콘")
    args = cli.parse_args()
    emoticon = None if args.emoticon_id is None else {"type": args.emoticon_type, "id": args.emoticon_id}
    # accepted=true confirms the native callback, not the final DB state.
    show(client().react_message(args.room, args.log, reaction_type=args.reaction_type, emoticon=emoticon))


if __name__ == "__main__":
    main()
