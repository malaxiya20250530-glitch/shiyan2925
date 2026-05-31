#!/usr/bin/env python3
"""
feedback_dashboard.py — 自进化知识库仪表盘（纯标准库）
启动: python3 feedback_dashboard.py --port 8900
"""

import json
import sys
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from pathlib import Path

import feedback_store as fs

TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>自进化知识库 — 反馈仪表盘</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,system-ui,sans-serif;background:#0d1117;color:#c9d1d9;min-height:100vh}
.header{background:#161b22;border-bottom:1px solid #30363d;padding:16px 24px;position:sticky;top:0;z-index:10}
.header h1{font-size:20px;color:#58a6ff}
.stats{display:flex;gap:16px;margin-top:10px}
.stat{padding:4px 12px;border-radius:6px;font-size:13px}
.stat.pending{background:#d2992210;color:#d29922}
.stat.applied{background:#3fb95010;color:#3fb950}
.stat.rejected{background:#f8514910;color:#f85149}
.stat.total{background:#8b949e20;color:#8b949e}
.container{max-width:900px;margin:24px auto;padding:0 16px}
.card{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:16px;margin-bottom:12px}
.card-header{display:flex;justify-content:space-between;align-items:start;margin-bottom:10px}
.verdict{font-size:12px;padding:2px 8px;border-radius:4px;font-weight:600}
.verdict.contradicted{background:#f8514920;color:#f85149}
.verdict.verified{background:#3fb95020;color:#3fb950}
.verdict.uncertain{background:#d2992220;color:#d29922}
.claim{font-size:16px;color:#f0f6fc;margin-bottom:8px}
.fact{font-size:13px;color:#8b949e;margin-bottom:8px}
.meta{font-size:12px;color:#484f58;display:flex;gap:12px}
.actions{margin-top:10px;display:flex;gap:8px}
.btn{padding:6px 14px;border:none;border-radius:6px;font-size:13px;cursor:pointer;font-weight:500}
.btn-approve{background:#238636;color:#fff}
.btn-approve:hover{background:#2ea043}
.btn-reject{background:#da363320;color:#f85149;border:1px solid #f8514920}
.btn-reject:hover{background:#da363330}
.empty{text-align:center;padding:60px 20px;color:#484f58}
.empty h2{font-size:18px;margin-bottom:8px}
.refresh{background:#21262d;color:#c9d1d9;border:1px solid #30363d;padding:6px 14px;border-radius:6px;cursor:pointer}
.page-nav{display:flex;gap:8px;justify-content:center;margin:20px 0}
.page-btn{background:#21262d;color:#58a6ff;border:1px solid #30363d;padding:6px 12px;border-radius:6px;cursor:pointer}
.page-btn.active{background:#1f6feb;color:#fff;border-color:#1f6feb}
.correction-input{width:100%;background:#0d1117;border:1px solid #30363d;border-radius:6px;padding:8px;color:#c9d1d9;font-size:13px;margin-top:8px;display:none}
.correction-input.show{display:block}
.btn-rematch{background:#1f6feb20;color:#58a6ff;border:1px solid #1f6feb30}
.btn-rematch:hover{background:#1f6feb30}
.rematch-box{background:#0d1117;border:1px solid #30363d;border-radius:6px;padding:10px}
</style>
</head>
<body>
<div class="header">
  <h1>🧠 自进化知识库 — 反馈仪表盘</h1>
  <div class="stats">
    <span class="stat total">总计: {total}</span>
    <span class="stat pending">待复核: {pending}</span>
    <span class="stat applied">已应用: {applied}</span>
    <span class="stat rejected">已驳回: {rejected}</span>
  </div>
</div>
<div class="container">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
    <span style="font-size:14px;color:#8b949e">共 {pending} 条待复核记录</span>
    <button class="refresh" onclick="location.reload()">🔄 刷新</button>
  </div>
  {cards}
  {page_nav}
</div>
<script>
function approve(id){
  fetch('/api/approve',{
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({id:id,correction:''})
  }).then(r=>r.json()).then(d=>{if(d.ok)location.reload()})
}
function reject(id){
  fetch('/api/reject',{
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({id:id})
  }).then(r=>r.json()).then(d=>{if(d.ok)location.reload()})
}
function toggleRematch(id){
  var box=document.getElementById('rematch-'+id);
  box.style.display=box.style.display==='none'?'block':'none';
}
function rematch(id){
  var key=document.getElementById('kb-select-'+id).value;
  fetch('/api/rematch',{
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({id:id,rematch_key:key})
  }).then(r=>r.json()).then(d=>{if(d.ok)location.reload()})
}
</script>
</body>
</html>"""


def build_card(record: dict) -> str:
    vid = record["id"]
    v = record["verdict"]
    v_label = {"contradicted": "🔴 矛盾", "verified": "🟢 验证", "uncertain": "🟡 不确定"}.get(v, v)
    claim = record["claim"].replace("<", "&lt;").replace(">", "&gt;")
    fact = record["fact"].replace("<", "&lt;").replace(">", "&gt;")
    evidence = record.get("evidence", "")[:100]
    source = record.get("source", "")
    ts = record.get("created_at", 0)
    t_str = time.strftime("%Y-%m-%d %H:%M", time.localtime(float(ts))) if ts else ""

    # 生成KB键下拉选项
    from hallucination_detector import KNOWLEDGE_BASE
    kb_opts = "".join(f'<option value="{k}">{k}</option>' for k in sorted(KNOWLEDGE_BASE.keys()))

    return f"""<div class="card">
  <div class="card-header">
    <span class="verdict {v}">{v_label}</span>
    <span style="font-size:11px;color:#484f58">置信度: {record['confidence']:.0%}</span>
  </div>
  <div class="claim">💬 {claim}</div>
  <div class="fact">📋 {fact}</div>
  <div class="meta">
    <span>📚 {source}</span>
    <span>🕐 {t_str}</span>
    <span>#{vid}</span>
  </div>
  <div class="actions">
    <button class="btn btn-approve" onclick="approve({vid})">✅ 确认无误</button>
    <button class="btn btn-reject" onclick="reject({vid})">❌ 驳回</button>
    <button class="btn btn-rematch" onclick="toggleRematch({vid})">🔧 重新匹配</button>
  </div>
  <div id="rematch-{vid}" class="rematch-box" style="display:none;margin-top:10px">
    <select id="kb-select-{vid}" style="background:#0d1117;color:#c9d1d9;border:1px solid #30363d;border-radius:6px;padding:6px;width:100%;margin-bottom:6px">
      {kb_opts}
    </select>
    <button class="btn btn-approve" onclick="rematch({vid})">✅ 确认匹配</button>
    <button class="btn btn-reject" onclick="toggleRematch({vid})" style="margin-left:6px">取消</button>
  </div>
</div>"""


class FeedbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/" or path == "/feedback":
            self._serve_page()
        elif path == "/api/stats":
            self._json(fs.get_stats())
        else:
            self.send_error(404)

    def do_POST(self):
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length)) if length else {}

        if path == "/api/approve":
            rid = body.get("id")
            if rid:
                # 写入反馈库
                fs.apply_correction(rid, body.get("correction", ""))
                # 同时写入用户知识库
                self._kb_apply(rid)
                self._json({"ok": True})
            else:
                self._json({"ok": False, "error": "missing id"})
        elif path == "/api/reject":
            rid = body.get("id")
            if rid:
                fs.reject_record(rid)
                self._json({"ok": True})
            else:
                self._json({"ok": False, "error": "missing id"})
        elif path == "/api/rematch":
            rid = body.get("id")
            rematch_key = body.get("rematch_key")
            if rid and rematch_key:
                fs.set_rematch(rid, rematch_key)
                self._json({"ok": True})
            else:
                self._json({"ok": False, "error": "missing id or rematch_key"})
        else:
            self.send_error(404)


    def _kb_apply(self, record_id: int) -> None:
        """将已确认记录写入 kb_user.json"""
        try:
            import json as _json
            import sqlite3 as _sqlite
            from hallucination_detector import KNOWLEDGE_BASE as _KB

            conn = _sqlite.connect(str(fs.DB_PATH))
            conn.row_factory = _sqlite.Row
            row = conn.execute("SELECT * FROM feedback WHERE id = ?", (record_id,)).fetchone()
            conn.close()
            if not row:
                return
            record = dict(row)
            claim = record["claim"]
            fact = record["fact"]
            verdict = record["verdict"]
            source = record.get("source", "反馈记录")

            # 从 claim 提取关键词作 KB 键
            words = [w for w in claim if '一' <= w <= '鿿' or w.isalpha()]
            # 简单启发式：取前几个汉字/字母
            import re
            matches = re.findall(r'[一-鿿A-Za-z]{2,}', claim)
            key = matches[0] if matches else claim[:6]

            if verdict == "contradicted":
                new_fact = f"{claim}与已知事实矛盾——{fact}"
            elif verdict == "verified":
                new_fact = f"{claim}——经核实：{fact}"
            else:
                new_fact = f"{claim}——相关：{fact}"

            # 读写 kb_user.json
            kb_path = fs.DB_PATH.parent / "kb_user.json"
            with open(kb_path) as f:
                user_kb = _json.load(f)
            if key not in user_kb:
                user_kb[key] = {"facts": [], "source": source}
            if new_fact not in user_kb[key]["facts"]:
                user_kb[key]["facts"].append(new_fact)
            # 去重：不在已有事实中
            if key in _KB:
                existing = set(_KB[key]["facts"])
                user_kb[key]["facts"] = [f for f in user_kb[key]["facts"] if f not in existing]
            with open(kb_path, "w") as f:
                _json.dump(user_kb, f, ensure_ascii=False, indent=2)
        except Exception:
            pass  # KB写入失败不影响主流程
    def _serve_page(self):
        qs = parse_qs(urlparse(self.path).query)
        page = int(qs.get("page", [1])[0])
        per_page = 15
        records = fs.get_pending(page, per_page)
        total_pending = fs.get_pending_count()
        total_pages = max(1, (total_pending + per_page - 1) // per_page)
        stats = fs.get_stats()

        cards = "".join(build_card(r) for r in records) if records else \
            '<div class="empty"><h2>🎉 没有待复核记录</h2><p>所有反馈已处理完毕</p></div>'

        page_nav = ""
        if total_pages > 1:
            page_btns = []
            for p in range(1, total_pages + 1):
                cls = "page-btn active" if p == page else "page-btn"
                page_btns.append(f'<a class="{cls}" href="/feedback?page={p}">{p}</a>')
            page_nav = f'<div class="page-nav">{"".join(page_btns)}</div>'

        html = (TEMPLATE
            .replace("{total}", str(stats["total"]))
            .replace("{pending}", str(stats["pending"]))
            .replace("{applied}", str(stats["applied"]))
            .replace("{rejected}", str(stats["rejected"]))
            .replace("{cards}", cards)
            .replace("{page_nav}", page_nav))
        self._html(html)

    def _json(self, data):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def _html(self, html):
        body = html.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass  # 静默日志


def main():
    port = 8900
    for i, a in enumerate(sys.argv):
        if a == "--port" and i + 1 < len(sys.argv):
            port = int(sys.argv[i + 1])

    HTTPServer.allow_reuse_address = True
    server = HTTPServer(("127.0.0.1", port), FeedbackHandler)
    print(f"🧠 反馈仪表盘: http://127.0.0.1:{port}/feedback")
    print(f"   按 Ctrl+C 停止")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")


if __name__ == "__main__":
    main()
