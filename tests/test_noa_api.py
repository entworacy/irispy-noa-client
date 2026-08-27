import unittest
from unittest.mock import Mock, patch

from iris import ChatContext, IrisAPI, IrisError


def response(status_code=200, payload=None):
    result = Mock()
    result.status_code = status_code
    result.json.return_value = {} if payload is None else payload
    result.text = ""
    return result


class NoaApiTests(unittest.TestCase):
    def setUp(self):
        self.api = IrisAPI(
            "http://127.0.0.1:3000/",
            noa_prefix="custom-noa/",
            timeout=12.5,
        )

    @patch("iris.bot._internal.iris.requests.post")
    def test_kick_member_uses_noa_endpoint_and_string_ids(self, post):
        post.return_value = response(payload={"ok": True, "verified": True})

        result = self.api.kick_member(123, user_id=7626329973288865709)

        self.assertTrue(result["verified"])
        post.assert_called_once_with(
            "http://127.0.0.1:3000/custom-noa/rooms/123/kick",
            json={"userId": "7626329973288865709"},
            timeout=12.5,
        )

    @patch("iris.bot._internal.iris.requests.post")
    def test_markdown_uses_iris_reply(self, post):
        post.return_value = response(payload={"success": True})

        self.api.reply_markdown(123, "**hello**")

        post.assert_called_once_with(
            "http://127.0.0.1:3000/reply",
            json={"type": "markdown", "room": "123", "data": "**hello**"},
            timeout=12.5,
        )

    @patch("iris.bot._internal.iris.requests.post")
    def test_custom_reply_builds_noa_payload(self, post):
        post.return_value = response(payload={"success": True})

        self.api.custom_reply(
            123,
            1,
            "hello",
            attachment={"mentions": []},
            thread_id=456,
        )

        payload = post.call_args.kwargs["json"]
        self.assertEqual(payload["type"], "custom")
        self.assertEqual(payload["room"], "123")
        self.assertEqual(payload["data"]["chat_id"], "123")
        self.assertEqual(payload["data"]["thread_id"], "456")
        self.assertEqual(payload["data"]["attachment"], {"mentions": []})

    @patch("iris.bot._internal.iris.requests.post")
    def test_share_member_profile_keeps_large_ids_as_strings(self, post):
        post.return_value = response(payload={"ok": True, "url": "https://open.kakao.com/me/x"})

        self.api.share_member_open_profile(
            18422091737011039,
            7626329973288865709,
            mode="hook",
        )

        self.assertEqual(
            post.call_args.kwargs["json"],
            {
                "chatId": "18422091737011039",
                "userId": "7626329973288865709",
                "mode": "hook",
            },
        )

    @patch("iris.bot._internal.iris.requests.get")
    def test_get_open_chat_profiles(self, get):
        get.return_value = response(payload={"ok": True, "profiles": []})

        result = self.api.get_open_chat_profiles()

        self.assertEqual(result["profiles"], [])
        get.assert_called_once_with(
            "http://127.0.0.1:3000/custom-noa/open-chat/profiles",
            timeout=12.5,
        )

    @patch("iris.bot._internal.iris.requests.post")
    def test_noa_error_message_is_preserved(self, post):
        post.return_value = response(503, {"error": "Kakao hook unavailable"})

        with self.assertRaisesRegex(IrisError, "Kakao hook unavailable"):
            self.api.kick_member(123, user_id=456)

    def test_validates_required_kick_target_and_mode(self):
        with self.assertRaises(ValueError):
            self.api.kick_member(123)
        with self.assertRaises(ValueError):
            self.api.share_open_profile(123, mode="fast")


class ChatContextNoaTests(unittest.TestCase):
    def setUp(self):
        self.api = Mock(spec=IrisAPI)
        self.context = ChatContext(
            room=Mock(id=18422091737011039),
            sender=Mock(),
            message=Mock(),
            raw={},
            api=self.api,
        )

    def test_share_member_profile_uses_current_room(self):
        self.api.share_member_open_profile.return_value = {
            "url": "https://open.kakao.com/me/x"
        }

        result = self.context.share_member_open_profile(
            7626329973288865709,
            mode="hook",
        )

        self.assertEqual(result["url"], "https://open.kakao.com/me/x")
        self.api.share_member_open_profile.assert_called_once_with(
            18422091737011039,
            7626329973288865709,
            mode="hook",
        )

    def test_leave_room_uses_current_room(self):
        self.context.leave_room()

        self.api.leave_room.assert_called_once_with(18422091737011039)


if __name__ == "__main__":
    unittest.main()
