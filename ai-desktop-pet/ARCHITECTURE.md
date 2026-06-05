# 🐾 AI虚拟桌面精灵 — 系统架构

## 概述

AI虚拟桌面精灵是一个运行在 Android 设备上的 3D 虚拟宠物系统，
具备 LLM 驱动的智能对话、情绪表达、以及手机自动化操控能力。

## 系统分层

```
┌──────────────────────────────────────────────┐
│          Unity 3D 渲染层 (前端)               │
│  PetCore.cs  |  PetAnimationController.cs    │
│  PetEmotionSystem.cs                        │
│  ┌─────────────────────────────────────┐    │
│  │  3D角色模型 · 动画状态机 · 触摸交互  │    │
│  │  SpeechBubble · 表情系统 · 粒子特效  │    │
│  └─────────────────────────────────────┘    │
└──────────────────┬───────────────────────────┘
                   │ WebSocket (ws://127.0.0.1:9527)
┌──────────────────▼───────────────────────────┐
│        Python AI 后端 (Termux 进程)           │
│  pet_server.py     — WebSocket 服务主控      │
│  llm_engine.py     — LLM 对话引擎            │
│  emotion_engine.py — 情绪状态机              │
│  personality.py    — 性格系统                │
│  automation.py     — 手机自动化引擎          │
│  memory.py         — 短期/长期记忆           │
└──────────────────┬───────────────────────────┘
                   │ Termux:API
┌──────────────────▼───────────────────────────┐
│           Android 系统桥接层                  │
│  floating_window.sh — 悬浮窗管理             │
│  notify.sh          — 系统通知               │
│  sensor.sh          — 传感器数据             │
│  ┌─────────────────────────────────────┐    │
│  │  MediaProjection · 无障碍服务        │    │
│  │  通知监听 · 剪贴板 · 传感器         │    │
│  └─────────────────────────────────────┘    │
└──────────────────────────────────────────────┘
```

## 数据流

```
用户触摸/语音 → Unity前端 → WebSocket → pet_server.py
                                         ├→ llm_engine.py (生成回复)
                                         ├→ emotion_engine.py (更新情绪)
                                         ├→ memory.py (存储上下文)
                                         └→ automation.py (执行自动化)
                                              ↓
Unity前端 ← WebSocket ← 回复JSON (文本+情绪+动作指令)
```

## 通信协议 (WebSocket JSON)

### 前端 → 后端

```json
{
  "type": "user_input",
  "content": "帮我打开微信",
  "context": {"app_focus": "home", "time": "14:30"}
}
```

### 后端 → 前端

```json
{
  "type": "pet_response",
  "text": "好的，正在帮你打开微信~",
  "emotion": "happy",
  "animation": "wave",
  "action": {"type": "open_app", "target": "com.tencent.mm"}
}
```

## 部署方式

1. **Python 后端**：在 Termux 中运行 `python3 backend/pet_server.py`
2. **Unity 前端**：在桌面 Unity Editor 中打开 `unity_project/`，构建 Android APK
3. **Android 桥接**：通过 Termux:API 与系统交互
4. **通信**：Unity APK 通过 WebSocket 连接本地 Termux 后端

## 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| 3D渲染 | Unity 2022.3 LTS | C# + URP |
| AI后端 | Python 3 | 纯标准库 + 异步WebSocket |
| LLM | OpenAI API / 本地模型 | 可配置多后端 |
| Android桥接 | Termux:API | Bash + Python 封装 |
| 通信 | WebSocket | asyncio + websockets |
