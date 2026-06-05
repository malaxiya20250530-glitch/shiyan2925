# 🎮 Unity 3D 桌面精灵前端

## 导入步骤

本目录包含 AI 桌面精灵的 Unity 3D 前端脚本，需要在桌面端 Unity Editor 中打开和构建。

### 环境要求

- **Unity 2022.3 LTS** 或更高版本
- **Android Build Support** 模块（Unity Hub 中安装）
- **Android SDK / NDK**（Unity 自动管理或手动配置）

### 导入流程

1. 打开 **Unity Hub** → 新建项目
   - 模板：**3D (URP)** 或 **3D (Built-in)**
   - 项目名：`AIDesktopPet`

2. 将 `Assets/Scripts/` 目录下的所有 `.cs` 文件复制到项目的 `Assets/Scripts/` 中

3. 场景搭建：
   - 创建空 GameObject 命名为 `PetRoot`
   - 挂载脚本：`PetCore`、`PetEmotionSystem`、`AIConnector`、`FloatingWindowBridge`
   - 创建子物体 `SpeechBubble`（Canvas → Panel → Text），挂载 `SpeechBubble` 脚本

4. 导入 3D 模型（推荐格式）：
   - **VRM** 格式（推荐）：从 VRoid Hub 下载或用 VRoid Studio 创建
   - **FBX** 格式：需手动设置 Animator Controller
   - 将模型拖到 `PetRoot` 下作为子物体

5. 配置 Animator：
   - 创建 Animator Controller，添加以下动画状态：`idle`, `bounce`, `spin`, `wave`, `yawn`, `jump`, `stomp`, `droop`, `hide`, `stretch`, `look_around`
   - 每个状态设置 Trigger 参数（与代码中的 `PlayAnimation()` 对应）

6. Build Settings：
   - 切换到 **Android** 平台
   - Player Settings → Resolution → **Fullscreen Window** 关闭
   - 设置自定义分辨率（如 400×500）
   - 启用 **Transparent Background**（需要修改 AndroidManifest）

### 场景层级结构参考

```
PetRoot (PetCore + PetEmotionSystem + AIConnector + FloatingWindowBridge)
├── Model (3D 模型 + Animator)
│   └── Face (SkinnedMeshRenderer - BlendShapes)
├── Canvas (World Space, 对话气泡)
│   └── SpeechBubble (SpeechBubble)
│       ├── Background (Image)
│       └── Text (Text / TMP)
└── EventSystem
```

### Android 透明背景配置

在 `Assets/Plugins/Android/AndroidManifest.xml` 中添加：

```xml
<activity android:theme="@android:style/Theme.Translucent.NoTitleBar">
```

### 连接后端

- 后端默认地址：`ws://127.0.0.1:9527`
- 可在 Unity Inspector 中修改 `AIConnector.serverUrl`
- 确保手机和 Termux 在同一设备（本地回环）
