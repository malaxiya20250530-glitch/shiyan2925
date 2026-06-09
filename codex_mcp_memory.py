#!/usr/bin/env python3
"""
轻量级 MCP 服务器 — 将 codex_memory 系统封装为 stdio JSON-RPC 协议。
用法: codex_mcp_memory.py（由 Codex MCP 客户端自动调用）
"""
import sys
import json
import subprocess
from pathlib import Path

HOME = Path("/data/data/com.termux/files/home")

def handle_request(req: dict) -> dict:
    """处理单个 JSON-RPC 请求"""
    method = req.get("method", "")
    req_id = req.get("id")

    if method == "initialize":
        return {"jsonrpc": "2.0", "id": req_id, "result": {
            "protocolVersion": "2024-11-05",
            "serverInfo": {"name": "codex-memory", "version": "1.0.0"},
            "capabilities": {"tools": {}}
        }}

    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": [
            {"name": "remember", "description": "保存一条永久记忆",
             "inputSchema": {"type": "object", "properties": {
                 "key": {"type": "string"}, "content": {"type": "string"}},
                 "required": ["key", "content"]}},
            {"name": "forget", "description": "删除一条记忆",
             "inputSchema": {"type": "object", "properties": {
                 "key": {"type": "string"}}, "required": ["key"]}},
            {"name": "context", "description": "获取当前会话上下文",
             "inputSchema": {"type": "object", "properties": {}}},
        ]}}

    if method == "tools/call":
        tool_name = req["params"]["name"]
        args = req["params"].get("arguments", {})

        if tool_name == "remember":
            key = args["key"]
            content = args["content"]
            subprocess.run(
                ["python3", str(HOME / "codex_memory.py"), "remember", key, content],
                capture_output=True, cwd=str(HOME))
            return {"jsonrpc": "2.0", "id": req_id, "result": {"content": [{"type": "text", "text": f"已记住: {key}"}]}}

        if tool_name == "forget":
            key = args["key"]
            subprocess.run(
                ["python3", str(HOME / "codex_memory.py"), "forget", key],
                capture_output=True, cwd=str(HOME))
            return {"jsonrpc": "2.0", "id": req_id, "result": {"content": [{"type": "text", "text": f"已遗忘: {key}"}]}}

        if tool_name == "context":
            result = subprocess.run(
                ["python3", str(HOME / "codex_memory.py"), "context"],
                capture_output=True, text=True, cwd=str(HOME))
            return {"jsonrpc": "2.0", "id": req_id, "result": {"content": [{"type": "text", "text": result.stdout}]}}

    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": "未知方法"}}

def main():
    """主循环：从 stdin 逐行读取 JSON-RPC 请求"""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            resp = handle_request(req)
            print(json.dumps(resp), flush=True)
        except json.JSONDecodeError:
            pass

if __name__ == "__main__":
    main()
