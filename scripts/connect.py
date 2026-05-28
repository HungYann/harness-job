#!/usr/bin/env python3
"""检测 Chrome CDP 连接状态。

用法：
    python3 scripts/connect.py
"""
import _bootstrap  # noqa: F401
from rich.console import Console
from bosshunter.browser import check_chrome_connection, find_boss_tab

console = Console()
console.print("[bold]正在检测 Chrome 连接...[/bold]")

info = check_chrome_connection()
if not info:
    console.print("[red]✗ 无法连接 Chrome 调试端口[/red]")
    console.print("  请确保 Chrome 已开启远程调试（chrome://inspect/#remote-debugging）")
    raise SystemExit(1)

console.print(f"[green]✓ Chrome 已连接: {info.get('Browser', info.get('status', 'OK'))}[/green]")

tab = find_boss_tab()
if tab:
    console.print(f"[green]✓ 发现某直聘页面: {tab.get('title', '')}[/green]")
else:
    console.print("[yellow]! 未发现某直聘页面，请在 Chrome 中打开 www.zhipin.com 并登录[/yellow]")
