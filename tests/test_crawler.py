"""
tests/test_crawler.py
----------------------
測試知識爬蟲 & 資料庫模組 (crawler.py)
"""

import os
import tempfile
import pytest

from xiao_qian.crawler import (
    KnowledgeDB,
    KnowledgeEntry,
    KnowledgeCrawler,
    CrawlerConfig,
    _extract_text,
)


# ---------------------------------------------------------------------------
# _extract_text
# ---------------------------------------------------------------------------

class TestExtractText:
    def test_strips_html_tags(self):
        html = "<html><body><p>Hello World</p></body></html>"
        assert "Hello World" in _extract_text(html)
        assert "<p>" not in _extract_text(html)

    def test_skips_script_content(self):
        html = "<script>var x = 1;</script><p>visible</p>"
        text = _extract_text(html)
        assert "var x" not in text
        assert "visible" in text

    def test_skips_style_content(self):
        html = "<style>body{color:red}</style><p>text</p>"
        text = _extract_text(html)
        assert "color:red" not in text
        assert "text" in text


# ---------------------------------------------------------------------------
# KnowledgeDB
# ---------------------------------------------------------------------------

class TestKnowledgeDB:
    def _make_db(self, tmp_path) -> KnowledgeDB:
        return KnowledgeDB(db_path=str(tmp_path / "test.db"))

    def test_save_and_count(self, tmp_path):
        db = self._make_db(tmp_path)
        entry = KnowledgeEntry(url="https://example.com", title="Example", content="Hello")
        db.save(entry)
        assert db.count() == 1
        db.close()

    def test_search_by_title(self, tmp_path):
        db = self._make_db(tmp_path)
        db.save(KnowledgeEntry(url="https://a.com", title="Python 教學", content="print hello"))
        db.save(KnowledgeEntry(url="https://b.com", title="Java 入門", content="System.out"))
        results = db.search("Python")
        assert len(results) == 1
        assert results[0].title == "Python 教學"
        db.close()

    def test_search_by_content(self, tmp_path):
        db = self._make_db(tmp_path)
        db.save(KnowledgeEntry(url="https://c.com", title="Test", content="small qian rocks"))
        results = db.search("rocks")
        assert any("rocks" in r.content for r in results)
        db.close()

    def test_upsert_same_url(self, tmp_path):
        db = self._make_db(tmp_path)
        db.save(KnowledgeEntry(url="https://dup.com", title="v1", content="old"))
        db.save(KnowledgeEntry(url="https://dup.com", title="v2", content="new"))
        assert db.count() == 1
        results = db.search("new")
        assert len(results) == 1
        db.close()

    def test_sqlite_uri_prefix_stripped(self, tmp_path):
        """KnowledgeDB 應正確處理 sqlite:/// 前綴。"""
        path = str(tmp_path / "uri_test.db")
        db = KnowledgeDB(db_path=f"sqlite:///{path}")
        db.save(KnowledgeEntry(url="https://x.com", title="T", content="C"))
        assert db.count() == 1
        db.close()

    def test_empty_search_returns_empty(self, tmp_path):
        db = self._make_db(tmp_path)
        results = db.search("nonexistent_keyword_xyz")
        assert results == []
        db.close()


# ---------------------------------------------------------------------------
# KnowledgeCrawler (unit – 不發出真實 HTTP 請求)
# ---------------------------------------------------------------------------

class TestKnowledgeCrawler:
    def _make_crawler(self, tmp_path) -> KnowledgeCrawler:
        db = KnowledgeDB(db_path=str(tmp_path / "crawler_test.db"))
        config = CrawlerConfig(timeout=5, delay=0)
        return KnowledgeCrawler(db=db, config=config)

    def test_crawl_failure_returns_none(self, tmp_path):
        """對一個不存在的 URL 爬取應回傳 None 而非拋出例外。"""
        crawler = self._make_crawler(tmp_path)
        result = crawler.crawl("http://localhost:19999/nonexistent_page_xyz")
        assert result is None

    def test_search_knowledge_empty(self, tmp_path):
        crawler = self._make_crawler(tmp_path)
        results = crawler.search_knowledge("無此詞")
        assert results == []

    def test_crawl_many_yields_results(self, tmp_path, monkeypatch):
        """crawl_many 應對每個 URL 產生一個結果（成功或 None）。"""
        crawler = self._make_crawler(tmp_path)
        urls = ["http://fail1.invalid", "http://fail2.invalid"]
        results = list(crawler.crawl_many(urls))
        assert len(results) == 2

    def test_api_key_stored(self, tmp_path):
        """crawler 應正確儲存 API 金鑰。"""
        db = KnowledgeDB(db_path=str(tmp_path / "ak.db"))
        crawler = KnowledgeCrawler(db=db, api_key="craw-test-key")
        assert crawler.api_key == "craw-test-key"
