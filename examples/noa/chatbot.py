"""python -m examples.noa.chatbot --room 123"""
import os
from urllib.parse import urlsplit

from iris import Bot, ChatContext

from ._common import parser


def main():
    cli = parser("ChatContext를 사용하는 메시지 이벤트 봇", room=True)
    args = cli.parse_args()
    # Bot accepts an IPv4:port endpoint; IrisAPI accepts a full HTTP URL.
    endpoint = urlsplit(os.getenv("IRIS_URL", "http://127.0.0.1:3000"))
    bot = Bot(
        endpoint.netloc,
        noa_prefix=os.getenv("NOA_PREFIX", "/noa"),
        noa_url=os.getenv("NOA_URL", "http://127.0.0.1:4000"),
        noa_token=os.getenv("NOA_API_TOKEN") or None,
        timeout=(5.0, 130.0),
    )

    @bot.on_event("message")
    def on_message(chat: ChatContext):
        if str(chat.room.id) != args.room or chat.sender.id == bot.bot_id:
            return
        command = chat.message.msg.strip()
        if command == "!서식":
            chat.reply_markdown("**Noa RichText**\n*기울임*과 ~~취소선~~")
        elif command == "!리액션":
            chat.react(1)  # React to the command message itself.
        elif command == "!멘션":
            chat.custom_text("{sender} 님 안녕하세요!", mentions={"sender": chat.sender})

    bot.run()


if __name__ == "__main__":
    main()
