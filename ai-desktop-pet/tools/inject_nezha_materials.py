#!/usr/bin/env python3
"""
哪吒专用 PBR 材质注入器
根据 docs/NEZHA_DESIGN_SPEC.md 七色方案，向 GLB 注入材质定义。
"""

import json, struct, sys, copy, os
from pathlib import Path


# 哪吒七色方案
COLORS = {
    "Nezha_Skin":       {"base": [0.96, 0.90, 0.83, 1.0], "rough": 0.6, "metal": 0.0},   # 肤色暖白
    "Nezha_Vest":       {"base": [0.80, 0.13, 0.13, 1.0], "rough": 0.7, "metal": 0.0},   # 哪吒红
    "Nezha_Hair":       {"base": [0.10, 0.10, 0.18, 1.0], "rough": 0.5, "metal": 0.1},   # 水墨黑
    "Nezha_Pants":      {"base": [0.29, 0.29, 0.35, 1.0], "rough": 0.8, "metal": 0.0},   # 水墨灰
    "Nezha_Accessory":  {"base": [0.85, 0.65, 0.13, 1.0], "rough": 0.3, "metal": 0.9},   # 乾坤金
    "Nezha_Sash":       {"base": [0.80, 0.13, 0.13, 1.0], "rough": 0.4, "metal": 0.0},   # 混天绫红
    "Nezha_FireWheel":  {"base": [0.00, 0.80, 1.00, 0.8], "rough": 0.1, "metal": 0.2},   # 风火轮青焰
}

# 额外：眼部 shader 参数（PBR 无法完全表达，留作 Unity Shader 参考）
EYE_PARAMS = {
    "Nezha_Eye": {"base": [0.05, 0.03, 0.02, 1.0], "rough": 0.1, "metal": 0.0,
                  "emissive": [0.3, 0.15, 0.0], "_FiredUpColor": [1.0, 0.3, 0.0]},
}


def read_glb(path: str) -> tuple:
    with open(path, "rb") as f:
        magic = f.read(4)
        assert magic == b"glTF", "无效 GLB"
        ver, total = struct.unpack("<II", f.read(8))
        chunks = {}
        while True:
            hdr = f.read(8)
            if len(hdr) < 8:
                break
            clen, ctype = struct.unpack("<II", hdr)
            chunks[ctype] = f.read(clen)
    gltf = json.loads(chunks[0x4E4F534A])
    bin_data = chunks.get(0x004E4942, b"")
    return gltf, bin_data


def inject_materials(gltf: dict) -> dict:
    """注入哪吒材质到 glTF"""
    gltf = copy.deepcopy(gltf)

    existing = {m.get("name", ""): i for i, m in enumerate(gltf.get("materials", []))}
    mat_idx_map = {}

    # 添加材质定义
    if "materials" not in gltf:
        gltf["materials"] = []

    for mat_name, props in {**COLORS, **EYE_PARAMS}.items():
        if mat_name in existing:
            mat_idx_map[mat_name] = existing[mat_name]
            continue

        material = {
            "name": mat_name,
            "pbrMetallicRoughness": {
                "baseColorFactor": props["base"],
                "metallicFactor": props["metal"],
                "roughnessFactor": props["rough"],
            },
        }

        # 自发光（眼睛 fired_up 状态）
        if "emissive" in props:
            material["emissiveFactor"] = props["emissive"]

        # 存储自定义参数到 extras（Unity 导入后可读）
        if any(k.startswith("_") for k in props):
            material["extras"] = {k: v for k, v in props.items() if k.startswith("_")}

        # 双面渲染（混天绫、头发需要）
        if mat_name in ("Nezha_Sash", "Nezha_Hair"):
            material["doubleSided"] = True

        # 透明（风火轮青焰）
        if mat_name == "Nezha_FireWheel":
            material["alphaMode"] = "BLEND"

        mat_idx = len(gltf["materials"])
        gltf["materials"].append(material)
        mat_idx_map[mat_name] = mat_idx
        print(f"  ✓ {mat_name}: rgba({props['base'][0]:.2f},{props['base'][1]:.2f},{props['base'][2]:.2f})")

    # 关联到网格的 primitive
    mat_names = list(mat_idx_map.keys())
    for mesh in gltf.get("meshes", []):
        for pi, prim in enumerate(mesh.get("primitives", [])):
            # 根据 primitive 索引分配材质
            mat_name = mat_names[pi % len(mat_names)] if mat_names else "Nezha_Skin"
            prim["material"] = mat_idx_map[mat_name]

    return gltf


def write_glb(gltf: dict, bin_data: bytes, output: str) -> int:
    json_str = json.dumps(gltf, separators=(",", ":"))
    json_bytes = json_str.encode()
    while len(json_bytes) % 4:
        json_bytes += b" "
    while len(bin_data) % 4:
        bin_data += b"\x00"

    total = 12 + 8 + len(json_bytes) + 8 + len(bin_data)
    with open(output, "wb") as f:
        f.write(b"glTF")
        f.write(struct.pack("<II", 2, total))
        f.write(struct.pack("<II", len(json_bytes), 0x4E4F534A))
        f.write(json_bytes)
        if bin_data:
            f.write(struct.pack("<II", len(bin_data), 0x004E4942))
            f.write(bin_data)
    return total


def stats(gltf: dict) -> dict:
    ms = gltf.get("materials", [])
    return {
        "网格": len(gltf.get("meshes", [])),
        "材质": len(ms),
        "材质列表": [m.get("name", "?") for m in ms],
        "节点": len(gltf.get("nodes", [])),
        "骨骼": sum(1 for n in gltf.get("nodes", []) if "skin" not in n and "mesh" not in n),
    }


if __name__ == "__main__":
    inp = sys.argv[1] if len(sys.argv) > 1 else "./nezha_rigged.glb"
    out = sys.argv[2] if len(sys.argv) > 2 else inp.replace(".glb", "_textured.glb")

    print("🎨 哪吒 PBR 材质注入器")
    print(f"   输入: {inp}")
    print()

    gltf, bin_data = read_glb(inp)
    s_before = stats(gltf)
    print(f"   注入前: {s_before['材质']} 材质")

    gltf = inject_materials(gltf)
    total = write_glb(gltf, bin_data, out)

    s_after = stats(gltf)
    print(f"   注入后: {s_after['材质']} 材质")
    for m in s_after["材质列表"]:
        print(f"     - {m}")
    print(f"   文件大小: {total/1024:.0f}KB")
    print(f"\n✅ 已保存: {out}")
