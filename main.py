"""
main.py
--------
小千 (Xiao Qian) AI 夥伴 – 命令列入口點

使用方式：
    # 設定 API 金鑰（至少需要 XIAO_QIAN_API_KEY 才能使用完整對話功能）
    export XIAO_QIAN_API_KEY="sk-..."
    export CRAWLER_API_KEY="craw-..."

    # 啟動互動對話
    python main.py

    # 指令說明（於對話中輸入）：
    /greet          → 讓小千打招呼
    /learn <url>    → 讓小千學習指定網頁
    /recall <詞>    → 從知識庫搜尋
    /summarize      → 進入摘要模式（下一行輸入文字）
    /analyze        → 進入分析模式（下一行輸入文字）
    /quit           → 離開
"""

from __future__ import annotations

import logging
import sys

from xiao_qian.core import XiaoQian
from xiao_qian.config import Config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
)


def main() -> None:
    config = Config()
    xq = XiaoQian(config=config)

    print("=" * 60)
    print(f"  歡迎來到小千的世界！  (版本 0.1.0)")
    print("  輸入 /help 查看指令，/quit 離開。")
    print("=" * 60)
    print(xq.greet())
    print()

    while True:
        try:
            user_input = input("你：").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n小千：掰掰～期待下次見面！❤")
            break

        if not user_input:
            continue

        # --- 特殊指令 ---
        if user_input == "/quit":
            print("小千：掰掰～期待下次見面！❤")
            break

        elif user_input == "/help":
            print(
                "指令列表：\n"
                "  /greet          → 讓小千打招呼\n"
                "  /learn <url>    → 讓小千學習指定網頁\n"
                "  /recall <詞>    → 從知識庫搜尋\n"
                "  /summarize      → 進入摘要模式\n"
                "  /analyze        → 進入分析模式\n"
                "  /quit           → 離開\n"
            )

        elif user_input == "/greet":
            print(f"小千：{xq.greet()}")

        elif user_input.startswith("/learn "):
            url = user_input[len("/learn "):].strip()
            print(f"小千：{xq.learn_from_url(url)}")

        elif user_input.startswith("/recall "):
            keyword = user_input[len("/recall "):].strip()
            print(f"小千：{xq.recall(keyword)}")

        elif user_input == "/summarize":
            print("請輸入要摘要的文字（輸入空白行結束）：")
            lines: list[str] = []
            while True:
                line = input()
                if not line:
                    break
                lines.append(line)
            text = "\n".join(lines)
            if text:
                print(f"小千：{xq.summarize(text)}")

        elif user_input == "/analyze":
            print("請輸入要分析的內容（輸入空白行結束）：")
            lines_a: list[str] = []
            while True:
                line = input()
                if not line:
                    break
                lines_a.append(line)
            data = "\n".join(lines_a)
            if data:
                print(f"小千：{xq.analyze(data)}")

        else:
            # 一般對話
            response = xq.chat(user_input)
            print(f"小千：{response}")

        print()


if __name__ == "__main__":
    main()
