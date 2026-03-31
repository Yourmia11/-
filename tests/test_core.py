"""
tests/test_core.py
-------------------
測試小千核心對話引擎 (core.py)
"""

import tempfile
import pytest

from xiao_qian.config import Config
from xiao_qian.core import XiaoQian, Personality, ConversationHistory, Message
from xiao_qian.crawler import KnowledgeDB, KnowledgeCrawler, CrawlerConfig
from xiao_qian.security import SecurityGuard, RateLimiter


# ---------------------------------------------------------------------------
# Personality
# ---------------------------------------------------------------------------

class TestPersonality:
    def test_greet_returns_string(self):
        p = Personality()
        assert isinstance(p.greet(), str)
        assert len(p.greet()) > 0

    def test_encourage_returns_string(self):
        p = Personality()
        assert isinstance(p.encourage(), str)

    def test_idle_returns_string(self):
        p = Personality()
        assert isinstance(p.idle(), str)


# ---------------------------------------------------------------------------
# ConversationHistory
# ---------------------------------------------------------------------------

class TestConversationHistory:
    def test_add_and_retrieve(self):
        h = ConversationHistory()
        h.add("user", "hello")
        h.add("assistant", "hi")
        payload = h.to_api_payload()
        assert any(m["role"] == "user" and m["content"] == "hello" for m in payload)
        assert any(m["role"] == "assistant" and m["content"] == "hi" for m in payload)

    def test_max_turns_truncates(self):
        h = ConversationHistory(max_turns=2)
        for i in range(10):
            h.add("user", f"msg{i}")
            h.add("assistant", f"resp{i}")
        # 只保留最近 max_turns*2 條非 system 訊息
        non_system = [m for m in h.messages if m.role != "system"]
        assert len(non_system) <= 4  # max_turns * 2

    def test_system_messages_preserved(self):
        h = ConversationHistory(max_turns=1)
        h.add("system", "you are xiao qian")
        for i in range(5):
            h.add("user",      f"u{i}")
            h.add("assistant", f"a{i}")
        assert any(m.role == "system" for m in h.messages)


# ---------------------------------------------------------------------------
# XiaoQian (offline mode – no real API key)
# ---------------------------------------------------------------------------

def _make_xq(tmp_path) -> XiaoQian:
    """建立不需真實 API 金鑰的 XiaoQian 實例（離線模式）。"""
    config = Config(xiao_qian_api_key=None, crawler_api_key=None,
                    db_uri=f"sqlite:///{tmp_path}/test.db")
    db      = KnowledgeDB(db_path=str(tmp_path / "test.db"))
    crawler = KnowledgeCrawler(db=db, config=CrawlerConfig(delay=0))
    return XiaoQian(config=config, crawler=crawler)


class TestXiaoQian:
    def test_greet(self, tmp_path):
        xq = _make_xq(tmp_path)
        result = xq.greet()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_chat_offline_mode(self, tmp_path):
        xq = _make_xq(tmp_path)
        result = xq.chat("你好！")
        # 離線模式應包含提示訊息
        assert "離線" in result or "XIAO_QIAN_API_KEY" in result

    def test_chat_empty_input(self, tmp_path):
        xq = _make_xq(tmp_path)
        result = xq.chat("   ")
        # 空輸入（消毒後）應得到友善回應，而非崩潰
        assert isinstance(result, str)

    def test_recall_no_knowledge(self, tmp_path):
        xq = _make_xq(tmp_path)
        result = xq.recall("量子力學")
        assert "量子力學" in result

    def test_learn_from_url_failure(self, tmp_path):
        xq = _make_xq(tmp_path)
        result = xq.learn_from_url("http://localhost:19999/bad_url_xyz")
        assert isinstance(result, str)
        # 應回傳失敗訊息而非拋出例外
        assert len(result) > 0

    def test_summarize_offline(self, tmp_path):
        xq = _make_xq(tmp_path)
        result = xq.summarize("這是一段很長的測試文字，需要摘要。")
        assert isinstance(result, str)

    def test_analyze_offline(self, tmp_path):
        xq = _make_xq(tmp_path)
        result = xq.analyze("銷售數據：1月100萬，2月80萬，3月120萬。")
        assert isinstance(result, str)

    def test_security_sanitizes_input(self, tmp_path):
        xq = _make_xq(tmp_path)
        # HTML 標籤應被清除
        result = xq.chat("<script>alert(1)</script>你好")
        assert "<script>" not in result

    def test_rate_limit_raises(self, tmp_path):
        guard = SecurityGuard(rate_limiter=RateLimiter(max_calls=1, window_sec=60))
        config = Config(xiao_qian_api_key=None, crawler_api_key=None,
                        db_uri=f"sqlite:///{tmp_path}/rl.db")
        db      = KnowledgeDB(db_path=str(tmp_path / "rl.db"))
        crawler = KnowledgeCrawler(db=db, config=CrawlerConfig(delay=0))
        xq = XiaoQian(config=config, security=guard, crawler=crawler)
        xq.chat("first", caller_id="ruser")
        with pytest.raises(PermissionError):
            xq.chat("second", caller_id="ruser")
