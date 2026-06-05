#!/usr/bin/env python3
"""哪吒终端跳舞 —— ASCII 骨骼动画，Termux 里直接跑"""

import math, time, os, sys


# 21 骨哪吒骨架
FRAMES = [
    # 每个元素: (帧描述, 骨架姿势字符串)
    # 姿势: H=头 O=身 /=\=手臂 | | =腿 * =风火轮 ~ =混天绫
    ("💤 待机晃动",
     r"""
         o
        (O)
      /--+--\
        /_\
       |    |
      *|    |*
    """),
    ("🕺 右摆",
     r"""
          o
         (O)
       /-+--\
         /_\
        |    |
       *|    |*
    """),
    ("🕺 左摆",
     r"""
        o
       (O)
     /--+-\\
        /_\
       |    |
      *|    |*
    """),
    ("🔥 fired_up 战鬪",
     r"""
       \o/
       (O)
     ~/--+--\~
       |/_\|
      *||  ||*
      🔥🔥  🔥🔥
    """),
    ("💃 国风旋转",
     r"""
        o
       (O)~
     ~/--+--\
       /_\
      |    |
     *|    |*
    """),
    ("🎤 街舞锁舞",
     r"""
       _o_
       (O)
      /-+\-\\
       /_\
      |    |
     *|    |*
    """),
]

FRAME_DELAYS = {
    "💤 待机晃动": 0.3,
    "🕺 右摆": 0.25,
    "🕺 左摆": 0.25,
    "🔥 fired_up 战鬪": 0.15,
    "💃 国风旋转": 0.22,
    "🎤 街舞锁舞": 0.18,
}

# ── 骨骼线框动画（更酷） ──

BONE_TREE = {
    "Hips":       {"pos": (0, 0.85),  "parent": None},
    "Spine":      {"pos": (0, 1.05),  "parent": "Hips"},
    "Spine1":     {"pos": (0, 1.25),  "parent": "Spine"},
    "Spine2":     {"pos": (0, 1.45),  "parent": "Spine1"},
    "Neck":       {"pos": (0, 1.65),  "parent": "Spine2"},
    "Head":       {"pos": (0, 1.85),  "parent": "Neck"},
    "LShoulder":  {"pos": (-0.2, 1.5),"parent": "Spine2"},
    "LArm":       {"pos": (-0.4, 1.35),"parent": "LShoulder"},
    "LForeArm":   {"pos": (-0.6, 1.15),"parent": "LArm"},
    "LHand":      {"pos": (-0.7, 0.95),"parent": "LForeArm"},
    "RShoulder":  {"pos": (0.2, 1.5), "parent": "Spine2"},
    "RArm":       {"pos": (0.4, 1.35), "parent": "RShoulder"},
    "RForeArm":   {"pos": (0.6, 1.15), "parent": "RArm"},
    "RHand":      {"pos": (0.7, 0.95), "parent": "RForeArm"},
    "LUpLeg":     {"pos": (-0.12,0.6),"parent": "Hips"},
    "LLeg":       {"pos": (-0.12,0.35),"parent": "LUpLeg"},
    "LFoot":      {"pos": (-0.12,0.08),"parent": "LLeg"},
    "RUpLeg":     {"pos": (0.12, 0.6), "parent": "Hips"},
    "RLeg":       {"pos": (0.12, 0.35), "parent": "RUpLeg"},
    "RFoot":      {"pos": (0.12, 0.08), "parent": "RLeg"},
}


def rotate(p: tuple, angle: float) -> tuple:
    x, y = p
    c, s = math.cos(angle), math.sin(angle)
    return (x * c - y * s, x * s + y * c)


def animate_bones(frame: int, style: str = "idle") -> dict:
    """计算骨骼位置"""
    t = frame * 0.1

    if style == "fired_up":
        energy, speed = 3, 2.5
    elif style == "hiphop":
        energy, speed = 1.5, 1.8
    elif style == "chinese":
        energy, speed = 1, 1
    else:
        energy, speed = 0.5, 0.7

    st = t * speed
    bones = {}

    # 髋部中心
    hip_x = math.sin(st) * 0.1 * energy
    hip_y = 0.85 + abs(math.sin(st * 2)) * 0.02 * energy
    bones["Hips"] = (hip_x, hip_y)

    # 脊柱
    spine_angle = math.sin(st) * 0.1 * energy
    for i, name in enumerate(["Spine", "Spine1", "Spine2", "Neck", "Head"]):
        base = bones[BONE_TREE[name]["parent"]]
        dx, dy = BONE_TREE[name]["pos"]
        dx, dy = rotate((dx, dy), spine_angle * (i + 1) * 0.3)
        bones[name] = (base[0] + dx, base[1] + dy)

    # 肩膀（先算，作为手臂起点）
    for side in ["L", "R"]:
        parent = bones[BONE_TREE[f"{side}Shoulder"]["parent"]]
        dx, dy = BONE_TREE[f"{side}Shoulder"]["pos"]
        bones[f"{side}Shoulder"] = (parent[0] + dx, parent[1] + dy)

    # 手臂
    for side, mult in [("L", -1), ("R", 1)]:
        shoulder_angle = math.sin(st * 1.5) * 0.3 * energy * mult
        if style == "hiphop":
            shoulder_angle = (1 if math.sin(st * 2) > 0 else -1) * 0.6 * energy * mult
        if style == "fired_up":
            shoulder_angle = math.sin(st * 3) * 0.7 * energy * mult

        prev = bones[f"{side}Shoulder"]
        for name in ["Arm", "ForeArm", "Hand"]:
            full = f"{side}{name}"
            dx, dy = BONE_TREE[full]["pos"]
            dx, dy = rotate((dx, dy), shoulder_angle * (0.5 if "Fore" in name or "Hand" in name else 1))
            bones[full] = (prev[0] + dx, prev[1] + dy)
            prev = bones[full]

    # 腿
    for side, mult in [("L", -1), ("R", 1)]:
        leg_angle = math.sin(st + (0 if side == "L" else math.pi)) * 0.2 * energy * mult
        if style == "fired_up":
            leg_angle = math.sin(st * 3 + (0 if side == "L" else math.pi)) * 0.5 * energy * mult

        prev = bones["Hips"]
        for name in ["UpLeg", "Leg", "Foot"]:
            full = f"{side}{name}"
            dx, dy = BONE_TREE[full]["pos"]
            dx, dy = rotate((dx, dy), leg_angle)
            bones[full] = (prev[0] + dx, prev[1] + dy)
            prev = bones[full]

    return bones


def render_skeleton(bones: dict, width: int = 60, height: int = 30) -> str:
    """渲染骨骼到字符画布"""
    # 映射坐标到画布
    scale = 18
    cx, cy = width // 2, height - 3

    canvas = [[" " for _ in range(width)] for _ in range(height)]

    # 画骨骼连接
    connections = [
        ("Hips", "Spine"), ("Spine", "Spine1"), ("Spine1", "Spine2"),
        ("Spine2", "Neck"), ("Neck", "Head"),
        ("Spine2", "LShoulder"), ("LShoulder", "LArm"), ("LArm", "LForeArm"), ("LForeArm", "LHand"),
        ("Spine2", "RShoulder"), ("RShoulder", "RArm"), ("RArm", "RForeArm"), ("RForeArm", "RHand"),
        ("Hips", "LUpLeg"), ("LUpLeg", "LLeg"), ("LLeg", "LFoot"),
        ("Hips", "RUpLeg"), ("RUpLeg", "RLeg"), ("RLeg", "RFoot"),
    ]

    for a, b in connections:
        if a not in bones or b not in bones:
            continue
        x1 = int(bones[a][0] * scale + cx)
        y1 = int(cy - bones[a][1] * scale)
        x2 = int(bones[b][0] * scale + cx)
        y2 = int(cy - bones[b][1] * scale)

        # Bresenham 画线
        dx, dy = abs(x2 - x1), abs(y2 - y1)
        sx, sy = (1 if x2 > x1 else -1), (1 if y2 > y1 else -1)
        err = dx - dy
        while True:
            if 0 <= x1 < width and 0 <= y1 < height:
                canvas[y1][x1] = "█" if a in ("Spine", "Spine1", "Spine2") else "▓"
            if x1 == x2 and y1 == y2:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x1 += sx
            if e2 < dx:
                err += dx
                y1 += sy

    # 画关节点
    joint_chars = {"Head": "●", "LHand": "○", "RHand": "○", "LFoot": "▲", "RFoot": "▲"}
    for name, (bx, by) in bones.items():
        x, y = int(bx * scale + cx), int(cy - by * scale)
        if 0 <= x < width and 0 <= y < height:
            canvas[y][x] = joint_chars.get(name, "●")

    return "\n".join("".join(row) for row in canvas)


def clear():
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()


if __name__ == "__main__":
    styles = ["idle", "chinese", "hiphop", "fired_up"]
    style_names = {"idle": "💤 待机", "chinese": "🏮 国风", "hiphop": "🎤 街舞", "fired_up": "🔥 战鬪"}

    print("\033[?25l")  # 隐藏光标
    try:
        frame = 0
        current_style = 0
        style_timer = 0

        while True:
            style = styles[current_style]
            bones = animate_bones(frame, style)

            clear()
            print(f"  ╔{'═'*42}╗")
            print(f"  ║  {style_names[style]:^38}  ║")
            print(f"  ╚{'═'*42}╝")
            print()
            print(render_skeleton(bones))
            print()
            print(f"  风格: {'█'*(current_style+1)}{'░'*(3-current_style)}")
            print(f"  ← → 切换舞风 | q 退出")

            frame += 1
            style_timer += 1
            if style_timer > 60:
                current_style = (current_style + 1) % len(styles)
                style_timer = 0

            time.sleep(0.08 if style == "fired_up" else 0.12)

    except KeyboardInterrupt:
        pass
    finally:
        clear()
        print("\033[?25h")  # 恢复光标
        print("哪吒退场 👋")
