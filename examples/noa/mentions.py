"""python -m examples.noa.mentions --room 123 --user 456 --nickname '사용자😀'"""
from iris import Mention

from ._common import client, parser, positive_id, show


def main():
    cli = parser("UTF-16 멘션 위치를 자동 계산하는 custom_text", room=True)
    cli.add_argument("--user", required=True, type=positive_id)
    cli.add_argument("--nickname", required=True)
    args = cli.parse_args()
    # Repeated placeholders and emoji do not require manual attachment ranges.
    show(client().custom_text(args.room, "😀 {target} 님, 확인해 주세요. 감사합니다, {target} 님!",
                              mentions={"target": Mention(user_id=args.user, nickname=args.nickname)}))


if __name__ == "__main__":
    main()
