"""python -m examples.noa.kick --room 123 --user 456"""
from ._common import client, parser, positive_id, show


def main():
    cli = parser("내부 후킹으로 오픈채팅 사용자 강퇴", room=True)
    target = cli.add_mutually_exclusive_group(required=True)
    target.add_argument("--user", type=positive_id, help="참여 중이거나 이미 나간 사용자의 ID")
    target.add_argument("--nickname", help="현재 참여자 목록에서 검색할 닉네임")
    args = cli.parse_args()
    # The same API handles present and departed users. KakaoTalk hooking is required.
    show(client().kick_member(args.room, user_id=args.user, nickname=args.nickname))


if __name__ == "__main__":
    main()
