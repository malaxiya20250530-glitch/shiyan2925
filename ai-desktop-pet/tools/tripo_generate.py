#!/usr/bin/env python3
"""
Tripo 3D API 模型生成器
支持文生3D 和 图生3D，pro 模型可选骨骼绑定
文档: https://docs.tripo3d.ai
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error
import argparse
from pathlib import Path


class TripoGenerator:
    """Tripo 3D 模型生成客户端"""

    BASE_URL = "https://api.tripo3d.ai"

    # 模型档次
    MODELS = {
        "fast": {"version": "v2.5-20250923", "mode": "fast"},
        "pro":  {"version": "v2.5-20250923", "mode": "pro"},
    }

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.environ.get("TRIPO_API_KEY", "")
        if not self.api_key:
            sys.exit("❌ 请设置 TRIPO_API_KEY 环境变量，或通过 --api-key 参数传入\n"
                     "   注册获取: https://www.tripo3d.ai")

    # ─── 文生3D ───

    def text_to_3d(self, prompt: str, model: str = "fast",
                   texture: bool = True, pbr: bool = False,
                   auto_rig: bool = False,
                   output_dir: str = "./tripo_output") -> str | None:
        """文字描述生成 3D 模型

        参数:
            prompt: 描述文本
            model: 模型质量 (fast / pro)
            texture: 是否生成纹理
            pbr: 是否 PBR 材质
            auto_rig: 是否自动骨骼绑定（仅 pro 模式）
            output_dir: 输出目录
        返回:
            下载的模型文件路径
        """
        if model not in self.MODELS:
            sys.exit(f"❌ 无效模型: {model} (可选: fast, pro)")

        print(f"🔥 Tripo 文生3D [{model.upper()}] 已启动")
        print(f"   描述: {prompt}")
        if auto_rig:
            print(f"   🦴 自动骨骼绑定: 已启用")

        task_id = self._create_task("text_to_model", {
            "prompt": prompt,
            "model_version": self.MODELS[model]["version"],
            "model_seed": None,
            "face_limit": 50000 if model == "pro" else 30000,
            "texture": texture,
            "pbr": pbr,
            "auto_rig": auto_rig and model == "pro",
        })

        if not task_id:
            return None

        model_url = self._poll_until_done(task_id)
        if not model_url:
            return None

        return self._download_model(model_url, output_dir, task_id)

    # ─── 图生3D ───

    def image_to_3d(self, image_path: str, model: str = "fast",
                    texture: bool = True, auto_rig: bool = False,
                    output_dir: str = "./tripo_output") -> str | None:
        """参考图片生成 3D 模型

        参数:
            image_path: 参考图片（正面/多视图）
            model: 模型质量 (fast / pro)
            texture: 是否生成纹理
            auto_rig: 是否自动骨骼绑定（仅 pro 模式）
            output_dir: 输出目录
        """
        if not os.path.exists(image_path):
            sys.exit(f"❌ 图片不存在: {image_path}")

        print(f"🖼️  Tripo 图生3D [{model.upper()}] 已启动")
        print(f"   参考图: {image_path}")

        # 上传图片获取 URL（或用 base64）
        import base64
        with open(image_path, "rb") as f:
            ext = os.path.splitext(image_path)[1].lower()
            mime = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png"}.get(ext.lstrip("."), "png")
            image_b64 = base64.b64encode(f.read()).decode()

        task_id = self._create_task("image_to_model", {
            "file": {
                "type": mime,
                "data": image_b64
            },
            "model_version": self.MODELS[model]["version"],
            "model_seed": None,
            "face_limit": 50000 if model == "pro" else 30000,
            "texture": texture,
            "auto_rig": auto_rig and model == "pro",
        })

        if not task_id:
            return None

        model_url = self._poll_until_done(task_id)
        if not model_url:
            return None

        return self._download_model(model_url, output_dir, task_id)

    # ─── 内部方法 ───

    def _create_task(self, task_type: str, params: dict) -> str | None:
        """创建生成任务，返回 task_id"""
        body = {"type": task_type, **params}
        data = json.dumps(body).encode("utf-8")

        url = f"{self.BASE_URL}/v2/openapi/task"
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("Authorization", f"Bearer {self.api_key}")

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read().decode())
                code = result.get("code")
                if code != 0:
                    print(f"  ✗ API 错误 ({code}): {result.get('message', '未知')}")
                    return None
                task_id = result.get("data", {}).get("task_id")
                print(f"  任务ID: {task_id}")
                return task_id
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")
            print(f"  ✗ HTTP {e.code}: {body[:200]}")
            return None

    def _poll_until_done(self, task_id: str, max_wait: int = 600,
                         interval: int = 10) -> str | None:
        """轮询任务直到完成，返回模型下载 URL"""
        url = f"{self.BASE_URL}/v2/openapi/task/{task_id}"
        start = time.time()
        dots = 0

        while time.time() - start < max_wait:
            try:
                req = urllib.request.Request(url)
                req.add_header("Authorization", f"Bearer {self.api_key}")
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = json.loads(resp.read().decode())

                if data.get("code") != 0:
                    print(f"\n  ✗ 查询失败")
                    return None

                task_data = data.get("data", {})
                status = task_data.get("status", "unknown")
                progress = task_data.get("progress", 0)

                dots = (dots + 1) % 4
                spinner = ["⠋", "⠙", "⠹", "⠸"][dots]
                elapsed = int(time.time() - start)
                print(f"\r  {spinner} 状态: {status} | 进度: {progress}% | 耗时: {elapsed}s",
                      end="", flush=True)

                if status == "success":
                    print("\n  ✓ 生成完成！")
                    output = task_data.get("output", {})
                    # 优先 GLB 格式
                    model_url = output.get("glb") or output.get("model") or output.get("url")
                    return model_url

                if status in ("failed", "error", "cancelled"):
                    error = task_data.get("error", "未知错误")
                    print(f"\n  ✗ 任务失败: {error}")
                    return None

                time.sleep(interval)

            except urllib.error.HTTPError as e:
                print(f"\n  ✗ HTTP {e.code}")
                return None

        print(f"\n  ✗ 超时 ({max_wait}s)")
        return None

    def _download_model(self, url: str, output_dir: str,
                        task_id: str) -> str | None:
        """下载模型文件"""
        os.makedirs(output_dir, exist_ok=True)

        # 判断格式
        ext = "glb"
        if ".fbx" in url:
            ext = "fbx"
        elif ".obj" in url:
            ext = "obj"

        filename = f"nezha_tripo_{task_id[:8]}.{ext}"
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
        description="🦴 Tripo 3D 模型生成器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 文生3D（快速预览）
  python3 tripo_generate.py --prompt "哪吒Q版，三头身，国风卡渲，双髻，混天绫，风火轮" --model fast

  # 文生3D（高质量 + 自动骨骼）
  python3 tripo_generate.py --prompt "哪吒..." --model pro --rig

  # 图生3D
  python3 tripo_generate.py --image nezha_ref.png --model pro --rig
        """
    )
    parser.add_argument("--prompt", "-p", help="文字描述")
    parser.add_argument("--image", "-i", help="参考图片路径")
    parser.add_argument("--model", "-m", default="fast", choices=["fast", "pro"],
                        help="模型质量: fast(快) / pro(高质+可绑骨) (默认: fast)")
    parser.add_argument("--no-texture", action="store_true", help="不生成纹理")
    parser.add_argument("--pbr", action="store_true", help="生成 PBR 材质")
    parser.add_argument("--rig", action="store_true", help="自动骨骼绑定（仅 pro 模式）")
    parser.add_argument("--output", "-o", default="./tripo_output",
                        help="输出目录 (默认: ./tripo_output)")
    parser.add_argument("--api-key", help="Tripo API Key（或设环境变量 TRIPO_API_KEY）")

    args = parser.parse_args()

    if not args.prompt and not args.image:
        parser.error("至少需要 --prompt 或 --image")

    gen = TripoGenerator(api_key=args.api_key)

    if args.image:
        result = gen.image_to_3d(
            args.image, args.model,
            texture=not args.no_texture,
            auto_rig=args.rig,
            output_dir=args.output
        )
    else:
        result = gen.text_to_3d(
            args.prompt, args.model,
            texture=not args.no_texture,
            pbr=args.pbr,
            auto_rig=args.rig,
            output_dir=args.output
        )

    if result:
        print(f"\n🎉 3D 模型已生成: {result}")
        if args.rig:
            print("   🦴 已自动绑定骨骼，导入 Unity 后可直接使用 Humanoid Rig")
        print("   导入 Unity: Assets → Import New Asset → 选择 .glb 文件")
    else:
        print("\n❌ 生成失败")
        print("   提示: 检查 API Key，或免费额度是否用完")
        print("   注册: https://www.tripo3d.ai")
        sys.exit(1)


if __name__ == "__main__":
    main()
