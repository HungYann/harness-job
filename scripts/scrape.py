#!/usr/bin/env python3
"""采集某直聘岗位。

用法：
    python3 scripts/scrape.py -k "Python开发" -l 30
    python3 scripts/scrape.py                        # 使用 config.yaml 中的关键词
"""
import argparse
import _bootstrap  # noqa: F401
from rich.console import Console
from bosshunter.config import load_config
from bosshunter.scraper.jobs import scrape_jobs

parser = argparse.ArgumentParser(description="采集岗位")
parser.add_argument("--keyword", "-k", default=None, help="搜索关键词（覆盖 config.yaml）")
parser.add_argument("--limit",   "-l", type=int, default=30, help="最多抓取岗位数")
args = parser.parse_args()

console = Console()
config  = load_config()
keywords = [args.keyword] if args.keyword else config["search"]["keywords"]

console.print(f"[bold]开始采集...[/bold] 关键词: {keywords}")
count = scrape_jobs(config, keywords, args.limit)
console.print(f"[green]✓ 采集完成，共获取 {count} 个新岗位[/green]")
