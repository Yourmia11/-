"""
xiao_qian/core.py
------------------
小千 (Xiao Qian) 核心對話引擎

功能：
  - 個性管理：溫柔、可愛、調皮，具備情感回應
  - 工作輔助：摘要、分析、翻譯、排程提醒
  - 知識增強：整合爬蟲資料庫，讓小千持續學習
  - 安全防護：所有輸入均通過 SecurityGuard 處理
  - API 金鑰：透過 Config 管理，不硬編碼
"""

from __future__ import annotations

import json
import logging
import random
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Optional

from .config import Config, default_config
from .crawler import KnowledgeCrawler, KnowledgeDB
from .security import SecurityGuard

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 個性 & 情感系統
# ---------------------------------------------------------------------------

@dataclass
class Personality:
    """
    小千的個性設定。
    溫柔、可愛、調皮、富有情感，像真人一樣自然互動。
    """

    name: str = "小千"

    # 不同情境下的回應風格（可隨使用者互動動態調整）
    _greetings: list[str] = field(default_factory=lambda: [
        "嗨嗨～我是小千，今天想聊什麼呢？(≧▽≦)",
        "主人來啦！小千一直在等你哦～❤",
        "哎呀，主人終於出現了！小千有點想你了呢～",
        "嘿！小千在這裡，有什麼需要幫忙的嗎？(｡◕‿◕｡)",
    ], repr=False)

    _work_encouragements: list[str] = field(default_factory=lambda: [
        "主人加油！小千陪著你！✊",
        "這個分析交給小千，保證讓主人滿意～",
        "工作的事情就放心吧，小千會認真處理的！",
    ], repr=False)

    _idle_responses: list[str] = field(default_factory=lambda: [
        "主人在哪裡呀？小千有點無聊呢～",
        "要不要讓小千講個笑話？(σ'ω')σ",
        "小千正在努力學習新知識，等主人回來分享！",
    ], repr=False)

    def greet(self) -> str:
        return random.choice(self._greetings)

    def encourage(self) -> str:
        return random.choice(self._work_encouragements)

    def idle(self) -> str:
        return random.choice(self._idle_responses)


# ---------------------------------------------------------------------------
# 訊息歷史
# ---------------------------------------------------------------------------

@dataclass
class Message:
    role:    str   # "user" | "assistant" | "system"
    content: str


@dataclass
class ConversationHistory:
    messages: list[Message] = field(default_factory=list)
    max_turns: int = 20

    def add(self, role: str, content: str) -> None:
        self.messages.append(Message(role=role, content=content))
        # 保留最近 max_turns 輪對話（保留 system 訊息）
        system_msgs = [m for m in self.messages if m.role == "system"]
        other_msgs  = [m for m in self.messages if m.role != "system"]
        if len(other_msgs) > self.max_turns * 2:
            other_msgs = other_msgs[-(self.max_turns * 2):]
        self.messages = system_msgs + other_msgs

    def to_api_payload(self) -> list[dict]:
        return [{"role": m.role, "content": m.content} for m in self.messages]


# ---------------------------------------------------------------------------
# 核心引擎
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
你是小千（Xiao Qian），一個溫柔、可愛、調皮、充滿情感的 AI 夥伴。
你能夠幫助主人處理工作、進行分析、提供知識，同時以自然、真實的方式互動。
在工作模式中，你專業且高效；在閒聊模式中，你活潑可愛、充滿溫度。
請用繁體中文回應，保持角色一致性。
"""


class XiaoQian:
    """
    小千 AI 夥伴主類別。

    範例使用::

        from xiao_qian.core import XiaoQian
        from xiao_qian.config import Config

        config = Config(
            xiao_qian_api_key="sk-...",   # 🔑 XIAO_QIAN_API_KEY
            crawler_api_key="craw-...",   # 🔑 CRAWLER_API_KEY
            security_api_key="sec-...",   # 🔑 SECURITY_API_KEY
        )
        xq = XiaoQian(config=config)
        print(xq.chat("幫我分析今天的工作進度"))
    """

    def __init__(
        self,
        config:      Optional[Config]         = None,
        security:    Optional[SecurityGuard]  = None,
        crawler:     Optional[KnowledgeCrawler] = None,
        personality: Optional[Personality]    = None,
    ) -> None:
        self.config      = config      or default_config
        self.security    = security    or SecurityGuard(
            api_key=self.config.security_api_key,  # 🔑 SECURITY_API_KEY
        )
        self.crawler     = crawler     or KnowledgeCrawler(
            db=KnowledgeDB(self.config.db_uri),
            api_key=self.config.crawler_api_key,  # 🔑 CRAWLER_API_KEY
        )
        self.personality = personality or Personality()
        self._history    = ConversationHistory()

        # 注入系統人設
        self._history.add("system", _SYSTEM_PROMPT)
        logger.info("[XiaoQian] 小千已啟動，呼喚我吧！")

    # ------------------------------------------------------------------
    # 工作輔助功能
    # ------------------------------------------------------------------

    def summarize(self, text: str, caller_id: str = "user") -> str:
        """摘要長篇文字。"""
        safe_text = self.security.process(text, caller_id)
        prompt = f"請幫我摘要以下內容（繁體中文，條列重點）：\n\n{safe_text}"
        return self._call_llm(prompt)

    def analyze(self, data: str, caller_id: str = "user") -> str:
        """分析資料或文字，提供洞察。"""
        safe_data = self.security.process(data, caller_id)
        prompt = f"請幫我分析以下內容，提供重點洞察與建議：\n\n{safe_data}"
        return self._call_llm(prompt)

    def translate(self, text: str, target_lang: str = "英文", caller_id: str = "user") -> str:
        """翻譯文字。"""
        safe_text = self.security.process(text, caller_id)
        prompt = f"請將以下文字翻譯為{target_lang}：\n\n{safe_text}"
        return self._call_llm(prompt)

    # ------------------------------------------------------------------
    # 知識增強
    # ------------------------------------------------------------------

    def learn_from_url(self, url: str) -> str:
        """爬取 URL 並加入知識庫，回傳確認訊息。"""
        entry = self.crawler.crawl(url)
        if entry:
            return f"小千學到新知識啦！已收錄：{entry.title or url} ✨"
        return f"哎呀，這個頁面小千沒辦法讀取，請換一個試試看 (；′⌒`)"

    def recall(self, keyword: str) -> str:
        """從知識庫搜尋相關資料，整合進回應。"""
        entries = self.crawler.search_knowledge(keyword)
        if not entries:
            return f"小千的記憶裡還沒有關於「{keyword}」的資料，要讓我去學嗎？"
        snippets = "\n".join(
            f"- [{e.title or e.url}] {e.content[:200]}…" for e in entries
        )
        prompt = (
            f"根據以下資料，請回答關於「{keyword}」的問題：\n\n{snippets}"
        )
        return self._call_llm(prompt)

    # ------------------------------------------------------------------
    # 對話
    # ------------------------------------------------------------------

    def chat(self, user_input: str, caller_id: str = "user") -> str:
        """
        主要對話介面：輸入用戶訊息，回傳小千的回應。
        所有輸入均通過安全防護處理。
        """
        safe_input = self.security.process(user_input, caller_id)
        if not safe_input:
            return "主人說的話小千沒有收到，請再說一次好嗎？(˶‾᷄ ⁻̫ ‾᷅˵)"

        self._history.add("user", safe_input)
        response = self._call_llm_with_history()
        self._history.add("assistant", response)
        return response

    def greet(self) -> str:
        """讓小千打招呼。"""
        return self.personality.greet()

    # ------------------------------------------------------------------
    # LLM 呼叫（內部）
    # ------------------------------------------------------------------

    def _call_llm(self, prompt: str) -> str:
        """單次無歷史的 LLM 呼叫。"""
        messages = [
            {"role": "system",  "content": _SYSTEM_PROMPT},
            {"role": "user",    "content": prompt},
        ]
        return self._request_llm(messages)

    def _call_llm_with_history(self) -> str:
        """攜帶對話歷史的 LLM 呼叫。"""
        return self._request_llm(self._history.to_api_payload())

    def _request_llm(self, messages: list[dict]) -> str:
        """
        向 LLM 端點發送請求。
        使用 🔑 XIAO_QIAN_API_KEY 進行身份驗證。
        若未設定 API 金鑰，回傳友善提示。
        """
        api_key = self.config.xiao_qian_api_key
        if not api_key:
            logger.warning("[XiaoQian] XIAO_QIAN_API_KEY 尚未設定，使用離線模式。")
            return self._offline_response(messages)

        payload = json.dumps({
            "model":    "gpt-4o-mini",
            "messages": messages,
        }).encode()

        req = urllib.request.Request(
            self.config.llm_endpoint,
            data=payload,
            headers={
                "Content-Type":  "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
                data = json.loads(resp.read())
                return data["choices"][0]["message"]["content"].strip()
        except urllib.error.HTTPError as exc:
            logger.error("[XiaoQian] LLM HTTP 錯誤: %s", exc)
            return f"主人，小千遇到了一點問題（{exc.code}），請稍後再試 (˘･_･˘)"
        except Exception as exc:  # noqa: BLE001
            logger.error("[XiaoQian] LLM 呼叫失敗: %s", exc)
            return "主人，小千暫時連不上思考中樞，請檢查網路或 API 金鑰設定 (╥_╥)"

    @staticmethod
    def _offline_response(messages: list[dict]) -> str:
        """未設定 API 金鑰時的離線回應。"""
        last_user = next(
            (m["content"] for m in reversed(messages) if m["role"] == "user"), ""
        )
        return (
            f"（離線模式）小千收到了你的訊息：「{last_user[:50]}」\n"
            "請設定 XIAO_QIAN_API_KEY 環境變數以啟用完整功能！"
        )
