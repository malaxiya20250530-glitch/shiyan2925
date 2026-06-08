#!/usr/bin/env python3
"""记忆加载器 — 从 .memory/ 读取三层记忆，生成 Agent 启动上下文"""
import json, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MEMORY_ROOT = ROOT / ".memory"

PROJECT_DIR = MEMORY_ROOT / "project"
USER_DIR = MEMORY_ROOT / "user"
SESSION_LATEST = MEMORY_ROOT / "session" / "latest.md"


def _read_md(path: Path) -> str:
    """安全读取 Markdown 文件，不存在返回空字符串"""
    try:
        if path.exists():
            return path.read_text(encoding="utf-8").strip()
    except Exception:
        pass
    return ""


def _list_md_files(directory: Path) -> list[Path]:
    """列出目录下所有 .md 文件"""
    if not directory.exists():
        return []
    return sorted(directory.glob("*.md"))


def load_project_memory() -> dict[str, str]:
    """加载项目记忆（architecture, roadmap, decisions）"""
    result = {}
    for md_file in _list_md_files(PROJECT_DIR):
        name = md_file.stem  # 不含扩展名
        content = _read_md(md_file)
        if content:
            result[name] = content
    return result


def load_user_memory() -> dict[str, str]:
    """加载用户记忆（preferences, habits）"""
    result = {}
    for md_file in _list_md_files(USER_DIR):
        name = md_file.stem
        content = _read_md(md_file)
        if content:
            result[name] = content
    return result


def load_session_context() -> str:
    """加载上次会话摘要"""
    return _read_md(SESSION_LATEST)


def context_summary() -> str:
    """生成 Agent 启动时可注入的紧凑上下文摘要"""
    project = load_project_memory()
    user = load_user_memory()
    session = load_session_context()

    parts = []

    # 会话恢复
    if session:
        parts.append("## 上次会话\n" + session)

    # 项目记忆
    if project:
        lines = ["## 项目记忆"]
        for name, content in project.items():
            # 取前 5 行作为摘要
            summary = "\n".join(content.split("\n")[:5])
            lines.append(f"### {name}\n{summary}")
        parts.append("\n".join(lines))

    # 用户偏好
    if user:
        lines = ["## 用户偏好"]
        for name, content in user.items():
            summary = "\n".join(content.split("\n")[:3])
            lines.append(f"### {name}\n{summary}")
        parts.append("\n".join(lines))

    if not parts:
        return "（记忆为空）"

    return "\n\n".join(parts)


def full_dump() -> dict:
    """完整导出所有记忆（JSON 格式）"""
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "project": load_project_memory(),
        "user": load_user_memory(),
        "session": load_session_context(),
    }


def main() -> None:
    if "--json" in sys.argv:
        print(json.dumps(full_dump(), ensure_ascii=False, indent=2))
    elif "--full" in sys.argv:
        data = full_dump()
        print(f"=== 上次会话 ===")
        print(data["session"] or "（无）")
        print(f"\n=== 项目记忆 ===")
        for k, v in data["project"].items():
            print(f"\n--- {k} ---")
            print(v)
        print(f"\n=== 用户记忆 ===")
        for k, v in data["user"].items():
            print(f"\n--- {k} ---")
            print(v)
    else:
        # 默认：紧凑上下文
        print(context_summary())


if __name__ == "__main__":
    main()
