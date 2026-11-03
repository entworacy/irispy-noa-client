"""python -m examples.noa.custom_message --room 123 --text Hello"""
import json

from ._common import client, parser, positive_id, show


def main():
    cli = parser("custom 메시지와 선택적 attachment 전송", room=True)
    cli.add_argument("--text", required=True)
    cli.add_argument("--attachment", type=json.loads, default={}, help="JSON 객체")
    cli.add_argument("--thread", type=positive_id, help="선택적 스레드 ID")
    args = cli.parse_args()
    if not isinstance(args.attachment, dict):
        cli.error("--attachment는 JSON 객체여야 합니다")
    show(client().custom_reply(args.room, message_type=1, message=args.text,
                               attachment=args.attachment, thread_id=args.thread))


if __name__ == "__main__":
    main()
