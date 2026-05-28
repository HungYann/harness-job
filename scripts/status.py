#!/usr/bin/env python3
"""查看投递状态统计。

用法：
    python3 scripts/status.py         # 简要统计
    python3 scripts/status.py --full  # 完整仪表盘
"""
import argparse
import _bootstrap  # noqa: F401

parser = argparse.ArgumentParser(description="查看状态")
parser.add_argument("--full", action="store_true", help="完整仪表盘视图")
args = parser.parse_args()

if args.full:
    from bosshunter.tracker.status import show_dashboard
    show_dashboard()
else:
    from bosshunter.tracker.status import show_status
    show_status()
