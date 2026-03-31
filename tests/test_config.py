"""
tests/test_config.py
---------------------
測試 API 金鑰管理模組 (config.py)
"""

import os
import pytest
from xiao_qian.config import Config, KEY_XIAO_QIAN, KEY_CRAWLER


def test_key_identifiers():
    """確認金鑰識別名稱的常數值正確。"""
    assert KEY_XIAO_QIAN == "XIAO_QIAN_API_KEY"
    assert KEY_CRAWLER == "CRAWLER_API_KEY"


def test_config_reads_from_env(monkeypatch):
    """Config 應從環境變數讀取 API 金鑰。"""
    monkeypatch.setenv(KEY_XIAO_QIAN, "sk-test-xq")
    monkeypatch.setenv(KEY_CRAWLER,   "craw-test")
    cfg = Config()
    assert cfg.xiao_qian_api_key == "sk-test-xq"
    assert cfg.crawler_api_key   == "craw-test"


def test_config_missing_keys_returns_none(monkeypatch):
    """未設定環境變數時，金鑰應為 None。"""
    monkeypatch.delenv(KEY_XIAO_QIAN, raising=False)
    monkeypatch.delenv(KEY_CRAWLER,   raising=False)
    cfg = Config()
    assert cfg.xiao_qian_api_key is None
    assert cfg.crawler_api_key   is None


def test_config_validate_raises_when_missing(monkeypatch):
    """validate() 在缺少金鑰時應拋出 ValueError。"""
    monkeypatch.delenv(KEY_XIAO_QIAN, raising=False)
    monkeypatch.delenv(KEY_CRAWLER,   raising=False)
    cfg = Config()
    with pytest.raises(ValueError, match="API 金鑰"):
        cfg.validate()


def test_config_validate_passes_when_keys_set(monkeypatch):
    """validate() 在金鑰齊全時不應拋出例外。"""
    monkeypatch.setenv(KEY_XIAO_QIAN, "sk-abc")
    monkeypatch.setenv(KEY_CRAWLER,   "craw-xyz")
    cfg = Config()
    cfg.validate()  # should not raise


def test_config_default_db_uri():
    """預設資料庫 URI 應為 SQLite。"""
    cfg = Config()
    assert "sqlite" in cfg.db_uri
