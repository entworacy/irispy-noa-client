"""python -m examples.noa.loco_history --limit 100"""
from ._common import client, parser, show


def main():
    cli = parser("Noa에 캡처된 LOCO 송수신 내역 조회")
    cli.add_argument("--limit", type=int, default=100)
    args = cli.parse_args()
    # packetId and method can help correlate a request with its captured response.
    show(client().get_loco(limit=args.limit))


if __name__ == "__main__":
    main()
