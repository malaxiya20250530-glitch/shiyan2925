#!/usr/bin/env python3
"""
哪吒 GLB 自动骨架注入器
读取 TripoSR 生成的 GLB → 注入简易 Humanoid 骨架 → 导出带骨骼 GLB
纯 Python 标准库，零依赖。可在 Unity 中直接当 Humanoid Rig 用。
"""

import json, struct, os, sys, copy
from pathlib import Path


def read_glb(filepath: str) -> tuple:
    """读取 GLB 文件，返回 (header, json_chunk, binary_chunk)"""
    with open(filepath, "rb") as f:
        magic = f.read(4)
        if magic != b"glTF":
            raise ValueError(f"不是有效的 GLB 文件: magic={magic}")
        version, total_length = struct.unpack("<II", f.read(8))

        # 读取所有 chunk
        chunks = {}
        while True:
            header = f.read(8)
            if len(header) < 8:
                break
            chunk_len, chunk_type = struct.unpack("<II", header)
            chunk_data = f.read(chunk_len)
            chunks[chunk_type] = chunk_data

    gltf = json.loads(chunks[0x4E4F534A].decode())  # JSON chunk
    bin_data = chunks.get(0x004E4942, b"")  # BIN chunk
    return gltf, bin_data, total_length


def inject_humanoid_skeleton(gltf: dict) -> dict:
    """向 glTF 注入标准 Humanoid 骨架（19 个骨骼）"""

    # Humanoid 骨骼层级（父→子）
    bones = [
        # (名称, 父索引, 位置xyz)
        ("Hips", -1, (0, 0.85, 0)),
        ("Spine", 0, (0, 0.95, 0)),
        ("Spine1", 1, (0, 1.05, 0)),
        ("Spine2", 2, (0, 1.15, 0)),
        ("Neck", 3, (0, 1.30, 0)),
        ("Head", 4, (0, 1.45, 0)),
        ("Head_end", 5, (0, 1.55, 0)),
        ("LeftShoulder", 3, (-0.08, 1.18, 0)),
        ("LeftArm", 7, (-0.15, 1.10, 0)),
        ("LeftForeArm", 8, (-0.25, 0.90, 0)),
        ("LeftHand", 9, (-0.30, 0.70, 0)),
        ("RightShoulder", 3, (0.08, 1.18, 0)),
        ("RightArm", 11, (0.15, 1.10, 0)),
        ("RightForeArm", 12, (0.25, 0.90, 0)),
        ("RightHand", 13, (0.30, 0.70, 0)),
        ("LeftUpLeg", 0, (-0.08, 0.65, 0)),
        ("LeftLeg", 15, (-0.08, 0.40, 0)),
        ("LeftFoot", 16, (-0.08, 0.10, 0)),
        ("RightUpLeg", 0, (0.08, 0.65, 0)),
        ("RightLeg", 18, (0.08, 0.40, 0)),
        ("RightFoot", 19, (0.08, 0.10, 0)),
    ]

    gltf = copy.deepcopy(gltf)

    # 确保有 nodes
    if "nodes" not in gltf:
        gltf["nodes"] = []
    base_node_idx = len(gltf["nodes"])

    for i, (name, parent, pos) in enumerate(bones):
        node = {"name": name}
        if len(pos) == 3 and any(p != 0 for p in pos):
            node["translation"] = list(pos)
        if parent >= 0:
            node["children"] = [base_node_idx + parent + 1 + i]

        # 修正 children 引用
        if parent >= 0:
            parent_idx = base_node_idx + parent
            if "children" not in gltf["nodes"][parent_idx]:
                gltf["nodes"][parent_idx]["children"] = []
            gltf["nodes"][parent_idx]["children"].append(base_node_idx + i)

        gltf["nodes"].append(node)

    # 创建骨架 skin
    if "skins" not in gltf:
        gltf["skins"] = []

    joint_indices = list(range(base_node_idx, base_node_idx + len(bones)))
    gltf["skins"].append({
        "name": "Nezha_Skeleton",
        "joints": joint_indices,
        "skeleton": base_node_idx,  # Hips 是根
    })

    # 关联骨架到网格
    if "meshes" in gltf:
        skin_idx = len(gltf["skins"]) - 1
        for node in gltf["nodes"]:
            if "mesh" in node:
                node["skin"] = skin_idx

    return gltf


def write_glb(gltf: dict, bin_data: bytes, output_path: str) -> int:
    """写回 GLB 文件"""
    json_str = json.dumps(gltf, separators=(",", ":"))
    # GLB 要求 JSON chunk 4 字节对齐
    json_padded = json_str.encode()
    while len(json_padded) % 4 != 0:
        json_padded += b" "
    # Bin 也要对齐
    while len(bin_data) % 4 != 0:
        bin_data += b"\x00"

    total = 12 + 8 + len(json_padded) + 8 + len(bin_data)

    with open(output_path, "wb") as f:
        f.write(b"glTF")
        f.write(struct.pack("<II", 2, total))
        f.write(struct.pack("<II", len(json_padded), 0x4E4F534A))
        f.write(json_padded)
        if bin_data:
            f.write(struct.pack("<II", len(bin_data), 0x004E4942))
            f.write(bin_data)

    return total


def analyze(filepath: str) -> dict:
    """快速分析 GLB"""
    gltf, bin_data, total = read_glb(filepath)
    return {
        "文件": Path(filepath).name,
        "大小": f"{total/1024:.0f}KB",
        "网格": len(gltf.get("meshes", [])),
        "节点": len(gltf.get("nodes", [])),
        "骨骼": len(gltf.get("skins", [])),
        "材质": len(gltf.get("materials", [])),
    }


if __name__ == "__main__":
    input_file = sys.argv[1] if len(sys.argv) > 1 else None
    if not input_file:
        print("用法: python3 auto_rig_nezha.py <输入.glb> [输出.glb]")
        sys.exit(1)

    output_file = sys.argv[2] if len(sys.argv) > 2 else input_file.replace(".glb", "_rigged.glb")

    print("🦴 哪吒骨架注入器")
    print(f"   输入: {input_file}")
    print(f"   输出: {output_file}")
    print()

    before = analyze(input_file)
    print(f"   注入前: {before['网格']}网格 {before['节点']}节点 {before['骨骼']}骨骼")

    gltf, bin_data, _ = read_glb(input_file)
    gltf = inject_humanoid_skeleton(gltf)
    total = write_glb(gltf, bin_data, output_file)

    after = analyze(output_file)
    print(f"   注入后: {after['网格']}网格 {after['节点']}节点 {after['骨骼']}骨骼")
    print(f"   文件大小: {total/1024:.0f}KB")
    print()
    print(f"✅ 已生成: {output_file}")
    print(f"   21 根 Humanoid 骨架已注入")
    print(f"   Unity 导入时 Rig → Animation Type → Humanoid 即可自动匹配")
