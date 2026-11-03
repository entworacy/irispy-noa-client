"""python -m examples.noa.richtext --room 123 --text '**Hello**'"""
from ._common import client, parser, show


def main():
    cli = parser("Markdown 입력으로 RichText 전송", room=True)
    cli.add_argument("--text", default="**안녕하세요** 😀\n*기울임*과 ~~취소선~~")
    args = cli.parse_args()
    # Noa selects the native RichText transport on KakaoTalk 26.9.x.
    # Iris's Enqueued response is an acknowledgement, not delivery confirmation.
    show(client().reply_markdown(args.room, args.text))


if __name__ == "__main__":
    main()
