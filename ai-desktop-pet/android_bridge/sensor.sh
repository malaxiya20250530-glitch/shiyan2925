#!/data/data/com.termux/files/usr/bin/bash
# 传感器数据读取 —— 让宠物感知环境
SENSOR="${1:-light}"
termux-sensor -s "$SENSOR" -n 1 2>/dev/null | head -5
