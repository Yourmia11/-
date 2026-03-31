"""
xiao_qian/crawler.py
---------------------
小千專屬爬蟲 & 知識資料庫模組 (Xiao Qian Knowledge Crawler & DB)

功能：
  - 透過 HTTP 抓取網頁並萃取純文字
  - 將知識條目儲存至 SQLite 資料庫
  - 提供關鍵字搜尋介面供核心對話引擎查詢
"""

from __future__ import annotations

import hashlib
import logging
import sqlite3
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Iterator, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# HTML 純文字萃取
# ---------------------------------------------------------------------------

class _TextExtractor(HTMLParser):
    """簡易 HTML → 純文字轉換器（無外部依賴）。"""

    _SKIP_TAGS = {"script", "style", "head", "noscript", "meta", "link"}

    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []
        self._skip: int = 0

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag.lower() in self._SKIP_TAGS:
            self._skip += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in self._SKIP_TAGS:
            self._skip = max(0, self._skip - 1)

    def handle_data(self, data: str) -> None:
        if self._skip == 0 and data.strip():
            self._parts.append(data.strip())

    @property
    def text(self) -> str:
        return " ".join(self._parts)


def _extract_text(html: str) -> str:
    parser = _TextExtractor()
    parser.feed(html)
    return parser.text


# ---------------------------------------------------------------------------
# 知識條目
# ---------------------------------------------------------------------------

@dataclass
class KnowledgeEntry:
    url:        str
    title:      str
    content:    str
    fetched_at: float = field(default_factory=time.time)
    url_hash:   str   = field(init=False)

    def __post_init__(self) -> None:
        self.url_hash = hashlib.sha256(self.url.encode()).hexdigest()


# ---------------------------------------------------------------------------
# 資料庫管理
# ---------------------------------------------------------------------------

class KnowledgeDB:
    """
    SQLite 知識資料庫。
    儲存爬蟲抓回的條目，並提供全文關鍵字搜尋。
    """

    _SCHEMA = """
    CREATE TABLE IF NOT EXISTS knowledge (
        url_hash  TEXT PRIMARY KEY,
        url       TEXT NOT NULL,
        title     TEXT NOT NULL DEFAULT '',
        content   TEXT NOT NULL,
        fetched_at REAL NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_title   ON knowledge(title);
    """

    def __init__(self, db_path: str = "xiao_qian_knowledge.db") -> None:
        # Remove SQLite URI scheme if present
        if db_path.startswith("sqlite:///"):
            db_path = db_path[len("sqlite:///"):]
        self._path = db_path
        self._conn = sqlite3.connect(self._path, check_same_thread=False)
        self._conn.executescript(self._SCHEMA)
        self._conn.commit()
        logger.info("[KnowledgeDB] 已連線至 %s", self._path)

    def save(self, entry: KnowledgeEntry) -> None:
        """儲存或更新一筆知識條目。"""
        self._conn.execute(
            """
            INSERT OR REPLACE INTO knowledge (url_hash, url, title, content, fetched_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (entry.url_hash, entry.url, entry.title, entry.content, entry.fetched_at),
        )
        self._conn.commit()
        logger.debug("[KnowledgeDB] 已儲存: %s", entry.url)

    def search(self, keyword: str, limit: int = 10) -> list[KnowledgeEntry]:
        """關鍵字搜尋（標題與內容）。"""
        like = f"%{keyword}%"
        rows = self._conn.execute(
            """
            SELECT url_hash, url, title, content, fetched_at
            FROM knowledge
            WHERE title LIKE ? OR content LIKE ?
            ORDER BY fetched_at DESC
            LIMIT ?
            """,
            (like, like, limit),
        ).fetchall()
        return [
            KnowledgeEntry(url=r[1], title=r[2], content=r[3], fetched_at=r[4])
            for r in rows
        ]

    def count(self) -> int:
        """回傳資料庫中的條目數量。"""
        row = self._conn.execute("SELECT COUNT(*) FROM knowledge").fetchone()
        return row[0] if row else 0

    def close(self) -> None:
        self._conn.close()


# ---------------------------------------------------------------------------
# 爬蟲
# ---------------------------------------------------------------------------

@dataclass
class CrawlerConfig:
    timeout:     int   = 10        # HTTP 請求逾時（秒）
    user_agent:  str   = "XiaoQianBot/1.0 (+https://github.com/Yourmia11/-)"
    max_content: int   = 50_000    # 每頁最大保留字元數
    delay:       float = 1.0       # 每次請求之間的延遲（秒，禮貌爬蟲）


class KnowledgeCrawler:
    """
    小千專屬知識爬蟲。
    抓取指定 URL 清單，萃取文字並儲存進 KnowledgeDB。
    """

    def __init__(
        self,
        db:     Optional[KnowledgeDB] = None,
        config: Optional[CrawlerConfig] = None,
        api_key: Optional[str] = None,
    ) -> None:
        self.db     = db     or KnowledgeDB()
        self.config = config or CrawlerConfig()
        self.api_key = api_key  # 🔑 CRAWLER_API_KEY – 保留供付費爬蟲 API 使用

    # ------------------------------------------------------------------
    # 內部工具
    # ------------------------------------------------------------------

    def _fetch_html(self, url: str) -> str:
        """以標準庫發出 HTTP GET，回傳 HTML 字串。"""
        req = urllib.request.Request(
            url,
            headers={"User-Agent": self.config.user_agent},
        )
        with urllib.request.urlopen(req, timeout=self.config.timeout) as resp:  # noqa: S310
            charset = resp.headers.get_content_charset("utf-8")
            return resp.read().decode(charset, errors="replace")

    @staticmethod
    def _extract_title(html: str) -> str:
        """從 HTML 中萃取 <title> 標籤內容。"""
        import re
        m = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        return m.group(1).strip() if m else ""

    # ------------------------------------------------------------------
    # 公開介面
    # ------------------------------------------------------------------

    def crawl(self, url: str) -> Optional[KnowledgeEntry]:
        """
        抓取單一 URL，萃取文字，存入資料庫並回傳 KnowledgeEntry。
        若抓取失敗回傳 None。
        """
        logger.info("[Crawler] 抓取: %s", url)
        try:
            html    = self._fetch_html(url)
            title   = self._extract_title(html)
            content = _extract_text(html)[: self.config.max_content]
            entry   = KnowledgeEntry(url=url, title=title, content=content)
            self.db.save(entry)
            return entry
        except Exception as exc:  # noqa: BLE001
            logger.error("[Crawler] 抓取失敗 %s – %s", url, exc)
            return None
        finally:
            time.sleep(self.config.delay)

    def crawl_many(self, urls: list[str]) -> Iterator[Optional[KnowledgeEntry]]:
        """批次抓取多個 URL。"""
        for url in urls:
            yield self.crawl(url)

    def search_knowledge(self, keyword: str, limit: int = 5) -> list[KnowledgeEntry]:
        """從資料庫搜尋相關知識條目。"""
        return self.db.search(keyword, limit=limit)
