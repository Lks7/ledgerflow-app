from unittest.mock import patch

from django.test import Client, TestCase

from .config_service import get_or_create_config
from .services import test_ai_connection


class AIConfigTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_get_config_page(self):
        response = self.client.get("/ai/config")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "AI 控制台")

    def test_post_save_config(self):
        response = self.client.post(
            "/ai/config",
            {
                "action": "save",
                "provider": "openai",
                "api_base_url": "https://example.com",
                "api_key": "sk-test-123456",
                "model_name": "gpt-4o-mini",
                "system_prompt": "请用简洁语气给建议",
            },
        )
        self.assertEqual(response.status_code, 302)
        config = get_or_create_config()
        self.assertEqual(config.provider, "openai")
        self.assertEqual(config.model_name, "gpt-4o-mini")

    @patch("ai_advisor.services._openai_compatible_generate")
    def test_test_connection_success(self, mock_openai_generate):
        mock_openai_generate.return_value = '{"insight":"ok"}'
        config = get_or_create_config()
        config.provider = "openai"
        config.api_base_url = "https://example.com"
        config.api_key = "sk-test"
        config.model_name = "gpt-4o-mini"
        config.save()

        result = test_ai_connection()
        self.assertTrue(result["ok"])
