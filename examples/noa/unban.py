"""python -m examples.noa.unban --room 123 --user 456"""
from ._common import client, parser, positive_id, show


def main():
    cli = parser("오픈채팅 사용자의 강퇴 제한 해제", room=True)
    cli.add_argument("--user", required=True, type=positive_id)
    args = cli.parse_args()
    # Noa verifies the native callback and the matching KLDELITEM response.
    show(client().unban_member(args.room, args.user))


if __name__ == "__main__":
    main()
