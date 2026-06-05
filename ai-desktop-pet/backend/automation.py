"""手机自动化引擎 —— 通过 Termux:API 执行系统操作。"""

import json
import subprocess
import os
from typing import Optional


class AutomationEngine:
    """手机自动化执行器，封装 Termux:API 命令。"""

    # 常用应用包名映射
    APP_PACKAGES: dict[str, str] = {
        "微信": "com.tencent.mm",
        "QQ": "com.tencent.mobileqq",
        "支付宝": "com.eg.android.AlipayGphone",
        "淘宝": "com.taobao.taobao",
        "抖音": "com.ss.android.ugc.aweme",
        "微博": "com.sina.weibo",
        "哔哩哔哩": "tv.danmaku.bili",
        "B站": "tv.danmaku.bili",
        "小红书": "com.xingin.xhs",
        "知乎": "com.zhihu.android",
        "设置": "com.android.settings",
        "相机": "com.android.camera",
        "相册": "com.android.gallery3d",
        "日历": "com.android.calendar",
        "时钟": "com.android.deskclock",
        "计算器": "com.android.calculator2",
        "音乐": "com.android.music",
        "浏览器": "com.android.browser",
        "Chrome": "com.android.chrome",
    }

    def __init__(self, config_path: str = "config.json") -> None:
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        auto_cfg = cfg.get("automation", {})
        self.enabled: bool = auto_cfg.get("enabled", True)
        self.require_confirmation: bool = auto_cfg.get("require_confirmation", True)
        self.allowed_actions: list[str] = auto_cfg.get("allowed_actions", [])
        self._check_termux_api()

    def _check_termux_api(self) -> bool:
        """检查 Termux:API 是否可用"""
        try:
            result = subprocess.run(
                ["termux-notification-list"],
                capture_output=True, text=True, timeout=5
            )
            # 即使命令失败，只要没报 "command not found" 就算 API 存在
            if "No such file" in result.stderr or "not found" in result.stderr:
                self.enabled = False
                return False
            return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            self.enabled = False
            return False

    def execute(self, action_type: str, target: str,
                params: Optional[dict] = None) -> dict:
        """执行自动化操作

        参数:
            action_type: 操作类型 (open_app, send_notification, clipboard, volume, brightness, take_screenshot)
            target: 操作目标 (应用名/包名、通知文本等)
            params: 额外参数
        返回:
            {"success": bool, "message": str}
        """
        if not self.enabled:
            return {"success": False, "message": "自动化引擎未启用（Termux:API 不可用）"}

        if action_type not in self.allowed_actions:
            return {"success": False, "message": f"操作 '{action_type}' 不在允许列表中"}

        handlers = {
            "open_app": self._open_app,
            "send_notification": self._send_notification,
            "clipboard": self._set_clipboard,
            "volume": self._set_volume,
            "brightness": self._set_brightness,
            "take_screenshot": self._take_screenshot,
        }

        handler = handlers.get(action_type)
        if handler is None:
            return {"success": False, "message": f"未知操作类型: {action_type}"}

        return handler(target, params or {})

    def parse_intent_from_text(self, text: str) -> Optional[dict]:
        """从自然语言中解析自动化意图

        返回: {"action_type": str, "target": str, "params": dict} 或 None
        """
        text_lower = text.lower()

        # 打开应用
        for app_name, pkg in self.APP_PACKAGES.items():
            if app_name in text:
                return {"action_type": "open_app", "target": app_name, "params": {}}

        # 发送通知
        if "通知" in text or "提醒" in text:
            return {"action_type": "send_notification", "target": "宠物提醒",
                    "params": {"title": "桌面精灵提醒", "content": text}}

        # 截屏
        if "截屏" in text or "截图" in text:
            return {"action_type": "take_screenshot", "target": "screenshot", "params": {}}

        return None

    # ─── 内部操作方法 ───

    def _open_app(self, target: str, params: dict) -> dict:
        """打开指定应用"""
        pkg = self.APP_PACKAGES.get(target, target)
        try:
            subprocess.run(
                ["am", "start", "-n", f"{pkg}/.MainActivity"],
                capture_output=True, timeout=10
            )
            # 备选：用 monkey 命令
            subprocess.run(
                ["monkey", "-p", pkg, "-c", "android.intent.category.LAUNCHER", "1"],
                capture_output=True, timeout=10
            )
            return {"success": True, "message": f"已打开 {target}"}
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            return {"success": False, "message": f"打开应用失败: {e}"}

    def _send_notification(self, target: str, params: dict) -> dict:
        """发送系统通知"""
        title = params.get("title", "桌面精灵")
        content = params.get("content", target)
        try:
            subprocess.run(
                ["termux-notification", "--title", title, "--content", content],
                capture_output=True, timeout=5
            )
            return {"success": True, "message": "通知已发送"}
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            return {"success": False, "message": f"发送通知失败: {e}"}

    def _set_clipboard(self, target: str, params: dict) -> dict:
        """设置剪贴板内容"""
        try:
            subprocess.run(
                ["termux-clipboard-set", target],
                capture_output=True, timeout=5
            )
            return {"success": True, "message": "已复制到剪贴板"}
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            return {"success": False, "message": f"剪贴板操作失败: {e}"}

    def _set_volume(self, target: str, params: dict) -> dict:
        """调整音量（target 应为 0-15 的数字字符串）"""
        try:
            vol = int(target)
            vol = max(0, min(15, vol))
            subprocess.run(
                ["media", "volume", "--set", str(vol)],
                capture_output=True, timeout=5
            )
            return {"success": True, "message": f"音量已设为 {vol}"}
        except (ValueError, FileNotFoundError, subprocess.TimeoutExpired) as e:
            return {"success": False, "message": f"音量调节失败: {e}"}

    def _set_brightness(self, target: str, params: dict) -> dict:
        """调整亮度（target 应为 0-255 的数字字符串）"""
        try:
            bri = int(target)
            bri = max(0, min(255, bri))
            subprocess.run(
                ["settings", "put", "system", "screen_brightness", str(bri)],
                capture_output=True, timeout=5
            )
            return {"success": True, "message": f"亮度已设为 {bri}"}
        except (ValueError, FileNotFoundError, subprocess.TimeoutExpired) as e:
            return {"success": False, "message": f"亮度调节失败: {e}"}

    def _take_screenshot(self, target: str, params: dict) -> dict:
        """截屏并保存"""
        save_path = params.get("path",
                               f"/data/data/com.termux/files/home/ai-desktop-pet/screenshots/shot_{int(__import__('time').time())}.png")
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        try:
            subprocess.run(
                ["termux-screenshot", save_path],
                capture_output=True, timeout=10
            )
            return {"success": True, "message": f"截图已保存到 {save_path}"}
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            return {"success": False, "message": f"截图失败: {e}"}
