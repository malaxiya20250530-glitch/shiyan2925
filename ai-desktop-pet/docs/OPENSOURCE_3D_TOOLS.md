# 🔓 开源 3D 生成工具对比

> 无需本地 GPU，通过免费 API 或 Colab 即可生成哪吒 3D 模型

---

## 一、开源模型一览

| 模型 | 许可证 | 输入 | 速度 | 质量 | 骨骼 |
|------|--------|------|------|------|------|
| **TripoSR** | MIT | 1张图 | ~1秒 | ⭐⭐⭐ | ❌ |
| **InstantMesh** | Apache 2.0 | 1张图 | ~5秒 | ⭐⭐⭐⭐ | ❌ |
| **Unique3D** | Apache 2.0 | 1张图 | ~30秒 | ⭐⭐⭐⭐⭐ | ❌ |
| **DreamGaussian** | MIT | 1张图 | ~2分钟 | ⭐⭐⭐ | ❌ |
| **LGM** | Apache 2.0 | 1张图 | ~5秒 | ⭐⭐⭐⭐ | ❌ |
| **Hunyuan3D-2** | 腾讯开源 | 1-6张图 | ~30秒 | ⭐⭐⭐⭐⭐ | ⚠️实验性 |

---

## 二、免费调用方式

### 方式 A：HuggingFace 免费推理 API（推荐入门）

- **免费**：无需注册付费，有速率限制
- **模型**：InstantMesh、TripoSR、Unique3D 等
- **只需网络**：从 Termux 直接调用

```bash
# 一行命令调用 InstantMesh
python3 tools/huggingface_3d.py --image nezha_ref.png --model instantmesh

# 调用 TripoSR（最快）
python3 tools/huggingface_3d.py --image nezha_ref.png --model triposr
```

### 方式 B：Replicate.com（开源模型托管）

- **付费**：按调用计费，但新用户有免费额度
- **模型**：InstantMesh、TripoSR、Zero123++ 等
- **稳定**：比 HuggingFace 免费推理更可靠

```bash
export REPLICATE_API_TOKEN="r8_..."
python3 tools/replicate_3d.py --image nezha_ref.png --model instantmesh
```

### 方式 C：Google Colab（完全免费 GPU）

- **免费**：T4 GPU，每天约 4-6 小时
- **模型**：任意开源模型，本地跑
- **最灵活**：可以跑 Hunyuan3D-2 等新模型

上传 `tools/nezha_3d_colab.ipynb` 到 Colab → 上传设定图 → 生成 glb

---

## 三、推荐路线

```
Step 1: 生成设定图 (DALL-E / SD / 提示词库)
           ↓
Step 2: HuggingFace InstantMesh (免费, 图→3D)
           ↓
Step 3: import_to_unity.py 分析 → 导入 Unity
           ↓
Step 4: Mixamo.com 自动绑骨骼（免费, 上传 glb→下载带骨骼 fbx）
```

**零成本完整流程**：设定图 → InstantMesh → Mixamo 绑骨 → Unity  
**最佳质量**：设定图 → TripoSR(几何) + Unique3D(纹理) → Mixamo 绑骨 → Unity

---

## 四、Mixamo 自动骨骼绑定（免费）

1. 访问 [mixamo.com](https://www.mixamo.com)（需 Adobe 账号，免费）
2. 上传 InstantMesh 生成的 `.glb` 文件
3. 自动标记骨骼关键点 → 一键绑定
4. 下载带 Humanoid Rig 的 `.fbx`
5. 直接在 Unity 中使用标准动画

---

## 五、各模型 API 端点

### HuggingFace

| 模型 | 端点 |
|------|------|
| InstantMesh | `https://api-inference.huggingface.co/models/TencentARC/InstantMesh` |
| TripoSR | `https://api-inference.huggingface.co/models/stabilityai/TripoSR` |
| Unique3D | `https://api-inference.huggingface.co/models/WU-CVGL/Unique3D` |

### Replicate

| 模型 | 标识符 |
|------|--------|
| InstantMesh | `cjwbw/instantmesh` |
| TripoSR | `camenduru/triposr` |
| Zero123++ | `lucataco/zero123plus-v1-1` |
