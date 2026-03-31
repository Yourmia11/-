"""
tests/test_security.py
------------------------
測試絕對防護模組 (security.py)
"""

import time
import pytest
from xiao_qian.security import (
    RateLimiter,
    InputSanitizer,
    TokenAuthenticator,
    SecurityGuard,
)


# ---------------------------------------------------------------------------
# RateLimiter
# ---------------------------------------------------------------------------

class TestRateLimiter:
    def test_allows_within_limit(self):
        rl = RateLimiter(max_calls=5, window_sec=60)
        for _ in range(5):
            assert rl.is_allowed("user1") is True

    def test_blocks_over_limit(self):
        rl = RateLimiter(max_calls=3, window_sec=60)
        for _ in range(3):
            rl.is_allowed("user2")
        assert rl.is_allowed("user2") is False

    def test_different_identities_independent(self):
        rl = RateLimiter(max_calls=1, window_sec=60)
        assert rl.is_allowed("a") is True
        assert rl.is_allowed("b") is True   # 不同身份互不影響

    def test_window_resets(self):
        rl = RateLimiter(max_calls=1, window_sec=0.05)
        rl.is_allowed("x")
        assert rl.is_allowed("x") is False
        time.sleep(0.1)
        assert rl.is_allowed("x") is True   # 視窗重置後應允許


# ---------------------------------------------------------------------------
# InputSanitizer
# ---------------------------------------------------------------------------

class TestInputSanitizer:
    def test_removes_html_tags(self):
        result = InputSanitizer.clean("<script>alert(1)</script>hello")
        assert "<script>" not in result
        assert "hello" in result

    def test_removes_sql_fragments(self):
        result = InputSanitizer.clean("SELECT * FROM users; DROP TABLE users;--")
        assert "--" not in result
        assert ";" not in result

    def test_removes_control_characters(self):
        result = InputSanitizer.clean("hello\x00world\x1f!")
        assert "\x00" not in result
        assert "\x1f" not in result

    def test_clean_text_unchanged(self):
        text = "今天天氣很好，主人要加油！"
        assert InputSanitizer.clean(text) == text

    def test_strips_whitespace(self):
        result = InputSanitizer.clean("  hello  ")
        assert result == "hello"


# ---------------------------------------------------------------------------
# TokenAuthenticator
# ---------------------------------------------------------------------------

class TestTokenAuthenticator:
    def test_verify_valid_token(self):
        auth = TokenAuthenticator(secret="test-secret")
        token = auth.generate_token("payload123")
        assert auth.verify_token("payload123", token) is True

    def test_reject_invalid_token(self):
        auth = TokenAuthenticator(secret="test-secret")
        assert auth.verify_token("payload123", "wrongtoken") is False

    def test_different_payloads_different_tokens(self):
        auth = TokenAuthenticator(secret="test-secret")
        t1 = auth.generate_token("aaa")
        t2 = auth.generate_token("bbb")
        assert t1 != t2

    def test_tampered_payload_rejected(self):
        auth = TokenAuthenticator(secret="test-secret")
        token = auth.generate_token("original")
        assert auth.verify_token("tampered", token) is False


# ---------------------------------------------------------------------------
# SecurityGuard
# ---------------------------------------------------------------------------

class TestSecurityGuard:
    def test_process_clean_input(self):
        guard = SecurityGuard()
        result = guard.process("你好，小千！", caller_id="test")
        assert result == "你好，小千！"

    def test_process_sanitizes_html(self):
        guard = SecurityGuard()
        result = guard.process("<b>hello</b>", caller_id="test")
        assert "<b>" not in result

    def test_rate_limit_raises_permission_error(self):
        guard = SecurityGuard(rate_limiter=RateLimiter(max_calls=1, window_sec=60))
        guard.process("first", caller_id="testuser")
        with pytest.raises(PermissionError):
            guard.process("second", caller_id="testuser")

    def test_api_key_used_as_hmac_secret(self):
        """SecurityGuard 應將 api_key 作為 HMAC 共享密鑰傳遞給 TokenAuthenticator。"""
        guard = SecurityGuard(api_key="sec-shared-secret")
        token = guard.authenticator.generate_token("hello")
        assert guard.authenticator.verify_token("hello", token) is True

    def test_api_key_none_still_works(self):
        """未設定 api_key 時，SecurityGuard 應自動使用隨機密鑰，功能仍正常。"""
        guard = SecurityGuard(api_key=None)
        token = guard.authenticator.generate_token("world")
        assert guard.authenticator.verify_token("world", token) is True

    def test_different_api_keys_produce_different_tokens(self):
        """不同 api_key 應產生不同的 HMAC 令牌。"""
        guard_a = SecurityGuard(api_key="key-aaa")
        guard_b = SecurityGuard(api_key="key-bbb")
        token_a = guard_a.authenticator.generate_token("payload")
        token_b = guard_b.authenticator.generate_token("payload")
        assert token_a != token_b
