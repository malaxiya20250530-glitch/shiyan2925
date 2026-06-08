#!/usr/bin/env python3
"""会话摘要生成器 — 退出前自动生成 .memory/session/latest.md"""
import json, os, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SESSION_DIR = ROOT / ".memory" / "session"
LATEST = SESSION_DIR / "latest.md"
ARCHIVE = SESSION_DIR / "archive"
SESSION_STATE = ROOT / ".codex_session.json"


def _git_log(limit: int = 5) -> str:
    """获取最近 Git 提交记录"""
    try:
        r = subprocess.run(
            ["git", "-C", str(ROOT), "log", f"-{limit}", "--oneline", "--no-decorate"],
            capture_output=True, text=True, timeout=5
        )
        return r.stdout.strip() or "（无提交记录）"
    except Exception:
        return "（无法获取 git 日志）"


def _git_diff_summary() -> str:
    """获取未提交改动摘要"""
    try:
        r = subprocess.run(
            ["git", "-C", str(ROOT), "status", "--short"],
            capture_output=True, text=True, timeout=5
        )
        return r.stdout.strip() or "（工作区干净）"
    except Exception:
        return "（无法获取）"


def _load_session_state() -> dict:
    """加载会话状态"""
    try:
        if SESSION_STATE.exists():
            return json.loads(SESSION_STATE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def generate() -> str:
    """生成会话摘要 Markdown 文本"""
    now = datetime.now(timezone.utc)
    state = _load_session_state()
    git_log = _git_log(5)
    git_status = _git_diff_summary()

    lines = [
        f"# 会话摘要",
        f"",
        f"**时间**: {now.strftime('%Y-%m-%d %H:%M:%S UTC')}",
        f"",
        f"## 当前任务",
        f"{state.get('current_task', '（未记录）')}",
        f"",
        f"## 任务状态",
        f"{state.get('task_status', 'unknown')}",
        f"",
        f"## 最近提交",
        f"```",
        git_log,
        f"```",
        f"",
        f"## 工作区状态",
        f"```",
        git_status,
        f"```",
    ]

    if state.get("checkpoint_notes"):
        lines += ["", "## 断点备注", state["checkpoint_notes"]]

    if state.get("files_touched"):
        lines += ["", "## 涉及文件"]
        for f in state["files_touched"]:
            lines.append(f"- `{f}`")

    return "\n".join(lines) + "\n"


def write() -> Path:
    """生成摘要并写入 latest.md，旧版归档"""
    # 归档旧版本
    if LATEST.exists():
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_path = ARCHIVE / f"session_{ts}.md"
        LATEST.rename(archive_path)

    content = generate()
    LATEST.write_text(content, encoding="utf-8")
    return LATEST


def main() -> None:
    if "--print" in sys.argv:
        print(generate())
    else:
        path = write()
        print(f"✅ 会话摘要已写入: {path}")


if __name__ == "__main__":
    main()
