import unittest
from unittest.mock import Mock, patch

from iris import ChatContext, IrisAPI, IrisError


class ReplyFormatTests(unittest.TestCase):
    def setUp(self):
        self.api = IrisAPI("http://127.0.0.1:3000", timeout=10.0)

    @patch("iris.bot._internal.iris.requests.post")
    def test_file_formats_follow_noa_and_iris_contracts(self, post):
        post.return_value = Mock(status_code=200)
        post.return_value.json.return_value = {"success": True, "message": "Enqueued"}
        cases = [
            ({"data": b"\0\xff"}, {"data": "AP8="}),
            ({"data": memoryview(b"abc")}, {"data": "YWJj"}),
            (
                {"data": "data:text/plain;name=test.txt;base64,YQ=="},
                {"data": "data:text/plain;name=test.txt;base64,YQ=="},
            ),
            (
                {"path": "/sdcard/Download/report.pdf"},
                {"path": "/sdcard/Download/report.pdf"},
            ),
            (
                {
                    "data": {
                        "name": "문서.pdf",
                        "mime": "application/pdf",
                        "data": "YQ==",
                    }
                },
                {
                    "data": {
                        "name": "문서.pdf",
                        "mime": "application/pdf",
                        "data": "YQ==",
                    }
                },
            ),
            (
                {"data": [{"filename": "a.txt", "b64": "YQ=="}]},
                {"data": [{"filename": "a.txt", "b64": "YQ=="}]},
            ),
        ]
        for arguments, fields in cases:
            with self.subTest(arguments=arguments):
                result = self.api.reply_file(9223372036854775807, **arguments)
                self.assertEqual(result["message"], "Enqueued")
                self.assertNotIn("verified", result)
                self.assertEqual(post.call_args.args, ("http://127.0.0.1:3000/reply",))
                self.assertEqual(
                    post.call_args.kwargs["json"],
                    {"type": "file", "room": "9223372036854775807", **fields},
                )
                self.assertEqual(post.call_args.kwargs["timeout"], 10.0)

    @patch("iris.bot._internal.iris.requests.post")
    def test_invalid_file_input_does_not_send(self, post):
        for arguments in (
            {},
            {"data": b""},
            {"data": []},
            {"data": 1},
            {"path": "relative.txt"},
            {"path": "/bad\0path"},
            {"data": "YQ==", "path": "/a.txt"},
        ):
            with (
                self.subTest(arguments=arguments),
                self.assertRaises((ValueError, TypeError)),
            ):
                self.api.reply_file(123, **arguments)
        post.assert_not_called()

    @patch("iris.bot._internal.iris.requests.post")
    def test_enqueue_and_legacy_reply_responses_are_returned_unchanged(self, post):
        post.return_value = Mock(status_code=200)
        for payload in (
            {"success": True, "message": "Enqueued"},
            {"success": True, "message": "success"},
        ):
            post.return_value.json.return_value = payload
            self.assertEqual(self.api.reply_markdown(123, "**굵게😀**"), payload)
            self.assertEqual(self.api.custom_reply(123, 1, "message"), payload)
            self.assertEqual(post.call_args.kwargs["json"]["data"]["chat_id"], "123")

    @patch("iris.bot._internal.iris.requests.post")
    def test_http_200_application_failures_raise_iris_error(self, post):
        post.return_value = Mock(status_code=200)
        for payload in (
            {"success": False, "message": "Unknown reply type"},
            {"ok": False, "error": "failed"},
        ):
            with self.subTest(payload=payload):
                post.return_value.json.return_value = payload
                with self.assertRaises(IrisError):
                    self.api.reply_file(123, data=b"abc")

    @patch("iris.bot._internal.iris.requests.post")
    def test_non_object_error_and_malformed_json_are_reported(self, post):
        post.return_value = Mock(status_code=503, text="invalid JSON")
        post.return_value.json.return_value = ["upstream failure"]
        with self.assertRaises(IrisError):
            self.api.reply_markdown(123, "text")
        post.return_value.json.side_effect = ValueError("bad JSON")
        with self.assertRaises(IrisError):
            self.api.reply_markdown(123, "text")

    def test_context_file_uses_current_or_explicit_room(self):
        api = Mock(spec=IrisAPI)
        chat = ChatContext(
            room=Mock(id=123), sender=Mock(), message=Mock(), raw={}, api=api
        )
        chat.reply_file(path="/sdcard/a.txt")
        api.reply_file.assert_called_with(123, data=None, path="/sdcard/a.txt")
        chat.reply_file(data=b"abc", room_id="456")
        api.reply_file.assert_called_with("456", data=b"abc", path=None)


if __name__ == "__main__":
    unittest.main()
