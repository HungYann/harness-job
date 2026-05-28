#!/usr/bin/env python3
"""一键运行完整流程：采集 → 评分 → 招呼语 → 人工确认 → 发送。

用法：
    python3 scripts/run.py
"""
import _bootstrap  # noqa: F401
from rich.console import Console
from bosshunter.config import load_config
from bosshunter.pipeline import run_pipeline

console = Console()
config = load_config()
console.print("[bold cyan]═══ BossHunter 启动 ═══[/bold cyan]\n")
run_pipeline(config)
console.print("\n[dim]💡 运行 python3 scripts/web.py 可打开可视化看板[/dim]")
