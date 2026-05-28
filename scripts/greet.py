#!/usr/bin/env python3
"""为通过评分的岗位生成个性化招呼语。

用法：
    python3 scripts/greet.py
"""
import _bootstrap  # noqa: F401
from rich.console import Console
from bosshunter.config import load_config
from bosshunter.ai.greeter import generate_greetings

console = Console()
config  = load_config()
console.print("[bold]生成招呼语...[/bold]")
count = generate_greetings(config)
console.print(f"[green]✓ 已生成 {count} 条招呼语[/green]")
