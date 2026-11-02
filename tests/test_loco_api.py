import base64
import json
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from unittest.mock import Mock, patch

import requests

from iris import Bot, ChatContext, IrisAPI, IrisError
from iris.bot._internal.loco import validate_loco_request

WRITE_RESULT = {
    "ok": True,
    "method": "PING",
    "packetId": 1000,
    "bodyLength": 5,
    "verification": "socket-write",
    "serverConfirmed": False,
}


class LocoValidationTests(unittest.TestCase):
    def test_keeps_supported_bson_types_and_large_ids(self):
        body = {
            "id": 9223372036854775807,
            "negative": -9223372036854775808,
            "long": {"$numberLong": "9223372036854775807"},
            "int": {"$numberInt": "-2147483648"},
            "double": {"$numberDouble": "+1.5e2"},
            "binary": {"$binary": base64.b64encode(b"\0\xff").decode()},
            "values": [None, True, False, 1.5, "한글😀\0", {}, []],
        }
        before = json.dumps(body)
        validate_loco_request("GETTEST1", body)
        self.assertEqual(json.dumps(body), before)
        # A root tag is an ordinary document key, not a scalar wrapper.
        validate_loco_request("PING", {"$numberLong": "a document field"})
        validate_loco_request("PING", {"zero": {"$numberLong": "0" * 5000}})

    def test_rejects_invalid_methods(self):
        for method in ("", "ping", "PING\n", "ABCDEFGHIJKL", "한글", "P-ING", 12, None):
            with self.subTest(method=method), self.assertRaises(ValueError):
                validate_loco_request(method, {})

    def test_rejects_lossy_and_non_json_values(self):
        invalid = [
            [],
            None,
            True,
            {"a": 2**63},
            {"a": -(2**63) - 1},
            {"a": float("nan")},
            {"a": float("inf")},
            {"a": b"bytes"},
            {"a": (1, 2)},
            {"a": {1, 2}},
            {1: "key"},
            {"a\0": 1},
            {"nested": {"a\0": 1}},
            {"a": {"$numberInt": "2147483648"}},
            {"a": {"$numberLong": "9223372036854775808"}},
            {"a": {"$numberLong": 1}},
            {"a": {"$numberLong": " 1"}},
            {"a": {"$numberLong": "１"}},
            {"a": {"$numberLong": "1", "other": 2}},
            {"a": {"$numberDouble": "NaN"}},
            {"a": {"$numberDouble": "1e999"}},
            {"a": {"$numberDouble": "1_000"}},
            {"a": {"$binary": "?"}},
            {"a": {"$binary": "YQ"}},
            {"a": {"$binary": "YR=="}},
        ]
        for body in invalid:
            with self.subTest(body=body), self.assertRaises((TypeError, ValueError)):
                validate_loco_request("PING", body)

    def test_bounds_size_in_utf8_bytes_and_depth(self):
        validate_loco_request("PING", {"a": "x" * (65_536 - 8)})
        with self.assertRaisesRegex(ValueError, "65536"):
            validate_loco_request("PING", {"a": "x" * (65_536 - 7)})
        validate_loco_request("PING", {"a": "😀" * ((65_536 - 8) // 4)})
        with self.assertRaisesRegex(ValueError, "65536"):
            validate_loco_request("PING", {"a": "😀" * (65_536 // 4)})
        value = None
        for _ in range(31):
            value = [value]
        validate_loco_request("PING", {"a": value})
        with self.assertRaisesRegex(ValueError, "32"):
            validate_loco_request("PING", {"a": [value]})
        cycle = {}
        cycle["self"] = cycle
        with self.assertRaisesRegex(ValueError, "32"):
            validate_loco_request("PING", cycle)


class DirectNoaApiTests(unittest.TestCase):
    def setUp(self):
        self.api = IrisAPI(
            "http://127.0.0.1:3000",
            noa_prefix="custom-noa",
            noa_url="https://noa.example/service/",
            noa_token="test-token",
            timeout=(2.0, 12.5),
        )

    @patch("iris.bot._internal.iris.requests.post")
    def test_write_result_is_preserved_without_inventing_server_confirmation(
        self, post
    ):
        post.return_value = Mock(status_code=200)
        post.return_value.json.return_value = WRITE_RESULT
        self.assertEqual(self.api.send_loco("PING", {}), WRITE_RESULT)
        post.assert_called_once_with(
            "https://noa.example/service/api/loco/send",
            json={"method": "PING", "body": {}},
            headers={"Authorization": "Bearer test-token"},
            timeout=(2.0, 12.5),
            allow_redirects=False,
        )

    @patch("iris.bot._internal.iris.requests.post")
    def test_timeout_is_not_retried(self, post):
        post.side_effect = requests.Timeout("write outcome unknown")
        with self.assertRaises(requests.Timeout):
            self.api.send_loco("PING", {})
        self.assertEqual(post.call_count, 1)

    @patch("iris.bot._internal.iris.requests.post")
    def test_noa_error_and_redirect_do_not_trigger_fallback(self, post):
        for status, payload in [
            (401, {"error": "authentication required"}),
            (503, {"error": "hook unavailable"}),
            (307, {"message": "redirect"}),
        ]:
            with self.subTest(status=status):
                post.reset_mock()
                post.return_value = Mock(status_code=status)
                post.return_value.json.return_value = payload
                with self.assertRaises(IrisError):
                    self.api.send_loco("PING", {})
                self.assertEqual(post.call_count, 1)

    @patch("iris.bot._internal.iris.requests.post")
    def test_missing_endpoint_and_bad_body_fail_before_network(self, post):
        with self.assertRaisesRegex(ValueError, "noa_url"):
            IrisAPI("http://127.0.0.1:3000").send_loco("PING", {})
        with self.assertRaises(ValueError):
            self.api.send_loco("PING", {"id": 2**63})
        post.assert_not_called()

    @patch("iris.bot._internal.iris.requests.get")
    def test_packet_list_and_status_use_direct_noa_routes(self, get):
        get.return_value = Mock(status_code=200)
        get.return_value.json.return_value = [{"packetId": 1000}]
        self.assertEqual(self.api.get_loco(limit=15), [{"packetId": 1000}])
        self.assertEqual(get.call_args.args, ("https://noa.example/service/api/loco",))
        self.assertEqual(get.call_args.kwargs["params"], {"limit": 15})
        get.return_value.json.return_value = {"kakaoHookActive": True}
        self.assertTrue(self.api.noa_status()["kakaoHookActive"])
        self.assertEqual(
            get.call_args.args, ("https://noa.example/service/api/status",)
        )
        for limit in (0, 10001, True, "500"):
            with self.subTest(limit=limit), self.assertRaises(ValueError):
                self.api.get_loco(limit=limit)

    def test_endpoint_and_token_configuration(self):
        for value in (
            "",
            "ftp://host",
            "http://user:pass@host",
            "http://host?token=x",
            "http://host/#x",
            "http://host:bad",
            "http://two hosts",
        ):
            with self.subTest(url=value), self.assertRaises(ValueError):
                IrisAPI("http://iris", noa_url=value)
        with self.assertRaises(ValueError):
            IrisAPI("http://iris", noa_token="token")
        api = IrisAPI("http://iris", noa_url="127.0.0.1:4000/")
        self.assertEqual(api.noa_url, "http://127.0.0.1:4000")

    def test_bot_configuration_and_context_do_not_inject_room_into_raw_loco(self):
        bot = Bot("127.0.0.1:3000", noa_url="http://127.0.0.1:4000", noa_token="token")
        self.assertEqual(bot.api.noa_url, "http://127.0.0.1:4000")
        self.assertEqual(bot.api._noa_token, "token")
        api = Mock(spec=IrisAPI)
        api.send_loco.return_value = WRITE_RESULT
        context = ChatContext(
            room=Mock(id=999), sender=Mock(), message=Mock(), raw={}, api=api
        )
        self.assertEqual(context.send_loco("PING", {}), WRITE_RESULT)
        api.send_loco.assert_called_once_with("PING", {})


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        self.respond()

    def do_POST(self):
        self.respond()

    def respond(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
        self.server.received.append(
            (self.path, dict(self.headers), json.loads(body) if body else None)
        )
        payload = (
            WRITE_RESULT
            if self.path.endswith("/api/loco/send")
            else {"success": True, "message": "Enqueued"}
        )
        encoded = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


class WireContractTests(unittest.TestCase):
    def test_real_http_preserves_ids_and_separates_iris_and_noa_authentication(self):
        servers = [HTTPServer(("127.0.0.1", 0), _Handler) for _ in range(2)]
        threads = []
        for server in servers:
            server.received = []
            thread = Thread(
                target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True
            )
            thread.start()
            threads.append(thread)
        iris, noa = servers
        try:
            api = IrisAPI(
                f"http://127.0.0.1:{iris.server_port}",
                noa_url=f"http://127.0.0.1:{noa.server_port}/proxy",
                noa_token="wire-test-token",
                timeout=2.0,
            )
            body = {
                "id": 9223372036854775807,
                "typed": {"$numberLong": "9223372036854775807"},
                "bytes": {"$binary": "AP8="},
                "text": "한글😀\0",
            }
            self.assertEqual(api.send_loco("PING", body), WRITE_RESULT)
            markdown = "**안녕😀** *기울임* ~~취소선~~"
            result = api.reply_markdown(9223372036854775807, markdown)
            self.assertEqual(result, {"success": True, "message": "Enqueued"})
            api.vox_audio_stop()
            self.assertEqual(noa.received[0][0], "/proxy/api/loco/send")
            self.assertEqual(
                noa.received[0][1]["Authorization"], "Bearer wire-test-token"
            )
            self.assertEqual(noa.received[0][2], {"method": "PING", "body": body})
            self.assertEqual(
                iris.received[0][2],
                {"type": "markdown", "room": "9223372036854775807", "data": markdown},
            )
            self.assertEqual(iris.received[1][0], "/noa/vox/audio/stop")
            for _, headers, _ in iris.received:
                self.assertNotIn("Authorization", headers)
        finally:
            for server, thread in zip(servers, threads):
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
