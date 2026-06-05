#!/usr/bin/env python3
"""
Replicate.com 开源 3D 模型 API（稳定托管，新用户有免费额度）
支持 InstantMesh / TripoSR / Zero123++ / 等
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
        "owner": "cjwbw",
        "name": "instantmesh",
        "desc": "腾讯 InstantMesh — 单图转 3D，~5秒",
        "version": None,  # 使用最新版本
    },
    "triposr": {
        "owner": "camenduru",
        "name": "triposr",
        "desc": "TripoSR — 极速 1 秒，MIT 许可",
        "version": None,
    },
    "zero123plus": {
        "owner": "lucataco",
        "name": "zero123plus-v1-1",
        "desc": "Zero123++ — 单图生成多视角 → 可用于 3D 重建",
        "version": None,
    },
}


class Replicate3D:
    """通过 Replicate API 调用托管的开源 3D 模型"""

    BASE_URL = "https://api.replicate.com/v1"

    def __init__(self, api_token: str | None = None) -> None:
        self.token = api_token or os.environ.get("REPLICATE_API_TOKEN", "")
        if not self.token:
            sys.exit(
                "❌ 请设置 REPLICATE_API_TOKEN 环境变量\n"
                "   免费注册: https://replicate.com/signin\n"
                "   获取 Token: https://replicate.com/account/api-tokens\n"
                "   新用户有免费额度，按量计费"
            )

    def image_to_3d(self, image_path: str, model: str = "instantmesh",
                    output_dir: str = "./replicate_output") -> str | None:
        """图片转 3D 模型

        参数:
            image_path: 输入图片路径
            model: 模型标识
            output_dir: 输出目录
        返回:
            下载的模型文件路径
        """
        if not os.path.exists(image_path):
            sys.exit(f"❌ 图片不存在: {image_path}")

        if model not in MODELS:
            sys.exit(f"❌ 未知模型: {model}\n   可选: {', '.join(MODELS)}")

        info = MODELS[model]
        model_id = f"{info['owner']}/{info['name']}"
        print(f"🔷 Replicate 推理: {info['desc']}")
        print(f"   模型: {model_id}")
        print(f"   输入: {image_path}")

        # 上传图片获取 data URI
        with open(image_path, "rb") as f:
            ext = os.path.splitext(image_path)[1].lower().lstrip(".")
            mime = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "webp": "webp"}.get(ext, "png")
            image_b64 = base64.b64encode(f.read()).decode()
        image_uri = f"data:image/{mime};base64,{image_b64}"

        # 创建预测
        prediction = self._create_prediction(model_id, {"image": image_uri})
        if not prediction:
            return None

        # 轮询等待完成
        result = self._poll_prediction(prediction)
        if not result:
            return None

        # 下载结果
        output_url = self._extract_model_url(result)
        if not output_url:
            print("   ✗ 未在输出中找到 3D 模型文件")
            print(f"   原始输出: {json.dumps(result, indent=2)[:300]}")
            return None

        return self._download(output_url, output_dir, model)

    # ─── 内部方法 ───

    def _create_prediction(self, model_id: str, input_data: dict) -> dict | None:
        """创建 Replicate 预测任务"""
        url = f"{self.BASE_URL}/models/{model_id}/predictions"
        body = json.dumps({"input": input_data}).encode("utf-8")

        req = urllib.request.Request(url, data=body, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("Authorization", f"Bearer {self.token}")

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode())
                pred_id = data.get("id", "")
                print(f"   预测ID: {pred_id}")
                return data
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")
            print(f"   ✗ HTTP {e.code}: {body[:200]}")
            return None

    def _poll_prediction(self, prediction: dict,
                         max_wait: int = 300,
                         interval: int = 5) -> dict | None:
        """轮询预测状态直到完成"""
        urls = prediction.get("urls", {})
        get_url = urls.get("get") or (
            f"{self.BASE_URL}/predictions/{prediction.get('id', '')}"
        )

        start = time.time()
        dots = 0
        while time.time() - start < max_wait:
            req = urllib.request.Request(get_url)
            req.add_header("Authorization", f"Bearer {self.token}")

            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = json.loads(resp.read().decode())

                status = data.get("status", "unknown")
                dots = (dots + 1) % 4
                spinner = ["⠋", "⠙", "⠹", "⠸"][dots]
                elapsed = int(time.time() - start)
                print(f"\r  {spinner} 状态: {status} | 耗时: {elapsed}s",
                      end="", flush=True)

                if status == "succeeded":
                    print("\n  ✓ 生成完成！")
                    return data.get("output")

                if status in ("failed", "canceled"):
                    error = data.get("error", "未知错误")
                    print(f"\n  ✗ 任务失败: {error}")
                    return None

                if status == "processing":
                    logs = data.get("logs", "")
                    if logs:
                        log_line = logs.split("\n")[-1][:60]
                        print(f" [{log_line}]", end="")

                time.sleep(interval)

            except urllib.error.HTTPError as e:
                print(f"\n  ✗ HTTP {e.code}")
                return None

        print(f"\n  ✗ 超时 ({max_wait}s)")
        return None

    def _extract_model_url(self, output) -> str | None:
        """从 Replicate 输出中提取 3D 模型 URL"""
        if isinstance(output, str) and output.startswith("http"):
            return output
        if isinstance(output, list):
            for item in output:
                if isinstance(item, str) and any(
                    item.endswith(ext) for ext in (".glb", ".obj", ".fbx")
                ):
                    return item
        if isinstance(output, dict):
            for key in ("model", "mesh", "glb", "output"):
                val = output.get(key)
                if isinstance(val, str) and val.startswith("http"):
                    return val
        return None

    def _download(self, url: str, output_dir: str,
                  model: str) -> str | None:
        """下载 3D 模型文件"""
        os.makedirs(output_dir, exist_ok=True)

        ext = "glb"
        for e in (".glb", ".obj", ".fbx"):
            if e in url.lower():
                ext = e.lstrip(".")
                break

        timestamp = int(time.time())
        filename = f"nezha_replicate_{model}_{timestamp}.{ext}"
        filepath = os.path.join(output_dir, filename)

        print(f"  ⬇ 下载 {ext.upper()}...")
        try:
            urllib.request.urlretrieve(url, filepath)
            size_mb = os.path.getsize(filepath) / (1024 * 1024)
            print(f"  ✓ {filepath} ({size_mb:.1f}MB)")
            return filepath
        except Exception as e:
            print(f"  ✗ 下载失败: {e}")
            return None


# ─── CLI ───

def main() -> None:
    parser = argparse.ArgumentParser(
        description="🔷 Replicate 开源 3D 模型推理",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  export REPLICATE_API_TOKEN="r8_..."
  python3 replicate_3d.py --image nezha_front.png --model instantmesh
  python3 replicate_3d.py --image nezha_front.png --model triposr
        """
    )
    parser.add_argument("--image", "-i", required=True, help="输入图片")
    parser.add_argument("--model", "-m", default="instantmesh",
                        choices=list(MODELS.keys()),
                        help="模型选择")
    parser.add_argument("--output", "-o", default="./replicate_output",
                        help="输出目录")
    parser.add_argument("--token", help="Replicate Token（或设环境变量）")

    args = parser.parse_args()

    gen = Replicate3D(api_token=args.token)
    result = gen.image_to_3d(args.image, args.model, args.output)

    if result:
        print(f"\n🎉 3D 模型已生成: {result}")
        print(f"\n📋 后续步骤:")
        print(f"   python3 tools/import_to_unity.py {result}")
        print(f"   上传 Mixamo 绑骨骼 → Unity")
    else:
        print("\n❌ 生成失败")
        sys.exit(1)


if __name__ == "__main__":
    main()
