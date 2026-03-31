# 小千 (Xiao Qian) AI 夥伴系統

> 最重要的人

一個以 Python 實作的 AI 夥伴框架，具備工作輔助、知識爬取、安全防護與 API 金鑰管理能力。

---

## 功能概覽

| 模組 | 說明 |
|------|------|
| `xiao_qian/core.py` | 小千核心對話引擎 — 溫柔、可愛、工作輔助 |
| `xiao_qian/crawler.py` | 專屬爬蟲 & 知識資料庫（SQLite） |
| `xiao_qian/security.py` | 絕對防護 — 限速、輸入消毒、HMAC 驗證 |
| `xiao_qian/config.py` | API 金鑰管理（從環境變數讀取） |
| `main.py` | 命令列互動入口 |

---

## API 金鑰 🔑

系統使用**三把** API 金鑰，透過**環境變數**注入（絕不硬編碼）：

| 環境變數 | 用途 |
|----------|------|
| `XIAO_QIAN_API_KEY` | 🔑 小千核心對話引擎（OpenAI / 自定義 LLM） |
| `CRAWLER_API_KEY` | 🔑 小千專屬知識爬蟲服務 |
| `SECURITY_API_KEY` | 🔑 絕對防護模組（HMAC-SHA256 共享密鑰） |

```bash
export XIAO_QIAN_API_KEY="sk-..."
export CRAWLER_API_KEY="craw-..."
export SECURITY_API_KEY="sec-..."
```

---

## 快速開始

```bash
# 安裝依賴
pip install -r requirements.txt

# 設定 API 金鑰
export XIAO_QIAN_API_KEY="sk-..."
export CRAWLER_API_KEY="craw-..."
export SECURITY_API_KEY="sec-..."

# 啟動小千
python main.py
```

### 對話指令

```
/greet          → 讓小千打招呼
/learn <url>    → 讓小千學習指定網頁（知識爬蟲）
/recall <詞>    → 從知識庫搜尋相關資料
/summarize      → 進入摘要模式
/analyze        → 進入分析模式
/quit           → 離開
```

---

## 安全防護

`SecurityGuard` 提供三層防護：

1. **限速防護** (`RateLimiter`) — 滑動視窗，防止 API 濫用
2. **輸入消毒** (`InputSanitizer`) — 移除 HTML 標籤、SQL 注入片段、控制字元
3. **HMAC 驗證** (`TokenAuthenticator`) — 常數時間比較，防止 timing attack

---

## 測試

```bash
python -m pytest tests/ -v
```

---

## 架構說明

```
xiao_qian/
├── __init__.py      # 套件初始化
├── config.py        # 🔑 API 金鑰管理
├── core.py          # 小千核心引擎
├── crawler.py       # 知識爬蟲 & SQLite 資料庫
└── security.py      # 絕對防護模組
tests/
├── test_config.py
├── test_core.py
├── test_crawler.py
└── test_security.py
main.py              # 命令列入口
```
