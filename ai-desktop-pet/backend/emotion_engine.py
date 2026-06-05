"""情绪引擎 —— 管理宠物的情绪状态，支持衰减、触发词检测、事件响应。"""

import json
import random
import time
from typing import Optional


class EmotionEngine:
    """情绪状态机，管理情绪值的增减、衰减和转换。"""

    EMOTION_TRIGGERS: dict[str, tuple[str, ...]] = {
        "happy": ("哈哈", "开心", "太好了", "喜欢", "谢谢", "爱你", "棒", "👍", "😊"),
        "sad": ("难过", "伤心", "呜呜", "哭了", "失败", "遗憾", "😢"),
        "angry": ("生气", "可恶", "讨厌", "滚", "烦", "😠", "找死"),
        "surprised": ("天哪", "居然", "什么", "不是吧", "震惊", "😲"),
        "sleepy": ("困", "累", "睡觉", "晚安", "😴"),
        "excited": ("冲", "庆祝", "太棒了", "牛逼", "🎉"),
        "shy": ("害羞", "不好意思", "脸红", "😳"),
        # 哪吒专属：燃起来！
        "fired_up": ("战斗", "来吧", "开打", "不认命", "拼了", "燃", "🔥", "⚡")
    }

    def __init__(self, config_path: str = "config.json") -> None:
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        emo_cfg = cfg.get("emotion", {})
        self.decay_rate: float = emo_cfg.get("decay_rate", 0.04)
        self.boost_intensity: float = emo_cfg.get("boost_intensity", 0.35)
        self.update_interval: int = emo_cfg.get("update_interval_sec", 5)

        # 情绪值字典，范围 [0, 1]
        self._values: dict[str, float] = {s: 0.0 for s in emo_cfg.get("states", ["neutral", "happy"])}
        self._values["neutral"] = 1.0  # 默认平静
        self._last_update: float = time.time()

    @property
    def dominant_emotion(self) -> str:
        """返回当前主导情绪（值最高的那个）"""
        if not self._values:
            return "neutral"
        return max(self._values, key=self._values.get)

    @property
    def emotion_values(self) -> dict[str, float]:
        """返回所有情绪值快照"""
        return dict(self._values)

    def tick(self) -> None:
        """时间推进 —— 触发情绪衰减"""
        now = time.time()
        if now - self._last_update < self.update_interval:
            return
        self._last_update = now
        for key in list(self._values):
            if key == "neutral":
                continue
            self._values[key] = max(0.0, self._values[key] - self.decay_rate)

    def detect_from_text(self, text: str) -> Optional[str]:
        """从用户输入文本中检测情绪触发词，返回触发的情绪名称或 None"""
        for emotion, keywords in self.EMOTION_TRIGGERS.items():
            for kw in keywords:
                if kw in text:
                    self._boost(emotion)
                    return emotion
        return None

    def boost(self, emotion: str) -> None:
        """手动提升某情绪值（如事件触发）"""
        if emotion in self._values:
            self._boost(emotion)

    def _boost(self, emotion: str) -> None:
        """内部：提升指定情绪值并自动衰减其他情绪"""
        self._values[emotion] = min(1.0, self._values.get(emotion, 0.0) + self.boost_intensity)
        self._values["neutral"] = max(0.0, self._values.get("neutral", 0.5) - self.boost_intensity * 0.5)
        # 哪吒专属：fired_up 时 angry 和 excited 也联动提升
        if emotion == "fired_up":
            self._values["angry"] = min(1.0, self._values.get("angry", 0.0) + self.boost_intensity * 0.6)
            self._values["excited"] = min(1.0, self._values.get("excited", 0.0) + self.boost_intensity * 0.4)

    def reset_to_neutral(self) -> None:
        """重置所有情绪为 neutral"""
        for key in self._values:
            self._values[key] = 0.0
        self._values["neutral"] = 1.0

    def get_animation_hint(self) -> str:
        """根据当前情绪返回建议的动画类型"""
        emotion = self.dominant_emotion
        mapping = {
            "happy": "bounce",
            "sad": "droop",
            "angry": "stomp",
            "surprised": "jump",
            "sleepy": "yawn",
            "excited": "spin",
            "shy": "hide",
            "fired_up": "battle_pose",   # 哪吒专属：战斗姿态
            "neutral": "idle"
        }
        return mapping.get(emotion, "idle")
