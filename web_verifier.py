#!/usr/bin/env python3
"""
联网验证模块 — 零外部 API 依赖
用 DuckDuckGo HTML 搜索 + SQLite 持久化缓存（78 小时 TTL）
"""

import re
import time
import json
import hashlib
import sqlite3
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError
from urllib.parse import quote
from typing import Optional


DB_PATH = Path(__file__).parent / "web_cache.db"
CACHE_TTL = 78 * 3600  # 78 小时


def _hash_claim(claim: str) -> str:
    """对 claim 做 SHA256 取前 16 位作为缓存键"""
    return hashlib.sha256(claim.encode()).hexdigest()[:16]


def _extract_snippets(html: str) -> list[str]:
    """从 DuckDuckGo HTML 结果页提取摘要片段"""
    snippets = []
    for m in re.finditer(r'class="result__snippet"[^>]*>(.*?)</', html, re.DOTALL):
        text = re.sub(r'<[^>]+>', '', m.group(1)).strip()
        text = re.sub(r'\s+', ' ', text)
        if len(text) > 20:
            snippets.append(text)
    return snippets[:5]


class WebVerifier:
    """轻量联网验证器 — SQLite 持久化缓存"""

    def __init__(self):
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS web_cache (
                    claim_hash TEXT PRIMARY KEY,
                    claim TEXT NOT NULL,
                    snippets TEXT NOT NULL,
                    created_at REAL NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_web_cache_created
                ON web_cache(created_at)
            """)
            conn.commit()

    def _cache_get(self, claim_hash: str) -> Optional[list[str]]:
        """从 SQLite 读取缓存，过期返回 None"""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT snippets, created_at FROM web_cache WHERE claim_hash = ?",
                (claim_hash,)
            ).fetchone()
        if row is None:
            return None
        if time.time() - row["created_at"] > CACHE_TTL:
            self._cache_delete(claim_hash)
            return None
        return json.loads(row["snippets"])

    def _cache_set(self, claim_hash: str, claim: str, snippets: list[str]):
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO web_cache (claim_hash, claim, snippets, created_at) VALUES (?, ?, ?, ?)",
                (claim_hash, claim, json.dumps(snippets, ensure_ascii=False), time.time())
            )
            conn.commit()

    def _cache_delete(self, claim_hash: str):
        with self._connect() as conn:
            conn.execute("DELETE FROM web_cache WHERE claim_hash = ?", (claim_hash,))
            conn.commit()

    def search(self, claim: str, timeout: float = 8.0) -> list[str]:
        """搜索 claim 并返回摘要列表（先查缓存）"""
        claim_hash = _hash_claim(claim)

        # 1. 查缓存
        cached = self._cache_get(claim_hash)
        if cached is not None:
            return cached

        # 2. 网络请求
        query = quote(claim)
        url = f"https://html.duckduckgo.com/html/?q={query}"
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }

        try:
            req = Request(url, headers=headers)
            with urlopen(req, timeout=timeout) as resp:
                html = resp.read().decode("utf-8", errors="replace")
        except (URLError, OSError, TimeoutError):
            return []

        snippets = _extract_snippets(html)

        # 3. 写入缓存
        if snippets:
            self._cache_set(claim_hash, claim, snippets)

        return snippets

    def verify(self, claim: str) -> dict:
        """
        联网验证一条声明
        返回: {verdict, confidence, evidence, source}
        """
        snippets = self.search(claim)
        if not snippets:
            return {
                "verdict": "uncertain",
                "confidence": 0.0,
                "evidence": "无法连接搜索服务",
                "source": "web",
            }

        claim_words = set(claim)
        best_score = 0.0
        best_snippet = ""

        for s in snippets:
            s_words = set(s)
            overlap = len(claim_words & s_words) / max(len(claim_words), 1)
            if overlap > best_score:
                best_score = overlap
                best_snippet = s

        if best_score > 0.3:
            return {
                "verdict": "verified",
                "confidence": min(0.7, best_score),
                "evidence": best_snippet[:200],
                "source": "web (DuckDuckGo)",
            }
        elif best_score > 0.1:
            return {
                "verdict": "uncertain",
                "confidence": best_score,
                "evidence": best_snippet[:200] if best_snippet else "无直接相关结果",
                "source": "web (DuckDuckGo)",
            }
        else:
            return {
                "verdict": "uncertain",
                "confidence": 0.1,
                "evidence": "未找到相关网络信息",
                "source": "web",
            }

    def stats(self) -> dict:
        """缓存统计"""
        with self._connect() as conn:
            total = conn.execute("SELECT COUNT(*) as cnt FROM web_cache").fetchone()["cnt"]
            valid = conn.execute(
                "SELECT COUNT(*) as cnt FROM web_cache WHERE created_at > ?",
                (time.time() - CACHE_TTL,)
            ).fetchone()["cnt"]
        return {"total": total, "valid": valid, "expired": total - valid, "ttl_hours": CACHE_TTL / 3600}



class WikipediaVerifier:
    """Wikipedia API 验证器 — 免费，无需 Key"""

    def __init__(self):
        self.cache: dict[str, tuple[float, str]] = {}
        self.cache_ttl = 86400  # 24 小时

    def search(self, query: str, lang: str = "zh", timeout: float = 8.0) -> str:
        """搜索 Wikipedia 并返回提取的摘要文本"""
        if query in self.cache:
            ts, text = self.cache[query]
            if time.time() - ts < self.cache_ttl:
                return text

        # Wikipedia REST API
        from urllib.parse import quote as _quote
        url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{_quote(query)}"
        headers = {"User-Agent": "AwarenessGateway/2.0", "Accept": "application/json"}

        try:
            req = Request(url, headers=headers)
            with urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode())
            extract = data.get("extract", "")
            if extract:
                self.cache[query] = (time.time(), extract)
                return extract
        except Exception:
            pass

        # 回退：搜索 API
        try:
            search_url = f"https://{lang}.wikipedia.org/w/api.php?action=query&list=search&srsearch={_quote(query)}&format=json&srlimit=1"
            req = Request(search_url, headers=headers)
            with urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode())
            results = data.get("query", {}).get("search", [])
            if results:
                title = results[0]["title"]
                # 递归获取摘要
                return self.search(title, lang, timeout)
        except Exception:
            pass

        return ""

    def verify(self, claim: str) -> dict:
        """Wikipedia 验证"""
        extract = self.search(claim)
        if not extract:
            return {"verdict": "uncertain", "confidence": 0.0, "evidence": "", "source": "wikipedia"}

        # 简单关键词重叠
        claim_words = set(claim)
        extract_words = set(extract[:500])
        overlap = len(claim_words & extract_words) / max(len(claim_words), 1)

        if overlap > 0.15:
            return {
                "verdict": "verified",
                "confidence": min(0.8, overlap + 0.3),
                "evidence": extract[:300],
                "source": "Wikipedia",
            }
        return {
            "verdict": "uncertain",
            "confidence": overlap,
            "evidence": extract[:200],
            "source": "Wikipedia",
        }
