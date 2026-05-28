#!/usr/bin/env python3
"""监听 HR 回复，自动回复 / 发送简历 / 跟进。

用法：
    python3 scripts/monitor.py           # 持续监听（默认 30 分钟间隔）
    python3 scripts/monitor.py --once    # 只检查一次
    python3 scripts/monitor.py --interval 15  # 每 15 分钟检查一次
"""
import argparse, time
import _bootstrap  # noqa: F401
from rich.console import Console
from bosshunter.config import load_config
from bosshunter.executor.monitor import monitor_and_send_resumes

parser = argparse.ArgumentParser(description="监听 HR 回复")
parser.add_argument("--once",     action="store_true", help="只检查一次")
parser.add_argument("--interval", type=int, default=None, help="循环间隔（分钟）")
args = parser.parse_args()

console = Console()
config  = load_config()
interval_min = args.interval or config.get("monitor", {}).get("interval", 30)
interval_sec = interval_min * 60

if args.once:
    console.print("[bold cyan]═══ 单次监听模式 ═══[/bold cyan]\n")
    summary = monitor_and_send_resumes(config)
    console.print(f"\n本次: 自动回复 {summary.get('replied',0)} 条 | 简历发送 {summary.get('resume_sent',0)} 份 | 跳过 {summary.get('skipped',0)} 条")
else:
    console.print(f"[bold cyan]═══ 持续监听（每 {interval_min} 分钟）═══[/bold cyan]")
    console.print("[dim]Ctrl+C 停止[/dim]\n")
    try:
        while True:
            try:
                monitor_and_send_resumes(config)
            except Exception as e:
                console.print(f"[red]本轮出错: {e}[/red]")
            console.print(f"\n[dim]等待 {interval_min} 分钟...[/dim]\n")
            time.sleep(interval_sec)
    except KeyboardInterrupt:
        console.print("\n[yellow]已停止[/yellow]")
