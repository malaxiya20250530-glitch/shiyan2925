#!/usr/bin/env python3
"""
Meshy.ai API 3D 模型生成器
支持文生3D (Text-to-3D) 和 图生3D (Image-to-3D)
文档: https://docs.meshy.ai/api
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error
import argparse
from pathlib import Path


class MeshyGenerator:
    """Meshy.ai 3D 模型生成客户端"""

    BASE_URL = "https://api.meshy.ai"

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.environ.get("MESHY_API_KEY", "")
        if not self.api_key:
            sys.exit("❌ 请设置 MESHY_API_KEY 环境变量，或通过 --api-key 参数传入\n"
                     "   免费注册获取: https://meshy.ai")

    # ─── 文生3D ───

    def text_to_3d(self, prompt: str, negative_prompt: str = "",
                   art_style: str = "realistic",
                   output_dir: str = "./meshy_output") -> str | None:
        """文字描述生成 3D 模型

        参数:
            prompt: 描述文本（支持中英文）
            negative_prompt: 负面描述（不要什么）
            art_style: 风格 (realistic / cartoon / low-poly / voxel)
            output_dir: 输出目录
        返回:
            下载的模型文件路径，或 None
        """
        print(f"🔥 Meshy 文生3D 已启动")
        print(f"   描述: {prompt}")

        task_id = self._create_text_task(prompt, negative_prompt, art_style)
        if not task_id:
            return None

        model_urls = self._poll_until_done(task_id, "text-to-3d")
        if not model_urls:
            return None

        return self._download_models(model_urls, output_dir, task_id)

    # ─── 图生3D ───

    def image_to_3d(self, image_path: str,
                    output_dir: str = "./meshy_output") -> str | None:
        """参考图片生成 3D 模型

        参数:
            image_path: 参考图片路径 (jpg/png, 建议正面视图)
            output_dir: 输出目录
        返回:
            下载的模型文件路径，或 None
        """
        if not os.path.exists(image_path):
            sys.exit(f"❌ 图片文件不存在: {image_path}")

        print(f"🖼️  Meshy 图生3D 已启动")
        print(f"   参考图: {image_path}")

        task_id = self._create_image_task(image_path)
        if not task_id:
            return None

        model_urls = self._poll_until_done(task_id, "image-to-3d")
        if not model_urls:
            return None

        return self._download_models(model_urls, output_dir, task_id)

    # ─── 内部方法 ───

    def _create_text_task(self, prompt: str, negative: str, art_style: str) -> str | None:
        """创建文生3D任务，返回 task_id"""
        body = {
            "mode": "preview",
            "prompt": prompt,
            "art_style": art_style,
            "should_remesh": True,
            "topology": "quad",
            "target_polycount": 30000,
        }
        if negative:
            body["negative_prompt"] = negative

        return self._post("/v2/text-to-3d", body)

    def _create_image_task(self, image_path: str) -> str | None:
        """创建图生3D任务，返回 task_id"""
        import base64
        with open(image_path, "rb") as f:
            image_b64 = base64.b64encode(f.read()).decode()

        body = {
            "mode": "preview",
            "image_url": f"data:image/png;base64,{image_b64}",
            "should_remesh": True,
            "topology": "quad",
            "target_polycount": 30000,
        }
        return self._post("/v2/image-to-3d", body)

    def _poll_until_done(self, task_id: str, task_type: str,
                         max_wait: int = 600, interval: int = 10) -> list[str] | None:
        """轮询任务状态直到完成"""
        url = f"{self.BASE_URL}/v2/{task_type}/{task_id}"
        start = time.time()
        dots = 0

        while time.time() - start < max_wait:
            try:
                req = urllib.request.Request(url)
                req.add_header("Authorization", f"Bearer {self.api_key}")
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = json.loads(resp.read().decode())

                status = data.get("status", "UNKNOWN")

                dots = (dots + 1) % 4
                spinner = ["⠋", "⠙", "⠹", "⠸"][dots]
                elapsed = int(time.time() - start)
                progress = data.get("progress", 0)
                print(f"\r  {spinner} 状态: {status} | 进度: {progress}% | 耗时: {elapsed}s", end="", flush=True)

                if status == "SUCCEEDED":
                    print("\n  ✓ 生成完成！")
                    model_urls = data.get("model_urls", {})
                    urls = []
                    for key in ["glb", "fbx", "obj", "usdz"]:
                        if key in model_urls:
                            urls.append(model_urls[key])
                    return urls if urls else None

                if status in ("FAILED", "EXPIRED"):
                    error = data.get("error", {}).get("message", "未知错误")
                    print(f"\n  ✗ 任务失败: {error}")
                    return None

                time.sleep(interval)

            except urllib.error.HTTPError as e:
                print(f"\n  ✗ API 错误: {e.code}")
                return None
            except Exception as e:
                print(f"\n  ✗ 请求异常: {e}")
                time.sleep(interval)

        print(f"\n  ✗ 超时 ({max_wait}s)")
        return None

    def _post(self, path: str, body: dict) -> str | None:
        """POST 请求，返回 result 字段"""
        url = f"{self.BASE_URL}{path}"
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("Authorization", f"Bearer {self.api_key}")

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read().decode())
                task_id = result.get("result")
                if not task_id:
                    print(f"  ✗ API 响应异常: {result}")
                    return None
                print(f"  任务ID: {task_id}")
                return task_id
        except urllib.error.HTTPError as e:
            body_text = e.read().decode(errors="replace")
            print(f"  ✗ HTTP {e.code}: {body_text[:200]}")
            return None

    def _download_models(self, urls: list[str], output_dir: str,
                         task_id: str) -> str | None:
        """下载所有格式的模型文件"""
        os.makedirs(output_dir, exist_ok=True)
        downloaded = []

        for url in urls:
            ext = url.split(".")[-1].split("?")[0]
            if ext not in ("glb", "fbx", "obj", "usdz"):
                ext = "glb"
            filename = f"nezha_{task_id[:8]}.{ext}"
            filepath = os.path.join(output_dir, filename)

            print(f"  ⬇ 下载 {ext.upper()}...")
            try:
                urllib.request.urlretrieve(url, filepath)
                size_mb = os.path.getsize(filepath) / (1024 * 1024)
                print(f"  ✓ {filepath} ({size_mb:.1f}MB)")
                downloaded.append(filepath)
            except Exception as e:
                print(f"  ✗ 下载失败 ({ext}): {e}")

        return downloaded[0] if downloaded else None


# ─── CLI 入口 ───

def main() -> None:
    parser = argparse.ArgumentParser(
        description="🔥 Meshy.ai 3D 模型生成器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 文生3D
  python3 meshy_generate.py --prompt "哪吒，三头身Q版，国风卡渲，双髻，红色马甲，混天绫飘飞，风火轮，火尖枪"

  # 图生3D（需先有设定图）
  python3 meshy_generate.py --image nezha_ref.png

  # 指定风格
  python3 meshy_generate.py --prompt "...哪吒..." --style cartoon --output ./nezha_3d
        """
    )
    parser.add_argument("--prompt", "-p", help="文字描述（中英文均可）")
    parser.add_argument("--image", "-i", help="参考图片路径")
    parser.add_argument("--negative", help="负面描述（不想要什么）")
    parser.add_argument("--style", default="cartoon",
                        choices=["realistic", "cartoon", "low-poly", "voxel"],
                        help="美术风格 (默认: cartoon)")
    parser.add_argument("--output", "-o", default="./meshy_output",
                        help="输出目录 (默认: ./meshy_output)")
    parser.add_argument("--api-key", help="Meshy API Key（或设环境变量 MESHY_API_KEY）")

    args = parser.parse_args()

    if not args.prompt and not args.image:
        parser.error("至少需要 --prompt 或 --image 参数")

    gen = MeshyGenerator(api_key=args.api_key)

    if args.image:
        result = gen.image_to_3d(args.image, args.output)
    else:
        result = gen.text_to_3d(args.prompt, args.negative or "", args.style, args.output)

    if result:
        print(f"\n🎉 3D 模型已生成: {result}")
        print("   导入 Unity: 将 .glb 或 .fbx 拖入 Assets 目录")
    else:
        print("\n❌ 生成失败")
        print("   提示: 检查 API Key 是否正确，或免费额度是否用完")
        print("   注册: https://meshy.ai")
        sys.exit(1)


if __name__ == "__main__":
    main()
