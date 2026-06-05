#!/usr/bin/env python3
"""
TripoSR HuggingFace Space 生成器（Gradio 4.x API）
图片 → GLB 3D 模型，带进度条和超时重试
"""

import json, urllib.request, base64, time, sys, os
from pathlib import Path

SPACE_URL = "https://stabilityai-triposr.hf.space"
JOIN_URL = f"{SPACE_URL}/queue/join"


def wake_space(timeout: int = 30) -> bool:
    """唤醒休眠的 HF Space"""
    for i in range(timeout):
        try:
            req = urllib.request.Request(SPACE_URL + "/")
            with urllib.request.urlopen(req, timeout=10) as r:
                if r.status == 200:
                    print(f"  ✓ Space 已就绪")
                    return True
        except Exception:
            time.sleep(2)
    print("  ✗ Space 唤醒超时")
    return False


def image_to_3d(image_path: str, output_dir: str = "./nezha_3d_output",
                remove_bg: bool = True, fg_ratio: float = 0.85,
                mc_resolution: int = 256, timeout: int = 300) -> str | None:
    """将图片发送到 TripoSR Space 生成 3D 模型"""

    # 读图 + base64
    path = Path(image_path)
    if not path.exists():
        print(f"✗ 图片不存在: {image_path}")
        return None

    with open(path, "rb") as f:
        raw = f.read()
    img_b64 = base64.b64encode(raw).decode()
    print(f"  📷 {path.name} ({len(raw)/1024:.0f}KB) → base64 ({len(img_b64)} chars)")

    # 唤醒 Space
    if not wake_space():
        return None

    # 提交任务
    session = f"nezha_{int(time.time())}"
    payload = {
        "fn_index": 3,
        "session_hash": session,
        "data": [
            {
                "path": None, "url": None,
                "orig_name": path.name,
                "mime_type": "image/png",
                "data": f"data:image/png;base64,{img_b64}",
            },
            remove_bg,
            fg_ratio,
            mc_resolution,
        ],
    }

    print(f"  🚀 提交生成请求...")
    req = urllib.request.Request(
        JOIN_URL,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read())
            event_id = result.get("event_id")
            print(f"  ✓ 已入队: event_id={event_id}")
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        print(f"  ✗ HTTP {e.code}: {body[:300]}")
        return None
    except Exception as e:
        print(f"  ✗ 请求失败: {e}")
        return None

    # 轮询结果
    data_url = f"{SPACE_URL}/queue/data?session_hash={session}"
    start = time.time()

    for i in range(timeout // 3):
        time.sleep(3)
        elapsed = int(time.time() - start)
        try:
            with urllib.request.urlopen(data_url, timeout=15) as resp:
                r = json.loads(resp.read())
                msg = r.get("msg", "")

                if msg == "process_completed":
                    print(f"  ✅ 生成完成! (耗时 {elapsed}s)")
                    return _save_output(r, output_dir)

                elif msg == "process_generating":
                    pct = r.get("output", {}).get("progress", 0)
                    bar = "█" * int(pct * 20) + "░" * (20 - int(pct * 20))
                    print(f"  ⏳ [{bar}] {elapsed}s", end="\r")

                elif msg == "estimation":
                    eta = r.get("estimation", {}).get("rank_eta", "?")
                    print(f"  ⏳ 排队中 ETA:{eta}s ({elapsed}s)", end="\r")

                else:
                    print(f"  ⚠️ 未知状态: {msg} ({elapsed}s)")

        except urllib.error.HTTPError as e:
            if e.code == 404:
                print(f"\n  ✗ 队列丢失 (404)，可能需要重新提交")
                return None
            print(f"\n  ⚠️ HTTP {e.code} ({elapsed}s)")
        except Exception as e:
            if i % 20 == 0:
                print(f"\n  ⚠️ 网络抖动 ({elapsed}s): {e}")

    print(f"\n  ✗ 超时 ({timeout}s)")
    return None


def _save_output(result: dict, output_dir: str) -> str | None:
    """从结果中提取并保存 GLB/OBJ 文件"""
    os.makedirs(output_dir, exist_ok=True)
    data = result.get("output", {}).get("data", [])

    for i, item in enumerate(data):
        if not isinstance(item, dict):
            continue

        # GLB 文件（优先）
        if "data" in item and item.get("mime_type", "").startswith("model/"):
            ext = "glb" if "glb" in item.get("mime_type", "") else "obj"
            fname = item.get("orig_name", f"nezha_3d.{ext}")
            filepath = os.path.join(output_dir, fname)
            raw = base64.b64decode(item["data"].split(",")[-1])
            with open(filepath, "wb") as f:
                f.write(raw)
            print(f"  📦 已保存: {filepath} ({len(raw)/1024:.0f}KB)")
            return filepath

        # URL 方式
        if "url" in item and item["url"]:
            url = item["url"]
            ext = "glb" if "glb" in url else "obj"
            fname = item.get("orig_name", f"nezha_3d.{ext}")
            filepath = os.path.join(output_dir, fname)
            try:
                urllib.request.urlretrieve(url, filepath)
                size = os.path.getsize(filepath)
                print(f"  📦 已下载: {filepath} ({size/1024:.0f}KB)")
                return filepath
            except Exception as e:
                print(f"  ✗ 下载失败: {e}")

    # 兜底：原始字符串
    for i, item in enumerate(data):
        if isinstance(item, str) and len(item) > 1000:
            fname = f"nezha_3d_output_{i}.glb"
            filepath = os.path.join(output_dir, fname)
            try:
                raw = base64.b64decode(item)
                with open(filepath, "wb") as f:
                    f.write(raw)
                print(f"  📦 已保存(string): {filepath} ({len(raw)/1024:.0f}KB)")
                return filepath
            except Exception:
                pass

    print(f"  ⚠️ 未找到可保存的 3D 文件")
    print(f"  debug: data items = {len(data)}")
    for i, item in enumerate(data):
        print(f"    [{i}] type={type(item).__name__}", end="")
        if isinstance(item, dict):
            print(f" keys={list(item.keys())[:5]}")
        elif isinstance(item, str):
            print(f" len={len(item)}")
        else:
            print()
    return None


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="TripoSR HF Space 3D 生成器")
    parser.add_argument("--image", "-i", required=True, help="输入图片")
    parser.add_argument("--output", "-o", default="./nezha_3d_output", help="输出目录")
    parser.add_argument("--no-bg-remove", action="store_true", help="不自动去背景")
    parser.add_argument("--fg-ratio", type=float, default=0.85, help="前景比例 (0.5-1.0)")
    parser.add_argument("--mc-res", type=int, default=256, help="Marching Cubes 分辨率")
    parser.add_argument("--timeout", type=int, default=300, help="超时秒数")

    args = parser.parse_args()
    print("🔺 TripoSR Space 3D 生成器")
    print(f"   图片: {args.image}")
    print()

    result = image_to_3d(
        args.image,
        output_dir=args.output,
        remove_bg=not args.no_bg_remove,
        fg_ratio=args.fg_ratio,
        mc_resolution=args.mc_res,
        timeout=args.timeout,
    )

    if result:
        print(f"\n🎉 成功! 3D 模型: {result}")
        print(f"\n📋 下一步:")
        print(f"   1. 分析: python3 tools/import_to_unity.py {result}")
        print(f"   2. 绑骨: Mixamo 或开源替代方案")
        print(f"   3. 导入 Unity")
    else:
        print(f"\n❌ 生成失败")
        sys.exit(1)
