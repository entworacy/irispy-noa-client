"""python -m examples.noa.profiles list"""
from ._common import client, parser, positive_id, show


def main():
    cli = parser("오픈프로필 목록 조회 및 링크 공유")
    commands = cli.add_subparsers(dest="action", required=True)
    commands.add_parser("list", help="사용 가능한 내 오픈프로필 목록")
    own = commands.add_parser("share", help="링크 ID로 오픈프로필 공유 URL 조회")
    own.add_argument("--link", required=True, type=positive_id)
    member = commands.add_parser("member", help="채팅방 참여자의 오픈프로필 URL 조회")
    member.add_argument("--room", required=True, type=positive_id)
    member.add_argument("--user", required=True, type=positive_id)
    args = cli.parse_args()
    api = client()
    if args.action == "list":
        show(api.get_open_chat_profiles())
    elif args.action == "share":
        show(api.share_open_profile(args.link, mode="hook"))
    else:
        show(api.share_member_open_profile(args.room, args.user, mode="hook"))


if __name__ == "__main__":
    main()
