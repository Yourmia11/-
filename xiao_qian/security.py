"""
xiao_qian/security.py
----------------------
絕對防護模組 (Absolute Protection Module)

功能：
  - 限速防護：防止暴力破解與 API 濫用
  - 輸入消毒：移除潛在的注入攻擊字元
  - 存取控制：驗證呼叫者身份
  - 安全日誌：記錄所有安全事件
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import re
import secrets
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 安全事件類型
# ---------------------------------------------------------------------------
SECURITY_EVENT_RATE_LIMIT    = "RATE_LIMIT_EXCEEDED"
SECURITY_EVENT_INVALID_TOKEN = "INVALID_TOKEN"
SECURITY_EVENT_SANITIZED     = "INPUT_SANITIZED"
SECURITY_EVENT_AUTH_OK       = "AUTH_SUCCESS"


@dataclass
class RateLimiter:
    """
    簡易滑動視窗限速器。
    max_calls  : 視窗內允許的最大呼叫次數
    window_sec : 視窗長度（秒）
    """

    max_calls:  int   = 60
    window_sec: float = 60.0
    _timestamps: dict = field(default_factory=lambda: defaultdict(list), repr=False)

    def is_allowed(self, identity: str) -> bool:
        """若此 identity 在視窗內呼叫次數未超限，回傳 True；否則 False。"""
        now = time.monotonic()
        window_start = now - self.window_sec
        timestamps = self._timestamps[identity]
        # 清除視窗外的舊時間戳
        self._timestamps[identity] = [t for t in timestamps if t >= window_start]
        if len(self._timestamps[identity]) >= self.max_calls:
            logger.warning(
                "[Security] %s – identity=%s, event=%s",
                SECURITY_EVENT_RATE_LIMIT, identity, "blocked",
            )
            return False
        self._timestamps[identity].append(now)
        return True


class InputSanitizer:
    """
    輸入消毒器：移除 HTML/Script 標籤、SQL 注入片段、控制字元等。
    回傳清潔後的字串。
    """

    # 禁止的 pattern（不分大小寫）
    _DANGEROUS_PATTERNS: list[re.Pattern] = [
        re.compile(r"<[^>]+>", re.IGNORECASE),                       # HTML tags
        re.compile(r"(--|;|/\*|\*/|xp_|EXEC\s)", re.IGNORECASE),     # SQL injection fragments
        re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]"),            # control characters
    ]

    @classmethod
    def clean(cls, text: str) -> str:
        """清理輸入文字並記錄是否有修改。"""
        cleaned = text
        for pattern in cls._DANGEROUS_PATTERNS:
            cleaned = pattern.sub("", cleaned)
        if cleaned != text:
            logger.info(
                "[Security] %s – original_len=%d, cleaned_len=%d",
                SECURITY_EVENT_SANITIZED, len(text), len(cleaned),
            )
        return cleaned.strip()


class TokenAuthenticator:
    """
    HMAC-SHA256 令牌驗證器。
    以共享密鑰對請求負載簽署，防止偽造請求。
    """

    def __init__(self, secret: Optional[str] = None) -> None:
        # 若未提供密鑰，產生隨機 256-bit 密鑰（僅用於本次執行期）
        self._secret: bytes = (secret or secrets.token_hex(32)).encode()

    def generate_token(self, payload: str) -> str:
        """為 payload 產生 HMAC-SHA256 令牌。"""
        return hmac.new(self._secret, payload.encode(), hashlib.sha256).hexdigest()

    def verify_token(self, payload: str, token: str) -> bool:
        """驗證令牌是否合法（使用常數時間比較防止 timing attack）。"""
        expected = self.generate_token(payload)
        ok = hmac.compare_digest(expected, token)
        event = SECURITY_EVENT_AUTH_OK if ok else SECURITY_EVENT_INVALID_TOKEN
        logger.info("[Security] %s – payload_len=%d", event, len(payload))
        return ok


class SecurityGuard:
    """
    絕對防護主類別：整合限速、消毒、驗證三層防護。

    使用方式：
        guard = SecurityGuard()
        safe_input = guard.process(raw_user_input, caller_id="user_123")
    """

    def __init__(
        self,
        rate_limiter:  Optional[RateLimiter]       = None,
        sanitizer:     Optional[InputSanitizer]    = None,
        authenticator: Optional[TokenAuthenticator]= None,
    ) -> None:
        self.rate_limiter  = rate_limiter  or RateLimiter()
        self.sanitizer     = sanitizer     or InputSanitizer()
        self.authenticator = authenticator or TokenAuthenticator()

    def check_rate_limit(self, caller_id: str) -> None:
        """若超限，拋出 PermissionError。"""
        if not self.rate_limiter.is_allowed(caller_id):
            raise PermissionError(f"呼叫頻率超限，請稍後再試 (caller={caller_id})")

    def sanitize(self, text: str) -> str:
        """消毒輸入並回傳。"""
        return self.sanitizer.clean(text)

    def process(self, raw_text: str, caller_id: str = "anonymous") -> str:
        """
        完整的防護流程：
          1. 限速檢查
          2. 輸入消毒
          3. 回傳安全字串
        """
        self.check_rate_limit(caller_id)
        return self.sanitize(raw_text)
