#!/usr/bin/env python3
"""
3D 模型 Unity 导入准备工具
- 验证模型文件格式
- 检测骨骼/动画
- 生成 Unity 导入配置建议
- 批量处理多个模型
"""

import json
import os
import sys
import struct
import argparse
from pathlib import Path
from datetime import datetime


def analyze_glb(filepath: str) -> dict:
    """分析 GLB 文件结构（GLTF 2.0 Binary）"""
    info = {"format": "glb", "valid": False, "meshes": 0, "animations": 0,
            "bones": 0, "materials": 0, "file_size_mb": 0}

    try:
        size = os.path.getsize(filepath)
        info["file_size_mb"] = round(size / (1024 * 1024), 2)

        with open(filepath, "rb") as f:
            # GLB Header: magic(4) + version(4) + length(4)
            header = f.read(12)
            if len(header) < 12:
                return info

            magic = struct.unpack("<I", header[0:4])[0]
            if magic != 0x46546C67:  # "glTF"
                return info

            version = struct.unpack("<I", header[4:8])[0]
            info["version"] = version
            info["valid"] = True

            # 读取 JSON chunk 获取详细信息
            chunk_len = struct.unpack("<I", f.read(4))[0]
            chunk_type = struct.unpack("<I", f.read(4))[0]

            if chunk_type == 0x4E4F534A:  # "JSON"
                json_data = json.loads(f.read(chunk_len).decode("utf-8"))

                info["meshes"] = len(json_data.get("meshes", []))
                info["materials"] = len(json_data.get("materials", []))

                # 统计骨骼（skin 中的 joints）
                skins = json_data.get("skins", [])
                if skins:
                    all_joints = set()
                    for skin in skins:
                        for joint in skin.get("joints", []):
                            all_joints.add(joint)
                    info["bones"] = len(all_joints)

                # 统计动画
                info["animations"] = len(json_data.get("animations", []))

    except (struct.error, json.JSONDecodeError, IOError) as e:
        info["error"] = str(e)

    return info


def analyze_fbx(filepath: str) -> dict:
    """FBX 基础分析（文本模式）"""
    info = {"format": "fbx", "valid": False, "meshes": 0, "animations": 0,
            "bones": 0, "file_size_mb": 0}

    try:
        size = os.path.getsize(filepath)
        info["file_size_mb"] = round(size / (1024 * 1024), 2)

        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read(10000)  # 只读前 10KB
            if "FBXHeaderExtension" in content:
                info["valid"] = True
            # 粗略统计
            info["meshes"] = content.count('Model: "Model::"') + content.count('Mesh "')
            info["bones"] = content.count('Deformer: "Skin::"')
            # FBX 动画统计（粗略）
            info["animations"] = content.count("AnimationCurveNode")

    except (IOError, UnicodeDecodeError):
        # 二进制 FBX
        info["valid"] = os.path.getsize(filepath) > 100

    return info


def analyze_obj(filepath: str) -> dict:
    """OBJ 文件分析"""
    info = {"format": "obj", "valid": False, "vertices": 0, "faces": 0,
            "file_size_mb": 0}
    try:
        size = os.path.getsize(filepath)
        info["file_size_mb"] = round(size / (1024 * 1024), 2)
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if line.startswith("v "):
                    info["vertices"] += 1
                elif line.startswith("f "):
                    info["faces"] += 1
        info["valid"] = info["vertices"] > 0
    except IOError:
        pass
    return info


def generate_report(filepath: str) -> str:
    """生成 Unity 导入建议报告"""
    ext = os.path.splitext(filepath)[1].lower()

    analyzers = {
        ".glb": analyze_glb,
        ".gltf": analyze_glb,
        ".fbx": analyze_fbx,
        ".obj": analyze_obj,
    }

    analyzer = analyzers.get(ext)
    if not analyzer:
        return f"⚠️ 不支持的格式: {ext}"

    info = analyzer(filepath)

    lines = []
    lines.append("=" * 60)
    lines.append(f"📦 模型分析: {os.path.basename(filepath)}")
    lines.append("=" * 60)
    lines.append(f"  格式: {info['format'].upper()}")
    lines.append(f"  大小: {info.get('file_size_mb', '?')} MB")
    lines.append(f"  有效: {'✓' if info.get('valid') else '✗'}")

    if info["format"] == "glb":
        lines.append(f"  版本: GLTF {info.get('version', '?')}")
        lines.append(f"  网格: {info.get('meshes', '?')} 个")
        lines.append(f"  材质: {info.get('materials', '?')} 个")
        lines.append(f"  骨骼: {info.get('bones', '?')} 根")
        lines.append(f"  动画: {info.get('animations', '?')} 条")
    elif info["format"] == "fbx":
        lines.append(f"  网格(估算): {info.get('meshes', '?')}")
        lines.append(f"  骨骼(估算): {info.get('bones', '?')}")
        lines.append(f"  动画(估算): {info.get('animations', '?')}")
    elif info["format"] == "obj":
        lines.append(f"  顶点: {info.get('vertices', '?')}")
        lines.append(f"  面: {info.get('faces', '?')}")

    lines.append("")
    lines.append("🎮 Unity 导入步骤:")
    lines.append("  1. 将文件拖入 Unity Project 窗口的 Assets/ 目录")
    lines.append("  2. 选中导入的模型，在 Inspector 中配置:")

    if info.get("bones", 0) > 0:
        lines.append("     - Rig → Animation Type: Humanoid")
        lines.append("     - Avatar Definition: Create From This Model")
    else:
        lines.append("     - Rig → Animation Type: None (无骨骼)")
        lines.append("     - 需要在 Unity 中手动配置 Animator Controller")

    if info.get("animations", 0) > 0:
        lines.append(f"     - Animation: 检测到 {info['animations']} 条动画")
        lines.append("     - 可拆分为 Animation Clips 使用")

    lines.append("     - Materials → Extract Materials (提取材质)")
    lines.append("  3. 将模型拖入场景，挂载 PetCore.cs + PetEmotionSystem.cs")
    lines.append("  4. 配置 Animator Controller 的 12 个动画状态")
    lines.append("")
    lines.append(f"📋 详细设计参考: docs/NEZHA_DESIGN_SPEC.md")
    lines.append("=" * 60)

    return "\n".join(lines)


# ─── CLI ───

def main() -> None:
    parser = argparse.ArgumentParser(
        description="📦 3D 模型 Unity 导入分析工具"
    )
    parser.add_argument("files", nargs="+", help="3D 模型文件路径 (.glb/.fbx/.obj)")
    parser.add_argument("--json", action="store_true", help="JSON 格式输出")

    args = parser.parse_args()

    for filepath in args.files:
        if not os.path.exists(filepath):
            print(f"✗ 文件不存在: {filepath}")
            continue

        if args.json:
            ext = os.path.splitext(filepath)[1].lower()
            analyzers = {".glb": analyze_glb, ".fbx": analyze_fbx, ".obj": analyze_obj}
            analyzer = analyzers.get(ext)
            if analyzer:
                print(json.dumps(analyzer(filepath), ensure_ascii=False, indent=2))
        else:
            print(generate_report(filepath))
            print()


if __name__ == "__main__":
    main()
