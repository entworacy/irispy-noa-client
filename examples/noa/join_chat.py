"""python -m examples.noa.join_chat --url https://open.kakao.com/o/ROOM --profile 456"""
from ._common import client, parser, positive_id, show


def main():
    cli = parser("선택한 오픈프로필로 오픈채팅 입장")
    cli.add_argument("--url", required=True, help="실제 입장할 오픈채팅 URL")
    cli.add_argument("--profile", type=positive_id, help="profiles list 결과의 프로필 ID")
    args = cli.parse_args()
    show(client().join_open_chat(args.url, profile_id=args.profile))


if __name__ == "__main__":
    main()
