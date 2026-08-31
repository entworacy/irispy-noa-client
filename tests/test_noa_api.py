import unittest
from io import BytesIO
from unittest.mock import Mock, patch

from iris import ChatContext, IrisAPI, IrisError, Mention


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
    def test_hide_message_uses_room_and_log_path(self, post):
        post.return_value = response(payload={"ok": True, "accepted": True})

        result = self.api.hide_message(18422091737011039, 7626329973288865709)

        self.assertTrue(result["accepted"])
        post.assert_called_once_with(
            "http://127.0.0.1:3000/custom-noa/rooms/18422091737011039/messages/7626329973288865709/hide",
            json=None,
            timeout=12.5,
        )

    def test_hide_message_rejects_invalid_ids(self):
        with self.assertRaises(ValueError):
            self.api.hide_message(0, 1)
        with self.assertRaises(ValueError):
            self.api.hide_message(1, "not-a-number")

    def test_chat_context_hides_current_or_explicit_message(self):
        api = Mock()
        chat = ChatContext(
            room=Mock(id=123),
            sender=Mock(),
            message=Mock(id=456),
            raw={},
            api=api,
        )

        chat.hide_message()
        chat.hide_message(789)

        self.assertEqual(
            api.hide_message.call_args_list,
            [unittest.mock.call(123, 456), unittest.mock.call(123, 789)],
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
    def test_custom_text_generates_mention_ordinals_and_utf16_lengths(self, post):
        post.return_value = response(payload={"success": True})

        self.api.custom_text(
            123,
            "{sender} 님, {sender}! {{ok}}",
            mentions={"sender": Mention(99, "사용자😀")},
        )

        data = post.call_args.kwargs["json"]["data"]
        self.assertEqual(data["type"], 1)
        self.assertEqual(data["message"], "@사용자😀 님, @사용자😀! {ok}")
        self.assertEqual(
            data["attachment"],
            {
                "mentions": [
                    {"user_id": 99, "at": [1], "len": 5},
                    {"user_id": 99, "at": [2], "len": 5},
                ]
            },
        )

    @patch("iris.bot._internal.iris.requests.post")
    def test_custom_text_numbers_distinct_mentions_in_render_order(self, post):
        post.return_value = response(payload={"success": True})

        self.api.custom_text(
            123,
            "😀 {sender} 님과 {manager} 님, {sender}",
            mentions={
                "sender": Mention(99, "사용자😀"),
                "manager": Mention(100, "관리자"),
            },
        )

        data = post.call_args.kwargs["json"]["data"]
        self.assertEqual(
            data["message"],
            "😀 @사용자😀 님과 @관리자 님, @사용자😀",
        )
        self.assertEqual(
            data["attachment"],
            {
                "mentions": [
                    {"user_id": 99, "at": [1], "len": 5},
                    {"user_id": 100, "at": [2], "len": 3},
                    {"user_id": 99, "at": [3], "len": 5},
                ]
            },
        )

    @patch("iris.bot._internal.iris.requests.post")
    def test_custom_text_counts_literal_at_signs(self, post):
        post.return_value = response(payload={"success": True})

        self.api.custom_text(
            123,
            "문의@test {sender}",
            mentions={"sender": Mention(99, "사용자")},
        )

        data = post.call_args.kwargs["json"]["data"]
        self.assertEqual(data["message"], "문의@test @사용자")
        self.assertEqual(
            data["attachment"],
            {"mentions": [{"user_id": 99, "at": [2], "len": 3}]},
        )

    def test_custom_text_rejects_missing_or_unused_mentions(self):
        with self.assertRaisesRegex(ValueError, "missing"):
            self.api.custom_text(123, "{sender}")
        with self.assertRaisesRegex(ValueError, "unused"):
            self.api.custom_text(
                123,
                "hello",
                mentions={"sender": Mention(99, "user")},
            )

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


class VoxApiTests(unittest.TestCase):
    def setUp(self):
        self.api = IrisAPI(
            "http://127.0.0.1:3000/",
            noa_prefix="custom-noa/",
            timeout=12.5,
        )

    @patch("iris.bot._internal.iris.requests.get")
    def test_status_uses_vox_endpoint(self, get):
        get.return_value = response(payload={"ok": True, "active": True})

        result = self.api.vox_status()

        self.assertTrue(result["active"])
        get.assert_called_once_with(
            "http://127.0.0.1:3000/custom-noa/vox/status",
            timeout=12.5,
        )

    @patch("iris.bot._internal.iris.requests.post")
    def test_voice_talk_keeps_room_and_peer_ids_as_strings(self, post):
        post.return_value = response(payload={"ok": True})

        self.api.vox_start_voice_talk(
            18422091737011039,
            peer_ids=[7626329973288865709, "7626329973288865710"],
        )

        post.assert_called_once_with(
            "http://127.0.0.1:3000/custom-noa/vox/voice-talk",
            json={
                "chatId": "18422091737011039",
                "peerIds": ["7626329973288865709", "7626329973288865710"],
            },
            timeout=12.5,
        )

    @patch("iris.bot._internal.iris.requests.post")
    def test_voice_room_control_endpoints(self, post):
        post.return_value = response(payload={"ok": True})

        self.api.vox_create_voice_room(123, title="테스트 보이스룸")
        self.api.vox_join_voice_room(123)
        self.api.vox_leave(123, kind="voiceroom")

        self.assertEqual(
            post.call_args_list[0].kwargs["json"],
            {"chatId": "123", "title": "테스트 보이스룸"},
        )
        self.assertEqual(
            post.call_args_list[1].kwargs["json"],
            {"chatId": "123"},
        )
        self.assertEqual(
            post.call_args_list[2].kwargs["json"],
            {"chatId": "123", "kind": "voiceroom"},
        )
        self.assertTrue(
            post.call_args_list[0].args[0].endswith("/vox/voice-rooms")
        )
        self.assertTrue(
            post.call_args_list[1].args[0].endswith("/vox/voice-rooms/join")
        )
        self.assertTrue(post.call_args_list[2].args[0].endswith("/vox/leave"))

    @patch("iris.bot._internal.iris.requests.post")
    def test_audio_start_push_and_stop(self, post):
        post.return_value = response(payload={"ok": True})

        self.api.vox_audio_start(mode="mix")
        self.api.vox_audio_push(bytearray([0, 255, 1, 254]))
        self.api.vox_audio_stop()

        self.assertEqual(post.call_args_list[0].kwargs["json"], {"mode": "mix"})
        self.assertEqual(
            post.call_args_list[1].args[0],
            "http://127.0.0.1:3000/custom-noa/vox/audio",
        )
        self.assertEqual(post.call_args_list[1].kwargs["data"], b"\x00\xff\x01\xfe")
        self.assertEqual(
            post.call_args_list[1].kwargs["headers"],
            {"Content-Type": "application/octet-stream"},
        )
        self.assertEqual(post.call_args_list[1].kwargs["timeout"], 12.5)
        self.assertTrue(post.call_args_list[2].args[0].endswith("/vox/audio/stop"))

    @patch("iris.bot._internal.iris.requests.post")
    def test_audio_stream_forwards_source_and_session_constraints(self, post):
        post.return_value = response(payload={"ok": True, "streamedBytes": 4})
        source = BytesIO(b"\x00\x00\x01\x00")

        result = self.api.vox_audio_stream(
            source,
            mode="replace",
            kind="cecall",
            room_id=18422091737011039,
        )

        self.assertEqual(result["streamedBytes"], 4)
        post.assert_called_once_with(
            "http://127.0.0.1:3000/custom-noa/vox/audio/stream",
            params={
                "mode": "replace",
                "kind": "cecall",
                "chatId": "18422091737011039",
            },
            data=source,
            headers={"Content-Type": "application/octet-stream"},
            timeout=12.5,
        )

    def test_vox_inputs_are_validated_before_request(self):
        for pcm in (b"", b"\x00", b"\x00\x00" * 48_001):
            with self.subTest(length=len(pcm)), self.assertRaises(ValueError):
                self.api.vox_audio_push(pcm)
        with self.assertRaises(TypeError):
            self.api.vox_audio_push("not bytes")
        with self.assertRaises(ValueError):
            self.api.vox_audio_start(mode="invalid")
        with self.assertRaises(ValueError):
            self.api.vox_leave(123, kind="invalid")
        with self.assertRaises(TypeError):
            self.api.vox_start_voice_talk(123, peer_ids="456")
        with self.assertRaises(TypeError):
            self.api.vox_audio_stream("audio.pcm")


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

    def test_custom_text_uses_current_room(self):
        self.context.sender.id = 99
        self.context.sender.name = "user"

        self.context.custom_text(
            "{sender} hello",
            mentions={"sender": self.context.sender},
        )

        self.api.custom_text.assert_called_once_with(
            18422091737011039,
            "{sender} hello",
            mentions={"sender": self.context.sender},
        )

    def test_vox_room_methods_use_current_room(self):
        self.context.vox_start_voice_talk(peer_ids=[123, 456])
        self.context.vox_create_voice_room(title="방 이름")
        self.context.vox_join_voice_room()
        self.context.vox_leave(kind="voiceroom")

        self.api.vox_start_voice_talk.assert_called_once_with(
            18422091737011039,
            peer_ids=[123, 456],
        )
        self.api.vox_create_voice_room.assert_called_once_with(
            18422091737011039,
            title="방 이름",
        )
        self.api.vox_join_voice_room.assert_called_once_with(18422091737011039)
        self.api.vox_leave.assert_called_once_with(
            18422091737011039,
            kind="voiceroom",
        )

    def test_vox_stream_requires_current_room(self):
        source = BytesIO(b"\x00\x00")

        self.context.vox_audio_stream(
            source,
            mode="replace",
            kind="cecall",
        )

        self.api.vox_audio_stream.assert_called_once_with(
            source,
            mode="replace",
            kind="cecall",
            room_id=18422091737011039,
        )


if __name__ == "__main__":
    unittest.main()
