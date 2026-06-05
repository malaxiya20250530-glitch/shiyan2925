#!/usr/bin/env python3
"""
通过 Gradio Space API 调用 InstantMesh 生成 3D 模型
直连 tencentarc-instantmesh.hf.space，Gradio 5.x SSE v3 协议
两阶段：POST /call/<api> → event_id → GET /queue/data?session_hash=<id>
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

SPACE_URL = "https://tencentarc-instantmesh.hf.space"
API_PREFIX = "/gradio_api"


def _gradaio_call(api_name: str, data: list, timeout: int = 300) -> dict | None:
    """两阶段 Gradio 5.x API 调用
    
    阶段1: POST /call/<api_name> → 获取 event_id
    阶段2: GET /queue/data?session_hash=<id> → 等待 process_completed
    """
    # ─── 阶段1: 提交任务 ───
    call_url = f"{SPACE_URL}{API_PREFIX}/call/{api_name}"
    body = json.dumps({"data": data}).encode("utf-8")
    
    req = urllib.request.Request(
        call_url, data=body,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body_text = e.read().decode(errors="replace")
        print(f"   ✗ HTTP {e.code}: {body_text[:200]}")
        return None
    except Exception as e:
        print(f"   ✗ 提交失败: {e}")
        return None
    
    event_id = result.get("event_id", "")
    if not event_id:
        print(f"   ✗ 未获取 event_id: {result}")
        return None
    
    print(f"   ⏳ {api_name} (event: {event_id[:12]}...)")
    
    # ─── 阶段2: 轮询结果 ───
    queue_url = f"{SPACE_URL}{API_PREFIX}/queue/data?session_hash={event_id}"
    start = time.time()
    last_msg = ""
    
    while time.time() - start < timeout:
        try:
            req = urllib.request.Request(queue_url, method="GET")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                for line_bytes in resp:
                    line = line_bytes.decode("utf-8").strip()
                    if not line or not line.startswith("data:"):
                        continue
                    
                    data_str = line[len("data:"):].strip()
                    try:
                        msg = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue
                    
                    msg_type = msg.get("msg", "")
                    if msg_type == "process_completed":
                        if msg.get("success"):
                            return msg.get("output", {})
                        else:
                            print(f"   ✗ 任务失败: {msg}")
                            return None
                    elif msg_type == "process_starts":
                        if last_msg != "starts":
                            last_msg = "starts"
                            # 进度点
                    elif msg_type == "estimation":
                        eta = msg.get("rank_eta", 0)
                        if last_msg != "est" and eta > 0:
                            last_msg = "est"
                            print(f"      排队中 (预估 {eta:.0f}s)...")
                        
        except urllib.error.HTTPError as e:
            if e.code == 404:
                time.sleep(2)
                continue
            print(f"   ✗ 轮询 HTTP {e.code}")
            return None
        except Exception:
            time.sleep(3)
    
    print(f"   ✗ 超时 ({timeout}s)")
    return None


def image_to_3d(image_path: str, seed: int = 42, steps: int = 50,
                output_dir: str = "./gradio_output") -> str | None:
    """通过 InstantMesh Gradio Space 将图片转为 3D 模型
    
    管线: check_input_image → preprocess → generate_mvs → make3d
    返回: 下载的 GLB 文件路径
    """
    if not os.path.exists(image_path):
        sys.exit(f"❌ 图片不存在: {image_path}")
    
    with open(image_path, "rb") as f:
        img_bytes = f.read()
    img_b64 = base64.b64encode(img_bytes).decode("ascii")
    mime = "image/png" if image_path.lower().endswith(".png") else "image/jpeg"
    img_url = f"data:{mime};base64,{img_b64}"
    
    print(f"🔷 InstantMesh Gradio Space 3D 生成")
    print(f"   图片: {image_path} ({len(img_bytes)/1024:.0f}KB)")
    print(f"   种子: {seed}  步数: {steps}")
    print()
    
    img_payload = {
        "path": None, "url": img_url,
        "size": len(img_bytes), "orig_name": os.path.basename(image_path),
        "mime_type": mime, "is_stream": False,
        "meta": {"_type": "gradio.FileData"}
    }
    
    # Step 1: 校验图片
    result = _gradaio_call("check_input_image", [img_payload])
    if result is None:
        return None
    print(f"   ✓ 图片校验通过")
    
    # Step 2: 预处理
    result = _gradaio_call("preprocess", [img_payload, seed])
    if result is None:
        return None
    preprocessed = result.get("data")
    if not preprocessed:
        print(f"   ✗ 预处理返回空数据")
        return None
    print(f"   ✓ 预处理完成")
    
    # Step 3: 多视角生成
    result = _gradaio_call("generate_mvs", [preprocessed, steps, seed])
    if result is None:
        return None
    mvs_output = result.get("data")
    if not mvs_output:
        print(f"   ✗ 多视角生成返回空数据")
        return None
    # generate_mvs 输出: [mvs_result, intermediate_preview]
    mvs_data = mvs_output[0] if isinstance(mvs_output, list) and len(mvs_output) > 0 else mvs_output
    print(f"   ✓ 多视角生成完成")
    
    # Step 4: 3D 重建
    result = _gradaio_call("make3d", [mvs_data])
    if result is None:
        return None
    outputs = result.get("data", [])
    print(f"   ✓ 3D 重建完成")
    
    # 下载输出: [0]=OBJ路径, [1]=GLB路径
    os.makedirs(output_dir, exist_ok=True)
    
    downloaded = None
    for i, label in enumerate(["obj", "glb"]):
        if i >= len(outputs) or not outputs[i]:
            continue
        
        file_info = outputs[i]
        file_url = file_info.get("url", "") if isinstance(file_info, dict) else str(file_info)
        if not file_url:
            print(f"   ⚠ {label} 输出 URL 为空")
            continue
        
        timestamp = int(time.time())
        filename = f"nezha_instantmesh_{label}_{timestamp}.{label}"
        filepath = os.path.join(output_dir, filename)
        
        if file_url.startswith("http"):
            try:
                with urllib.request.urlopen(file_url, timeout=120) as resp:
                    fdata = resp.read()
                with open(filepath, "wb") as out:
                    out.write(fdata)
                size_mb = len(fdata) / (1024 * 1024)
                print(f"   ✓ {filepath} ({size_mb:.1f}MB)")
                if label == "glb":
                    downloaded = filepath
            except Exception as e:
                print(f"   ✗ {label} 下载失败: {e}")
        elif file_url.startswith("data:"):
            _, b64_part = file_url.split(",", 1)
            fdata = base64.b64decode(b64_part)
            with open(filepath, "wb") as out:
                out.write(fdata)
            size_mb = len(fdata) / (1024 * 1024)
            print(f"   ✓ {filepath} ({size_mb:.1f}MB)")
            if label == "glb":
                downloaded = filepath
    
    return downloaded


def main() -> None:
    parser = argparse.ArgumentParser(
        description="🔷 InstantMesh Gradio Space 3D 生成",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python3 gradio_3d.py --image nezha_ref.png
  python3 gradio_3d.py --image nezha_ref.png --seed 123 --steps 75
        """
    )
    parser.add_argument("--image", "-i", required=True, help="输入图片路径")
    parser.add_argument("--seed", "-s", type=int, default=42, help="随机种子 (默认: 42)")
    parser.add_argument("--steps", type=int, default=50, help="多视角步数 (默认: 50)")
    parser.add_argument("--output", "-o", default="./gradio_output", help="输出目录")
    
    args = parser.parse_args()
    
    result = image_to_3d(
        args.image, seed=args.seed, steps=args.steps,
        output_dir=args.output
    )
    
    if result:
        print(f"\n🎉 3D 模型已生成: {result}")
        print(f"\n📋 后续步骤:")
        print(f"   1. 分析模型: python3 tools/import_to_unity.py {result}")
        print(f"   2. 免费绑骨骼: 上传到 https://mixamo.com → 下载 fbx")
        print(f"   3. 导入 Unity → 挂载 PetCore.cs")
    else:
        print("\n❌ 生成失败")
        print("   提示: 尝试更换 seed 值 / 确保图片为正面视图")
        sys.exit(1)


if __name__ == "__main__":
    main()
