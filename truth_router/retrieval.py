#!/usr/bin/env python3
"""检索模块 — 从知识库检索与查询相关的事实"""
import json, sqlite3, re, sys
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
KB_CORE = ROOT / "kb_core.json"
FACT_DB = ROOT / "knowledge" / "fact_store.db"


def _load_kb_core() -> dict:
    """加载语义索引"""
    try:
        if KB_CORE.exists():
            return json.loads(KB_CORE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _extract_entities(query: str, kb_core: dict) -> list[str]:
    """从查询中提取知识库内存在的实体名"""
    found = []
    for entity_name in kb_core:
        if entity_name in query:
            found.append(entity_name)
    return found


def _search_fact_db(keywords: list[str], limit: int = 10) -> list[dict]:
    """在 fact_store.db 中搜索匹配事实

    参数:
        keywords: 关键词列表（实体名）
        limit: 返回上限
    返回:
        [{"fact": str, "source": str, "confidence": float}, ...]
    """
    if not FACT_DB.exists():
        return []

    results = []
    try:
        conn = sqlite3.connect(str(FACT_DB))
        conn.row_factory = sqlite3.Row

        for kw in keywords:
            # 通过实体映射表查找
            rows = conn.execute(
                """SELECT f.fact, f.source, f.confidence
                   FROM facts_0 f
                   INNER JOIN entity_fact_map m ON m.fact_hash = f.hash
                   WHERE m.entity_name = ? AND f.active = 1
                   LIMIT ?""",
                (kw, limit)
            ).fetchall()
            for row in rows:
                results.append({
                    "fact": row["fact"],
                    "source": row["source"],
                    "confidence": row["confidence"],
                    "entity": kw,
                })

        conn.close()
    except Exception:
        pass

    return results


def _search_fts(query: str, limit: int = 10) -> list[dict]:
    """全文搜索回退（当实体映射无结果时）"""
    if not FACT_DB.exists():
        return []

    results = []
    try:
        conn = sqlite3.connect(str(FACT_DB))
        conn.row_factory = sqlite3.Row

        # 使用 FTS 表全文搜索
        terms = " OR ".join(f'"{t}"' for t in query.split() if len(t) >= 2)
        if not terms:
            conn.close()
            return []

        rows = conn.execute(
            f"""SELECT f.fact, f.source, f.confidence
                FROM facts_fts ft
                JOIN facts_0 f ON f.rowid = ft.rowid
                WHERE facts_fts MATCH ?
                LIMIT ?""",
            (terms, limit)
        ).fetchall()

        for row in rows:
            results.append({
                "fact": row["fact"],
                "source": row["source"],
                "confidence": row["confidence"],
            })

        conn.close()
    except Exception:
        pass

    return results


def retrieve(query: str, max_results: int = 10) -> dict:
    """检索与查询相关的事实

    参数:
        query: 用户查询文本
        max_results: 最大返回条数
    返回:
        {
            "query": str,
            "entities": [str, ...],
            "facts": [{"fact": str, "source": str, "confidence": float}, ...],
            "source": str  # "entity_map" | "fts" | "none"
        }
    """
    kb_core = _load_kb_core()
    entities = _extract_entities(query, kb_core)

    if entities:
        facts = _search_fact_db(entities, max_results)
        source = "entity_map"
    else:
        facts = _search_fts(query, max_results)
        source = "fts" if facts else "none"
        entities = []

    return {
        "query": query,
        "entities": entities,
        "facts": facts,
        "source": source,
    }


def main() -> None:
    if len(sys.argv) < 2:
        print("用法: python3 retrieval.py <查询文本>")
        sys.exit(1)

    query = " ".join(sys.argv[1:])
    result = retrieve(query)

    print(f"查询: {result['query']}")
    print(f"实体: {result['entities'] or '(未识别)'}")
    print(f"来源: {result['source']}")
    print(f"事实 ({len(result['facts'])} 条):")
    for f in result["facts"]:
        print(f"  [{f.get('entity', f['source'])}] {f['fact'][:80]} (置信度:{f['confidence']})")


if __name__ == "__main__":
    main()
