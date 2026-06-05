#!/usr/bin/env python3
"""TripoSR Gradio Space 3D 生成 — MIT 许可，1秒极速"""
import json, os, sys, time, base64, urllib.request, urllib.error, argparse

SPACE_URL = "https://stabilityai-triposr.hf.space"


def _call(api_name: str, data: list, timeout: int = 180) -> dict | None:
    """两阶段 Gradio API 调用"""
    # 阶段1: 提交
    url = f"{SPACE_URL}/call/{api_name}"
    body = json.dumps({"data": data}).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read().decode())
    event_id = result["event_id"]
    
    # 阶段2: 轮询
    qurl = f"{SPACE_URL}/queue/data?session_hash={event_id}"
    start = time.time()
    while time.time() - start < timeout:
        req = urllib.request.Request(qurl, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            for line in resp:
                line = line.decode().strip()
                if line.startswith("data:"):
                    msg = json.loads(line[5:].strip())
                    if msg.get("msg") == "process_completed":
                        if msg.get("success"):
                            return msg["output"]
                        else:
                            err = msg.get("output", {}).get("error", "未知错误")
                            print(f"   ✗ {api_name} 失败: {err}")
                            return None
        time.sleep(2)
    print(f"   ✗ {api_name} 超时")
    return None


def image_to_3d(image_path: str, remove_bg: bool = True,
                fg_ratio: float = 0.85, output_dir: str = "./triposr_output") -> str | None:
    """图片 → TripoSR → GLB"""
    if not os.path.exists(image_path):
        sys.exit(f"❌ 图片不存在: {image_path}")
    
    with open(image_path, "rb") as f:
        img_bytes = f.read()
    img_b64 = base64.b64encode(img_bytes).decode()
    mime = "image/png" if image_path.lower().endswith(".png") else "image/jpeg"
    
    print(f"🔷 TripoSR 3D 生成 (MIT)")
    print(f"   图片: {image_path} ({len(img_bytes)/1024:.0f}KB)")
    print(f"   去背景: {remove_bg}  前景比: {fg_ratio}")
    print()
    
    img_payload = {
        "path": None, "url": f"data:{mime};base64,{img_b64}",
        "size": len(img_bytes), "orig_name": os.path.basename(image_path),
        "mime_type": mime, "is_stream": False,
        "meta": {"_type": "gradio.FileData"}
    }
    
    # Step 1: preprocess (image, do_remove_background, foreground_ratio)
    print("   ⏳ 预处理...")
    result = _call("preprocess", [img_payload, remove_bg, fg_ratio])
    if result is None:
        return None
    pp_data = result["data"]
    print(f"   ✓ 预处理完成")
    
    # Step 2: generate (preprocessed_data, ?)
    print("   ⏳ 生成 3D...")
    result = _call("generate", [pp_data, None])  # 第2个参数可能是mc_resolution
    if result is None:
        return None
    
    outputs = result.get("data", [])
    os.makedirs(output_dir, exist_ok=True)
    
    downloaded = None
    for i, label in enumerate(["obj", "glb"]):
        if i >= len(outputs) or not outputs[i]:
            continue
        file_info = outputs[i]
        file_url = file_info.get("url", "") if isinstance(file_info, dict) else str(file_info)
        if not file_url or not file_url.startswith("http"):
            continue
        
        timestamp = int(time.time())
        filename = f"nezha_triposr_{label}_{timestamp}.{label}"
        filepath = os.path.join(output_dir, filename)
        
        try:
            with urllib.request.urlopen(file_url, timeout=60) as resp:
                fdata = resp.read()
            with open(filepath, "wb") as out:
                out.write(fdata)
            size_kb = len(fdata) / 1024
            print(f"   ✓ {filepath} ({size_kb:.0f}KB)")
            if label == "glb":
                downloaded = filepath
        except Exception as e:
            print(f"   ✗ {label} 下载失败: {e}")
    
    return downloaded


def main() -> None:
    parser = argparse.ArgumentParser(description="🔷 TripoSR Gradio Space 3D 生成")
    parser.add_argument("--image", "-i", required=True, help="输入图片路径")
    parser.add_argument("--keep-bg", action="store_true", help="保留背景")
    parser.add_argument("--fg-ratio", type=float, default=0.85, help="前景比例 (默认: 0.85)")
    parser.add_argument("--output", "-o", default="./triposr_output", help="输出目录")
    args = parser.parse_args()
    
    result = image_to_3d(
        args.image, remove_bg=not args.keep_bg,
        fg_ratio=args.fg_ratio, output_dir=args.output
    )
    
    if result:
        print(f"\n🎉 3D 模型: {result}")
    else:
        print("\n❌ 生成失败")
        sys.exit(1)


if __name__ == "__main__":
    main()
