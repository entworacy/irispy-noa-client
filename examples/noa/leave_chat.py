"""python -m examples.noa.leave_chat --room 123"""
from ._common import client, parser, show


def main():
    cli = parser("지정한 채팅방에서 나가기", room=True)
    args = cli.parse_args()
    # This leaves the chat room itself; vox_leave only leaves a voice session.
    show(client().leave_room(args.room))


if __name__ == "__main__":
    main()
