#!/usr/bin/env python3
"""自动发送已确认的招呼语。

用法：
    python3 scripts/send.py
    python3 scripts/send.py --force   # 跳过随机休息日检查
"""
import argparse
import _bootstrap  # noqa: F401
from rich.console import Console
from bosshunter.config import load_config
from bosshunter.executor.sender import send_greetings

parser = argparse.ArgumentParser(description="发送招呼语")
parser.add_argument("--force", action="store_true", help="跳过随机休息日")
args = parser.parse_args()

console = Console()
config  = load_config()
console.print("[bold]开始发送招呼语...[/bold]")
sent = send_greetings(config, force=args.force)
console.print(f"[green]✓ 发送完成: {sent} 条[/green]")
