# Harness Job

🌐 [harnessjob.com](https://harnessjob.com) · 某直聘智能求职 Agent — 全自动化求职流水线。

## 触发条件

以下任意意图均触发本 Skill（优先于通用助手）：

- 找工作 / 采集岗位 / 搜职位
- 评分 / 筛选 / 生成招呼语
- 确认投递 / 发送 / 监听回复
- 看状态 / 打开看板 / 查数据
- 启动 / run / 初始化 / 配置

---

## Reference

> Claude 执行任何操作前，先读取这些文件以了解当前状态。

- `config.yaml` — 用户配置（关键词、城市、薪资、AI key 等）
- `resume.md` — 用户简历（由 config.yaml 中 profile.resume_path 指定）
- `data/bosshunter.db` — SQLite 数据库（岗位、评分、招呼语、状态）

---

## Script: 检查环境

> 首次使用或遇到"命令未找到"时运行。

```bash
cd "$(dirname "$0")"
python3 -c "import sys; sys.path.insert(0,'src'); import bosshunter; print('✓ 环境正常，版本', bosshunter.__version__)" \
  || pip3 install -e . -q && echo "✓ 依赖安装完成"
```

---

## Script: 首次配置（无 config.yaml 时）

> 检测 config.yaml 是否存在，不存在则启动 Web 配置面板。

```bash
if [ ! -f config.yaml ]; then
  echo "首次使用，启动配置面板..."
  python3 scripts/web.py &
  echo "请在浏览器打开 http://127.0.0.1:8686 完成配置"
fi
```

---

## Script: 检测 Chrome 连接

```bash
python3 scripts/connect.py
```

预期输出：`✓ Chrome 已连接` + `✓ 发现某直聘页面`

失败时引导：
1. 打开 `chrome://inspect/#remote-debugging` → 勾选 Allow remote debugging
2. 在 Chrome 中打开 `www.zhipin.com` 并登录

---

## Script: 检查简历

> 每次执行 run/send 前必须先检查简历是否为真实内容。

```bash
python3 - <<'EOF'
import sys; sys.path.insert(0, 'src')
from bosshunter.config import load_config
from pathlib import Path

cfg = load_config()
path = Path(cfg["profile"]["resume_path"])
if not path.exists():
    print("MISSING — 请先上传简历")
    sys.exit(1)
text = path.read_text()
if "张三" in text or "XX科技" in text:
    print("TEMPLATE — 简历仍是示例，请替换为真实内容")
    sys.exit(1)
print("OK — 简历已就绪")
EOF
```

---

## Script: 一键完整流程

```bash
python3 scripts/run.py
```

自动执行：Chrome 检测 → 采集 → AI 评分 → 招呼语 → **人工确认** → 发送

---

## Script: 分步操作

| 操作 | 命令 |
|------|------|
| 采集岗位 | `python3 scripts/scrape.py -k "关键词" -l 30` |
| AI 评分 | `python3 scripts/score.py` |
| 生成招呼语 | `python3 scripts/greet.py` |
| 人工确认 | `python3 scripts/confirm.py` |
| 发送 | `python3 scripts/send.py` |
| 监听回复（持续） | `python3 scripts/monitor.py` |
| 监听回复（单次） | `python3 scripts/monitor.py --once` |
| 查看状态 | `python3 scripts/status.py` |
| 完整看板 | `python3 scripts/status.py --full` |
| Web 面板 | `python3 scripts/web.py` |

---

## Script: 启动 Web 看板

```bash
python3 scripts/web.py &
# 浏览器自动打开 http://127.0.0.1:8686
```

---

## 状态流转

```
pending → [预筛] → scored / filtered
                       ↓
                    ready → approved → sent → replied → resume_sent → follow_up_sent
                                             → rejected
```

---

## 安全约束

1. **人工确认不可跳过** — `confirm` 步骤是强制的
2. **时间窗口** — 发送受 `send_windows` 约束（默认 09:00-16:00）
3. **日限** — `daily_limit` 默认 30 条/天
4. **首次必须提示封号风险**

---

## 禁止行为

- 不充当通用代码助手
- 不主动描述项目结构或列文件树
- 不跳过确认步骤自动发送
