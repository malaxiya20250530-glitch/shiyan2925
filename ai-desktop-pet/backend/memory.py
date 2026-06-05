"""记忆系统 —— 管理短期对话历史和长期记忆持久化。"""

import json
import os
import time
from typing import Optional


class MemoryStore:
    """宠物记忆管理，短时对话 + 长期知识持久化。"""

    def __init__(self, config_path: str = "config.json") -> None:
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        mem_cfg = cfg.get("memory", {})
        self.short_term_size: int = mem_cfg.get("short_term_size", 20)
        self.long_term_path: str = mem_cfg.get("long_term_path", "long_term_memory.json")
        self.summary_interval: int = mem_cfg.get("summary_interval", 10)

        self._short_term: list[dict] = []
        self._long_term: list[dict] = self._load_long_term()
        self._message_count: int = 0

    def add_message(self, role: str, content: str) -> None:
        """添加一条对话消息到短期记忆

        参数:
            role: "user" 或 "assistant"
            content: 消息文本
        """
        entry = {
            "role": role,
            "content": content,
            "timestamp": time.time()
        }
        self._short_term.append(entry)
        if len(self._short_term) > self.short_term_size:
            self._short_term.pop(0)

        self._message_count += 1
        if self._message_count % self.summary_interval == 0:
            self._summarize_and_persist()

    def get_recent_history(self, n: Optional[int] = None) -> list[dict]:
        """返回最近 n 条对话历史（不含时间戳）"""
        if n is None:
            n = self.short_term_size
        return [{"role": m["role"], "content": m["content"]}
                for m in self._short_term[-n:]]

    def get_long_term_context(self) -> str:
        """返回长期记忆的文本摘要，用于注入 LLM 上下文"""
        if not self._long_term:
            return ""
        recent = self._long_term[-3:]
        lines = [f"- {m.get('summary', m.get('content', ''))}" for m in recent]
        return "你记得这些关于主人的事:\n" + "\n".join(lines)

    def remember_fact(self, fact: str, category: str = "general") -> None:
        """手动存储一条长期事实"""
        entry = {
            "category": category,
            "summary": fact,
            "timestamp": time.time()
        }
        self._long_term.append(entry)
        self._save_long_term()

    # ─── 内部方法 ───

    def _summarize_and_persist(self) -> None:
        """对最近对话做简单摘要并存入长期记忆"""
        recent = self._short_term[-self.summary_interval:]
        user_msgs = [m["content"] for m in recent if m["role"] == "user"]
        if not user_msgs:
            return
        summary = f"用户最近的话题: {'; '.join(user_msgs[-3:])}"
        self.remember_fact(summary, category="conversation_summary")

    def _load_long_term(self) -> list[dict]:
        """从磁盘加载长期记忆"""
        if os.path.exists(self.long_term_path):
            try:
                with open(self.long_term_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return []
        return []

    def _save_long_term(self) -> None:
        """将长期记忆落盘"""
        with open(self.long_term_path, "w", encoding="utf-8") as f:
            json.dump(self._long_term, f, ensure_ascii=False, indent=2)
