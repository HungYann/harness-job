#!/usr/bin/env python3
"""对采集的岗位进行 AI 两阶段评分。

用法：
    python3 scripts/score.py
"""
import _bootstrap  # noqa: F401
from rich.console import Console
from bosshunter.config import load_config
from bosshunter.ai.scorer import score_jobs

console = Console()
config  = load_config()
console.print("[bold]开始 AI 评分...[/bold]")
scored, filtered = score_jobs(config)
console.print(f"[green]✓ 评分完成: {scored} 个通过, {filtered} 个过滤[/green]")
