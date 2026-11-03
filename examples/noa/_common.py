"""Shared connection settings; importing examples never sends requests."""

import argparse
import json
import os

from iris import IrisAPI


def client(*, streaming: bool = False) -> IrisAPI:
    return IrisAPI(
        os.getenv("IRIS_URL", "http://127.0.0.1:3000"),
        noa_prefix=os.getenv("NOA_PREFIX", "/noa"),
        noa_url=os.getenv("NOA_URL", "http://127.0.0.1:4000"),
        noa_token=os.getenv("NOA_API_TOKEN") or None,
        # Streaming requests may outlast the regular request timeout.
        timeout=(5.0, None if streaming else 130.0),
    )


def positive_id(value: str) -> str:
    if not value.isascii() or not value.isdecimal() or not 0 < int(value) < 2**63:
        raise argparse.ArgumentTypeError("ID는 양의 64비트 정수여야 합니다")
    return str(int(value))


def parser(description: str, *, room: bool = False, log: bool = False) -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=description)
    if room:
        result.add_argument("--room", required=True, type=positive_id, help="채팅방 ID")
    if log:
        result.add_argument("--log", required=True, type=positive_id, help="메시지 ID")
    return result


def show(result) -> None:
    print(json.dumps(result, ensure_ascii=False, indent=2))
