#!/usr/bin/env python3
"""记忆写入器 — 向 .memory/ 三层结构写入记忆，支持追加和覆盖"""
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MEMORY_ROOT = ROOT / ".memory"

# 合法目标文件映射
VALID_TARGETS = {
    # project 层
    "architecture": MEMORY_ROOT / "project" / "architecture.md",
    "roadmap": MEMORY_ROOT / "project" / "roadmap.md",
    "decisions": MEMORY_ROOT / "project" / "decisions.md",
    # user 层
    "preferences": MEMORY_ROOT / "user" / "preferences.md",
    "habits": MEMORY_ROOT / "user" / "habits.md",
}


def _timestamp() -> str:
    """生成时间戳标记"""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def write_memory(target: str, content: str, mode: str = "append") -> Path:
    """写入记忆到指定目标文件

    参数:
        target: 目标文件名（不含 .md），如 'architecture', 'preferences'
        content: 要写入的内容
        mode: 'append' 追加（默认）或 'overwrite' 覆盖
    返回:
        写入的文件路径
    """
    if target not in VALID_TARGETS:
        valid = ", ".join(VALID_TARGETS)
        raise ValueError(f"无效目标 '{target}'，合法值: {valid}")

    path = VALID_TARGETS[target]
    path.parent.mkdir(parents=True, exist_ok=True)

    if mode == "overwrite":
        path.write_text(content.strip() + "\n", encoding="utf-8")
    else:
        # 追加模式：加时间戳前缀
        entry = f"\n## {_timestamp()}\n\n{content.strip()}\n"
        with open(path, "a", encoding="utf-8") as f:
            f.write(entry)

    return path


def main() -> None:
    if len(sys.argv) < 3:
        print("用法: python3 memory_writer.py <目标> <内容> [--overwrite]")
        print(f"目标: {', '.join(VALID_TARGETS)}")
        print("默认追加模式，加 --overwrite 覆盖写入")
        print()
        print("示例:")
        print('  python3 memory_writer.py architecture "改用责任链模式"')
        print('  python3 memory_writer.py roadmap "Q3: 接入语义索引" --overwrite')
        sys.exit(1)

    target = sys.argv[1]
    content = sys.argv[2]
    mode = "overwrite" if "--overwrite" in sys.argv else "append"

    try:
        path = write_memory(target, content, mode)
        print(f"✅ 已写入: {path} ({mode})")
    except ValueError as e:
        print(f"❌ {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
