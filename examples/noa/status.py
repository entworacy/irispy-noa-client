"""python -m examples.noa.status"""
from ._common import client, parser, show


def main():
    cli = parser("Noa 상태 및 Iris 확장 연결 확인")
    cli.add_argument("--vox", action="store_true", help="음성 기능 상태도 조회")
    args = cli.parse_args()
    api = client()
    show({"health": api.noa_health(), "status": api.noa_status()})
    if args.vox:
        show(api.vox_status())


if __name__ == "__main__":
    main()
