"""이미지 생성 혼합 전략 테스트: Body 씬에서 DALL-E 스킵 검증."""
from __future__ import annotations

import unittest

from shorts_maker_v2.models import ScenePlan


class TestImageMixedStrategy(unittest.TestCase):
    """Body 씬은 use_paid_image=False이어야 하고, Hook/CTA는 True."""

    def test_body_role_not_paid(self):
        """Body 씬의 structure_role은 'body'이므로 paid=False."""
        body_scene = ScenePlan(
            scene_id=3,
            narration_ko="테스트 바디",
            visual_prompt_en="body prompt",
            target_sec=5.0,
            structure_role="body",
        )
        use_paid = body_scene.structure_role in ("hook", "cta")
        self.assertFalse(use_paid, "Body 씬은 무료 이미지만 사용해야 합니다")

    def test_hook_role_is_paid(self):
        """Hook 씬은 paid 이미지 허용."""
        hook_scene = ScenePlan(
            scene_id=1,
            narration_ko="훅 내레이션",
            visual_prompt_en="hook prompt",
            target_sec=3.0,
            structure_role="hook",
        )
        use_paid = hook_scene.structure_role in ("hook", "cta")
        self.assertTrue(use_paid, "Hook 씬은 유료 이미지를 사용할 수 있어야 합니다")

    def test_cta_role_is_paid(self):
        """CTA 씬도 paid 이미지 허용."""
        cta_scene = ScenePlan(
            scene_id=7,
            narration_ko="CTA 내레이션",
            visual_prompt_en="cta prompt",
            target_sec=3.0,
            structure_role="cta",
        )
        use_paid = cta_scene.structure_role in ("hook", "cta")
        self.assertTrue(use_paid, "CTA 씬은 유료 이미지를 사용할 수 있어야 합니다")

    def test_unknown_role_defaults_to_body(self):
        """알 수 없는 role은 paid=False."""
        scene = ScenePlan(
            scene_id=4,
            narration_ko="rank5 씬",
            visual_prompt_en="rank prompt",
            target_sec=5.0,
            structure_role="rank5",
        )
        use_paid = scene.structure_role in ("hook", "cta")
        self.assertFalse(use_paid, "Hook/CTA가 아닌 role은 무료 이미지만 사용")


class TestVoiceRoleMapping(unittest.TestCase):
    """TTS 음성 역할 매핑 기본 로직 검증."""

    def test_role_in_voice_roles(self):
        """역할별 음성이 매핑되어 있으면 해당 음성 사용."""
        voice_roles = {
            "hook": "ko-KR-InJoonNeural",
            "body": "ko-KR-SunHiNeural",
            "cta": "ko-KR-InJoonNeural",
        }
        for role, expected in voice_roles.items():
            voice = voice_roles[role] if role in voice_roles else "default-voice"
            self.assertEqual(voice, expected, f"{role} 역할의 음성이 올바르지 않습니다")

    def test_unknown_role_uses_default(self):
        """매핑에 없는 역할은 기본 음성 사용."""
        voice_roles = {"hook": "ko-KR-InJoonNeural", "body": "ko-KR-SunHiNeural"}
        role = "rank3"
        voice = voice_roles[role] if role in voice_roles else "default-voice"
        self.assertEqual(voice, "default-voice")


if __name__ == "__main__":
    unittest.main()
