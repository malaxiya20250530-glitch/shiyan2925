#!/usr/bin/env python3
"""
HuggingFace 开源 3D 模型推理（免费，无需 GPU）
支持 InstantMesh / TripoSR / Unique3D
"""

import json
import os
import sys
import time
import base64
import urllib.request
import urllib.error
import argparse
from pathlib import Path


# ═══════════════════════════════════════════
# 模型注册表
# ═══════════════════════════════════════════

MODELS = {
    "instantmesh": {
        "name": "TencentARC/InstantMesh",
        "desc": "腾讯开源，图生3D，5秒出图，Apache 2.0",
        "api_url": "https://api-inference.huggingface.co/models/TencentARC/InstantMesh",
        "input_key": "image",
        "output_format": "glb",
    },
    "triposr": {
        "name": "stabilityai/TripoSR",
        "desc": "Stability AI + Tripo 联合开源，1秒极速，MIT 许可",
        "api_url": "https://api-inference.huggingface.co/models/stabilityai/TripoSR",
        "input_key": "image",
        "output_format": "glb",
    },
    "unique3d": {
        "name": "WU-CVGL/Unique3D",
        "desc": "高质量纹理重建，约30秒，Apache 2.0",
        "api_url": "https://api-inference.huggingface.co/models/WU-CVGL/Unique3D",
        "input_key": "image",
        "output_format": "glb",
    },
}


class HuggingFace3D:
    """通过 HuggingFace 免费推理 API 调用开源 3D 模型"""

    def __init__(self, hf_token: str | None = None) -> None:
        self.token = hf_token or os.environ.get("HF_TOKEN", "")
        if not self.token:
            print("⚠️  未设置 HF_TOKEN，将使用匿名访问（可能被限速）")
            print("   免费注册: https://huggingface.co/settings/tokens")
            print("   匿名也可用，但速率受限\n")

    def image_to_3d(self, image_path: str, model: str = "instantmesh",
                    output_dir: str = "./hf_output") -> str | None:
        """图片转 3D 模型

        参数:
            image_path: 输入图片（正面视图最佳）
            model: 模型标识 (instantmesh / triposr / unique3d)
            output_dir: 输出目录
        返回:
            下载的 GLB 文件路径
        """
        if not os.path.exists(image_path):
            sys.exit(f"❌ 图片不存在: {image_path}")

        if model not in MODELS:
            valid = ", ".join(MODELS.keys())
            sys.exit(f"❌ 未知模型: {model}\n   可选: {valid}")

        info = MODELS[model]
        print(f"🔓 HuggingFace 开源推理: {info['desc']}")
        print(f"   模型: {info['name']}")
        print(f"   输入: {image_path}")

        # 读取图片并 base64 编码
        with open(image_path, "rb") as f:
            image_bytes = f.read()

        # HuggingFace API 调用
        api_url = info["api_url"]
        headers = {"Content-Type": "application/octet-stream"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        req = urllib.request.Request(api_url, data=image_bytes, method="POST")
        for k, v in headers.items():
            req.add_header(k, v)

        print("   ⏳ 推理中（免费模型首次加载可能需要 20-60 秒）...")

        # 轮询等待（HuggingFace 冷启动可能较慢）
        max_attempts = 12
        for attempt in range(max_attempts):
            try:
                with urllib.request.urlopen(req, timeout=120) as resp:
                    content_type = resp.headers.get("Content-Type", "")

                    if "application/json" in content_type:
                        # 返回 JSON → 任务排队中
                        data = json.loads(resp.read().decode())
                        if "error" in data:
                            error_msg = data["error"]
                            if "loading" in str(error_msg).lower():
                                wait = min(10 * (attempt + 1), 30)
                                print(f"   ⏳ 模型加载中... 等待 {wait}s ({attempt+1}/{max_attempts})")
                                time.sleep(wait)
                                continue
                            else:
                                print(f"   ✗ 错误: {error_msg}")
                                return None

                    # 成功返回 → 可能是 GLB 二进制
                    data = resp.read()
                    if len(data) < 1000:
                        # 太小，可能是 JSON 错误
                        text = data.decode(errors="replace")
                        print(f"   ✗ 异常响应: {text[:200]}")
                        return None

                    # 保存 GLB
                    os.makedirs(output_dir, exist_ok=True)
                    timestamp = int(time.time())
                    filename = f"nezha_{model}_{timestamp}.glb"
                    filepath = os.path.join(output_dir, filename)

                    with open(filepath, "wb") as out:
                        out.write(data)

                    size_mb = len(data) / (1024 * 1024)
                    print(f"   ✓ {filepath} ({size_mb:.1f}MB)")
                    return filepath

            except urllib.error.HTTPError as e:
                error_body = e.read().decode(errors="replace")
                if e.code == 503 and attempt < max_attempts - 1:
                    wait = min(10 * (attempt + 1), 30)
                    print(f"   ⏳ 模型启动中 (503)... {wait}s 后重试")
                    time.sleep(wait)
                else:
                    print(f"   ✗ HTTP {e.code}: {error_body[:200]}")
                    return None

        print("   ✗ 超时：模型加载时间过长，请稍后重试")
        return None


# ─── CLI ───

def main() -> None:
    parser = argparse.ArgumentParser(
        description="🔓 HuggingFace 开源 3D 模型推理",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
模型:
  instantmesh  腾讯 InstantMesh — 图生3D，~5秒 (推荐入门)
  triposr      TripoSR — 图生3D，~1秒 (极速)
  unique3d     Unique3D — 图生3D，高质量纹理 (~30秒)

示例:
  # 免费推理（匿名访问）
  python3 huggingface_3d.py --image nezha_front.png --model instantmesh

  # 带 token（更高频率限制）
  export HF_TOKEN="hf_..."
  python3 huggingface_3d.py --image nezha_front.png --model triposr

  # 对比三种模型
  for m in instantmesh triposr unique3d; do
    python3 huggingface_3d.py --image nezha_front.png --model $m
  done
        """
    )
    parser.add_argument("--image", "-i", required=True, help="输入图片（正面视图最佳）")
    parser.add_argument("--model", "-m", default="instantmesh",
                        choices=list(MODELS.keys()),
                        help="模型选择 (默认: instantmesh)")
    parser.add_argument("--output", "-o", default="./hf_output",
                        help="输出目录 (默认: ./hf_output)")
    parser.add_argument("--token", help="HuggingFace Token（或设环境变量 HF_TOKEN）")

    args = parser.parse_args()

    gen = HuggingFace3D(hf_token=args.token)
    result = gen.image_to_3d(args.image, args.model, args.output)

    if result:
        print(f"\n🎉 3D 模型已生成: {result}")
        print(f"\n📋 后续步骤:")
        print(f"   1. 分析模型: python3 tools/import_to_unity.py {result}")
        print(f"   2. 免费绑骨骼: 上传到 https://mixamo.com → 下载 fbx")
        print(f"   3. 导入 Unity → 挂载 PetCore.cs")
    else:
        print("\n❌ 生成失败")
        print("   提示:")
        print("   - 首次调用模型需要加载 ~20-60 秒，重试即可")
        print("   - 匿名访问速率有限，建议设置 HF_TOKEN")
        print("   - 获取 Token: https://huggingface.co/settings/tokens")
        print("   - 备选: Google Colab (完全免费 GPU)")
        print("   - 备选: Replicate API (新用户有免费额度)")
        sys.exit(1)


if __name__ == "__main__":
    main()
