"""LLM 对话引擎 —— 负责与语言模型交互，生成宠物回复。"""

import json
import urllib.request
import urllib.error
from typing import Optional


class LLMEngine:
    """封装 LLM API 调用，支持 OpenAI 兼容接口。"""

    def __init__(self, config_path: str = "config.json") -> None:
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        llm_cfg = cfg["llm"]
        self.api_base: str = llm_cfg["api_base"]
        self.model: str = llm_cfg["model"]
        self.max_tokens: int = llm_cfg["max_tokens"]
        self.temperature: float = llm_cfg["temperature"]
        self.system_prompt: str = llm_cfg["system_prompt"]
        self.api_key: str = self._load_api_key()

    def _load_api_key(self) -> str:
        """从环境变量加载 API 密钥"""
        import os
        return os.environ.get("OPENAI_API_KEY", "")

    def chat(self, user_message: str, history: Optional[list[dict]] = None,
             emotion: str = "neutral", personality_hint: str = "") -> str:
        """发送对话请求，返回模型回复文本。

        参数:
            user_message: 用户输入文本
            history: 对话历史 [{"role":"user/assistant","content":"..."}]
            emotion: 当前情绪状态
            personality_hint: 性格提示词追加
        返回:
            模型回复的纯文本
        """
        if history is None:
            history = []

        messages = [{"role": "system", "content": self._build_system_prompt(emotion, personality_hint)}]
        messages.extend(history[-20:])  # 只保留最近 20 条历史
        messages.append({"role": "user", "content": user_message})

        body = json.dumps({
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature
        }).encode("utf-8")

        url = f"{self.api_base}/chat/completions"
        req = urllib.request.Request(url, data=body, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("Authorization", f"Bearer {self.api_key}")

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["choices"][0]["message"]["content"].strip()
        except urllib.error.URLError as e:
            return f"(网络错误，暂时无法回复: {e.reason})"
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            return f"(API 响应异常: {type(e).__name__})"

    def _build_system_prompt(self, emotion: str, personality_hint: str) -> str:
        """构建带情绪和性格的系统提示词"""
        emotion_guide = {
            "happy": "你现在很开心，语气轻快活泼。",
            "sad": "你现在有点低落，语气温柔带点忧伤。",
            "angry": "你现在有点生气，语气直接但克制。",
            "surprised": "你感到惊讶，语气充满意外感。",
            "sleepy": "你有点困，语气慵懒。",
            "excited": "你超级兴奋，语气充满能量！",
            "shy": "你有点害羞，语气软糯。",
            "neutral": "你心情平和，语气自然。"
        }
        emotion_line = emotion_guide.get(emotion, "")
        parts = [self.system_prompt]
        if emotion_line:
            parts.append(emotion_line)
        if personality_hint:
            parts.append(personality_hint)
        parts.append("回复简洁友善，不超过80个字。")
        return " ".join(parts)
