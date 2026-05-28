"""Pipeline - orchestrates the full BossHunter flow."""

from rich.console import Console

from bosshunter.browser import check_chrome_connection, find_boss_tab

console = Console()


def run_pipeline(config: dict) -> None:
    """Run the full pipeline: scrape → score → greet → confirm → send."""
    # Step 1: Check Chrome connection
    console.print("[bold]Step 1/5: 检测浏览器连接[/bold]")
    version_info = check_chrome_connection()
    if not version_info:
        console.print("[red]✗ Chrome 未连接，请确保带 --remote-debugging-port=9222 启动[/red]")
        return

    boss_tab = find_boss_tab()
    if not boss_tab:
        console.print("[red]✗ 未发现 某直聘 页面，请先登录[/red]")
        return
    console.print("[green]  ✓ 浏览器就绪[/green]\n")

    # Step 2: Scrape jobs
    console.print("[bold]Step 2/5: 采集岗位[/bold]")
    from bosshunter.scraper.jobs import scrape_jobs
    keywords = config["search"]["keywords"]
    count = scrape_jobs(config, keywords, limit=30)
    if count == 0:
        console.print("[yellow]  ! 未采集到新岗位，尝试继续处理已有岗位...[/yellow]")
    else:
        console.print(f"[green]  ✓ 采集 {count} 个新岗位[/green]\n")

    # Step 3: AI scoring (with pre-filter)
    console.print("[bold]Step 3/5: AI 评分筛选[/bold]")
    from bosshunter.ai.scorer import score_jobs
    scored, filtered = score_jobs(config)
    if scored == 0 and count > 0:
        console.print("[yellow]  ! 没有通过评分的岗位，流程结束[/yellow]")
        return
    console.print(f"[green]  ✓ {scored} 个通过, {filtered} 个过滤[/green]\n")

    # Step 4: Confirm which jobs to pursue
    console.print("[bold]Step 4/5: 确认投递清单[/bold]")
    from bosshunter.ui.confirm import show_confirmation
    approved = show_confirmation(config)
    if not approved:
        console.print("[yellow]  已取消发送[/yellow]")
        return

    # Step 5: Generate greetings for confirmed jobs, then send
    console.print("\n[bold]Step 5/5: 生成招呼语并发送[/bold]")
    from bosshunter.ai.greeter import generate_greetings
    greet_count = generate_greetings(config)
    console.print(f"[green]  ✓ 生成 {greet_count} 条招呼语[/green]")

    from bosshunter.executor.sender import send_greetings
    sent = send_greetings(config)
    console.print(f"\n[bold green]═══ 完成！发送 {sent} 条招呼语 ═══[/bold green]")
    console.print("\n[dim]提示: 使用 'python3 scripts/monitor.py' 监听HR回复并自动投递简历[/dim]")
