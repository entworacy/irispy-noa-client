"""Noa's direct LOCO API and supported JSON/BSON value contract."""

import base64
import binascii
import json
import math
import re
from typing import Any


class LocoMixin:
    def send_loco(self, method: str, body: dict[str, Any]) -> dict:
        """Write one LOCO packet through Noa; the result is not a server ACK.

        Requires ``noa_url`` and, when enabled on Noa, ``noa_token``. The body
        is sent unchanged, including explicit BSON wrappers and room IDs.
        A failed or timed-out write is never retried automatically.
        """
        validate_loco_request(method, body)
        return self._post_noa_direct("api/loco/send", {"method": method, "body": body})

    def get_loco(self, *, limit: int = 500) -> list[dict]:
        """Read captured packets; a sent packet's response may not be captured."""
        if (
            isinstance(limit, bool)
            or not isinstance(limit, int)
            or not 1 <= limit <= 10_000
        ):
            raise ValueError("limit must be an integer between 1 and 10000")
        return self._get_noa_direct("api/loco", params={"limit": limit})

    def noa_status(self) -> dict:
        """Return Noa's hook, Android runtime, and database status."""
        return self._get_noa_direct("api/status")


def validate_loco_request(method: str, body: dict[str, Any]) -> None:
    if not isinstance(method, str) or re.fullmatch(r"[A-Z0-9]{1,11}", method) is None:
        raise ValueError("method must contain 1 to 11 uppercase ASCII letters/digits")
    if not isinstance(body, dict):
        raise TypeError("body must be a JSON object")
    # A document root is not a typed scalar, even if its only key is a tag.
    for key, value in body.items():
        _key(key)
        _value(value, 1)
    encoded = json.dumps(
        body, ensure_ascii=False, allow_nan=False, separators=(",", ":")
    )
    if len(encoded.encode("utf-8")) > 65_536:
        raise ValueError("LOCO body exceeds 65536 JSON bytes")


def _key(key: str) -> None:
    if not isinstance(key, str):
        raise TypeError("BSON keys must be strings")
    if "\0" in key:
        raise ValueError("BSON keys cannot contain NUL")


def _value(value: Any, depth: int) -> None:
    if depth > 32:
        raise ValueError("LOCO body nesting exceeds 32 levels")
    if isinstance(value, dict):
        for key in value:
            _key(key)
        for tag in ("$numberLong", "$numberInt", "$numberDouble", "$binary"):
            if tag in value:
                if len(value) != 1 or not isinstance(value[tag], str):
                    raise ValueError(
                        f"{tag} must be the only field and contain a string"
                    )
                _typed_value(tag, value[tag])
                return
        for child in value.values():
            _value(child, depth + 1)
    elif isinstance(value, list):
        for child in value:
            _value(child, depth + 1)
    elif value is None or isinstance(value, (str, bool)):
        return
    elif isinstance(value, int):
        if not -(2**63) <= value < 2**63:
            raise ValueError("BSON integers must fit in signed 64 bits")
    elif isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("BSON doubles must be finite")
    else:
        raise TypeError("LOCO values must be JSON values; use $binary for bytes")


def _typed_value(tag: str, value: str) -> None:
    valid = False
    if tag in {"$numberLong", "$numberInt"}:
        bits = 64 if tag == "$numberLong" else 32
        if re.fullmatch(r"[+-]?[0-9]+", value):
            digits = value.lstrip("+-").lstrip("0") or "0"
            if len(digits) <= 19:
                parsed = int(digits) * (-1 if value.startswith("-") else 1)
                valid = -(2 ** (bits - 1)) <= parsed < 2 ** (bits - 1)
    elif tag == "$numberDouble":
        if re.fullmatch(
            r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?", value
        ):
            valid = math.isfinite(float(value))
    else:
        try:
            decoded = base64.b64decode(value, validate=True)
            valid = base64.b64encode(decoded).decode("ascii") == value
        except (ValueError, binascii.Error):
            pass
    if not valid:
        raise ValueError(f"invalid {tag} value")
