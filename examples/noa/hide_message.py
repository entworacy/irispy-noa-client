"""python -m examples.noa.hide_message --room 123 --log 456"""
from ._common import client, parser, show


def main():
    cli = parser("방장 권한으로 오픈채팅 메시지 가리기", room=True, log=True)
    args = cli.parse_args()
    show(client().hide_message(args.room, args.log))


if __name__ == "__main__":
    main()
