"""
xiao_qian/config.py
-------------------
API 金鑰管理模組 (API Key Management)
每把鑰匙都有唯一標識，方便日後擴充 2D/3D 介面或第三方服務。

API Key Registry
----------------
KEY_XIAO_QIAN  → 小千核心對話引擎 (OpenAI / 自定義 LLM 端點)
KEY_CRAWLER    → 小千專屬爬蟲/知識資料庫服務
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# API Key identifiers – 每把鑰匙的唯一標識名稱
# ---------------------------------------------------------------------------
KEY_XIAO_QIAN: str = "XIAO_QIAN_API_KEY"   # 🔑 小千對話引擎鑰匙
KEY_CRAWLER:   str = "CRAWLER_API_KEY"      # 🔑 知識爬蟲服務鑰匙


@dataclass
class Config:
    """
    全域設定物件。
    從環境變數讀取 API 金鑰，避免硬編碼 (hard-code) 進原始碼。
    未來可透過 `.env` 檔案或加密金鑰庫注入。
    """

    # 🔑 小千對話引擎 API 金鑰 (環境變數: XIAO_QIAN_API_KEY)
    xiao_qian_api_key: Optional[str] = field(
        default_factory=lambda: os.environ.get(KEY_XIAO_QIAN)
    )

    # 🔑 知識爬蟲服務 API 金鑰 (環境變數: CRAWLER_API_KEY)
    crawler_api_key: Optional[str] = field(
        default_factory=lambda: os.environ.get(KEY_CRAWLER)
    )

    # 對話引擎端點 (預設使用 OpenAI，可替換為本地 LLM)
    llm_endpoint: str = field(
        default_factory=lambda: os.environ.get(
            "XIAO_QIAN_LLM_ENDPOINT", "https://api.openai.com/v1/chat/completions"
        )
    )

    # 爬蟲資料庫連線 URI (預設本地 SQLite)
    db_uri: str = field(
        default_factory=lambda: os.environ.get("CRAWLER_DB_URI", "sqlite:///xiao_qian_knowledge.db")
    )

    # 安全模組：最大登入嘗試次數
    max_auth_attempts: int = 5

    def validate(self) -> None:
        """驗證必要設定是否齊全，缺少時拋出 ValueError。"""
        missing: list[str] = []
        if not self.xiao_qian_api_key:
            missing.append(KEY_XIAO_QIAN)
        if not self.crawler_api_key:
            missing.append(KEY_CRAWLER)
        if missing:
            raise ValueError(
                f"缺少必要的 API 金鑰，請設定以下環境變數: {', '.join(missing)}"
            )


# 模組層級的預設設定實例
default_config = Config()
