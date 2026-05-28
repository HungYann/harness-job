#!/usr/bin/env python3
"""启动 Web 配置面板 / 数据看板。

用法：
    python3 scripts/web.py            # 默认端口 8686，自动打开浏览器
    python3 scripts/web.py --port 9090 --no-open
"""
import sys, argparse
import _bootstrap  # noqa: F401

from bosshunter.web.server import run_server

parser = argparse.ArgumentParser(description="BossHunter Web Dashboard")
parser.add_argument("--port", "-p", type=int, default=8686)
parser.add_argument("--no-open", action="store_true")
args = parser.parse_args()

run_server(host="127.0.0.1", port=args.port, open_browser=not args.no_open)
