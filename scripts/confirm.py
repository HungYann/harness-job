#!/usr/bin/env python3
"""展示投递清单并逐个/批量确认（交互式终端）。

用法：
    python3 scripts/confirm.py
"""
import _bootstrap  # noqa: F401
from bosshunter.config import load_config
from bosshunter.ui.confirm import show_confirmation

config = load_config()
show_confirmation(config)
