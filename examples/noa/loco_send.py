"""python -m examples.noa.loco_send --method PING --body '{}'"""
import json

from ._common import client, parser, show


def main():
    cli = parser("Noa HTTP API를 통한 LOCO 직접 발신")
    cli.add_argument("--method", default="PING")
    cli.add_argument("--body", type=json.loads, default={}, help="LOCO 메서드에 맞는 JSON 객체")
    args = cli.parse_args()
    # No room ID is inserted automatically. Use {"$numberLong":"123"} for BSON int64.
    # A successful socket write does not confirm a successful server operation.
    show(client().send_loco(args.method, args.body))


if __name__ == "__main__":
    main()
