"""python -m examples.noa.errors"""
import requests
from iris import IrisError

from ._common import client, parser, show


def main():
    parser("Iris 및 Noa 응답 오류와 네트워크 오류 구분").parse_args()
    try:
        show(client().noa_health())
    except IrisError as error:
        raise SystemExit(f"Iris/Noa 요청 거부: {error}") from error
    except requests.Timeout as error:
        # A timeout does not prove that a request was never processed.
        raise SystemExit("응답 시간 초과: 대상 상태를 확인한 후 재시도하세요") from error
    except requests.RequestException as error:
        raise SystemExit(f"연결 오류: {error}") from error


if __name__ == "__main__":
    main()
