"""AI Scorer - Match jobs against resume using Claude API."""

import os
import json
from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from bosshunter.db import get_db, get_jobs_by_status, update_job_score, update_job_status, update_job_quick_score
from bosshunter.ai.prefilter import quick_score
from bosshunter.ai.model_resolve import resolve_model
from bosshunter.ai.resume import extract_resume_text

console = Console()

SCORING_PROMPT = """你是一位专业的求职顾问。请根据以下简历和岗位JD，评估候选人与该岗位的匹配度。

## 候选人简历
{resume}

## 岗位信息
- 职位：{title}
- 公司：{company}
- 薪资：{salary}
- 要求：{experience}
- JD：{jd}

## 评估要求
请从以下维度评估匹配度，给出0-100的综合评分：
1. 技能匹配度：候选人的技能是否覆盖岗位要求
2. 经验匹配度：工作年限和行业经验是否符合
3. 薪资合理性：期望薪资与岗位薪资是否匹配
4. 成长空间：该岗位对候选人职业发展是否有帮助

请严格按以下JSON格式输出，不要输出其他内容：
{{"score": 75, "reason": "匹配理由简述（50字内）", "missing": "缺失的关键技能或经验（30字内）"}}
"""


def _load_resume(config: dict) -> str:
    """Load resume from configured path. Supports .md and .pdf."""
    resume_path = Path(config.get("profile", {}).get("resume_path", ""))
    if not resume_path or not resume_path.exists():
        return ""
    return extract_resume_text(resume_path)


def _call_claude(prompt: str, config: dict) -> str | None:
    """Call Claude API and return response text."""
    try:
        import anthropic
    except ImportError:
        console.print("[red]需要安装 anthropic 包: pip install anthropic[/red]")
        return None

    ai_cfg = config.get("ai", {})
    api_key = (
        os.environ.get("ANTHROPIC_API_KEY")
        or os.environ.get("ANTHROPIC_AUTH_TOKEN")
        or ai_cfg.get("api_key")
    )
    if not api_key:
        console.print("[red]未设置 ANTHROPIC_API_KEY 环境变量或 config.yaml ai.api_key[/red]")
        return None

    model = resolve_model(ai_cfg.get("model", "claude-sonnet-4-6"), config)
    base_url = os.environ.get("ANTHROPIC_BASE_URL") or ai_cfg.get("base_url")

    kwargs = {"api_key": api_key}
    if base_url:
        kwargs["base_url"] = base_url

    client = anthropic.Anthropic(**kwargs)

    try:
        response = client.messages.create(
            model=model,
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}]
        )
        # Skip ThinkingBlock, find TextBlock
        for block in response.content:
            if hasattr(block, 'text'):
                return block.text
        return None
    except Exception as e:
        console.print(f"[red]API 调用失败: {e}[/red]")
        return None


def _parse_score_response(text: str) -> dict | None:
    """Parse JSON response from Claude."""
    try:
        # Try to find JSON in response
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(text[start:end])
    except json.JSONDecodeError:
        pass
    return None


def score_jobs(config: dict) -> tuple[int, int]:
    """Score all pending jobs. Returns (scored_count, filtered_count)."""
    db = get_db()
    resume = _load_resume(config)
    if not resume:
        console.print("[red]无法读取简历文件[/red]")
        return 0, 0

    threshold = config.get("scoring", {}).get("threshold", 60)
    prefilter_threshold = config.get("scoring", {}).get("prefilter_threshold", 40)
    pending_jobs = get_jobs_by_status(db, "pending")

    if not pending_jobs:
        console.print("[yellow]没有待评分的岗位[/yellow]")
        return 0, 0

    scored = 0
    filtered = 0
    prefiltered = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task(f"评分中 (0/{len(pending_jobs)})", total=len(pending_jobs))

        for job in pending_jobs:
            # Stage 1: Keyword pre-filter (free, no API calls)
            qs, qs_reason = quick_score(job, config)
            update_job_quick_score(db, job["id"], qs)

            if qs < prefilter_threshold:
                update_job_score(db, job["id"], qs, f"预筛不通过: {qs_reason}")
                update_job_status(db, job["id"], "filtered")
                filtered += 1
                prefiltered += 1
                progress.update(task, advance=1, description=f"评分中 ({scored+filtered}/{len(pending_jobs)}) [预筛淘汰{prefiltered}]")
                continue

            # Stage 2: LLM deep evaluation
            prompt = SCORING_PROMPT.format(
                resume=resume[:3000],
                title=job["title"],
                company=job["company"],
                salary=job["salary"],
                experience=job["experience"],
                jd=job["jd"][:2000],
            )

            response = _call_claude(prompt, config)
            if not response:
                continue

            result = _parse_score_response(response)
            if not result:
                continue

            score = result.get("score", 0)
            reason = result.get("reason", "")
            missing = result.get("missing", "")
            full_reason = f"{reason} | 缺失: {missing}" if missing else reason

            update_job_score(db, job["id"], score, full_reason)

            if score >= threshold:
                update_job_status(db, job["id"], "scored")
                scored += 1
            else:
                update_job_status(db, job["id"], "filtered")
                filtered += 1

            progress.update(task, advance=1, description=f"评分中 ({scored+filtered}/{len(pending_jobs)}) [预筛淘汰{prefiltered}]")

    if prefiltered > 0:
        console.print(f"[dim]  预筛阶段淘汰 {prefiltered} 个岗位（节省 {prefiltered} 次 API 调用）[/dim]")
    db.close()
    return scored, filtered
