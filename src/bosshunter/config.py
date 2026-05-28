"""Configuration loader for BossHunter."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from bosshunter import PROJECT_ROOT


# 某直聘城市编码映射
CITY_CODES: dict[str, str] = {
    "北京": "101010100",
    "上海": "101020100",
    "深圳": "101280100",
    "广州": "101280600",
    "杭州": "101210100",
    "成都": "101270100",
    "武汉": "101200100",
    "南京": "101190100",
    "西安": "101110100",
    "苏州": "101190400",
    "天津": "101030100",
    "重庆": "101040100",
    "郑州": "101180100",
    "长沙": "101250100",
    "东莞": "101281600",
    "佛山": "101280800",
    "合肥": "101220100",
    "厦门": "101230200",
    "青岛": "101120200",
    "大连": "101070200",
}


DEFAULTS: dict[str, Any] = {
    "profile": {
        "resume_path": "",  # 支持 .md 或 .pdf，通过 Web 面板上传或手动填写路径
        "resume_output_dir": "./data/resumes",
        "target_cities": ["北京"],
        "salary_min": 0,
        "salary_max": 0,
        "deal_breakers": [],
    },
    "search": {
        "keywords": [],
        "cities": [],  # Empty = fallback to profile.target_cities
        "salary_range": "",
        "max_pages": 3,
    },
    "scoring": {
        "threshold": 71,
        "prefilter_threshold": 40,
        "max_candidates": 20,
    },
    "throttle": {
        "daily_limit": 30,
        "interval_min": 60,
        "interval_max": 180,
        "browse_before_greet": True,
        "browse_duration_min": 15,
        "browse_duration_max": 30,
        "send_windows": ["09:00-16:00"],
        "day_off_probability": 0.05,
    },
    "ai": {
        "provider": "anthropic",   # anthropic | deepseek | openai | custom
        "model": "claude-sonnet-4-6",
        "api_key": "",             # 留空则读取对应环境变量
        "base_url": "",            # custom provider 专用
        "greeting_review_threshold": 7.0,
        "greeting_max_iterations": 2,
    },
    "monitor": {
        "interval": 30,  # 分钟
        "chat_url": "https://www.zhipin.com/web/geek/chat",
        "max_resume_sends_per_cycle": 5,
    },
    "follow_up": {
        "enabled": True,
        "interval_hours": 48,
        "skip_weekends": True,
    },
    "dedup": {
        "history_file": "./data/bosshunter-history.jsonl",
    },
}


def load_config(config_path: Path | None = None) -> dict[str, Any]:
    """Load configuration from YAML file, falling back to defaults.

    Resolution order for config path:
      1. Explicit *config_path* argument
      2. Env var BOSSHUNTER_CONFIG
      3. <project_root>/config.yaml
    """
    cfg = _deep_copy_dict(DEFAULTS)
    if config_path is None:
        env_path = os.environ.get("BOSSHUNTER_CONFIG")
        config_path = Path(env_path) if env_path else (PROJECT_ROOT / "config.yaml")
    if config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            user_cfg = yaml.safe_load(f) or {}
        _deep_merge(cfg, user_cfg)
    return cfg


def _deep_copy_dict(d: dict) -> dict:
    result = {}
    for k, v in d.items():
        if isinstance(v, dict):
            result[k] = _deep_copy_dict(v)
        elif isinstance(v, list):
            result[k] = v[:]
        else:
            result[k] = v
    return result


def _deep_merge(base: dict, override: dict) -> None:
    """Recursively merge override into base."""
    for k, v in override.items():
        if k in base and isinstance(base[k], dict) and isinstance(v, dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v
