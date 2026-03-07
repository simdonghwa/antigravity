"""
RAG 지식베이스 — ChromaDB 기반 자동화 패턴 벡터 검색
로컬 임베딩 (SentenceTransformer MiniLM) 사용 → API 키 불필요
"""

from __future__ import annotations
import json
import logging
import threading
from typing import Optional

logger = logging.getLogger(__name__)

# ── ChromaDB 클라이언트 싱글톤 ────────────────────────────────

_client = None
_collections: dict = {}
_lock = threading.Lock()
_seeded = False


def get_rag_client():
    """ChromaDB 영구 저장 클라이언트 (싱글톤)"""
    global _client
    if _client is None:
        with _lock:
            if _client is None:
                try:
                    import chromadb
                    from config import settings
                    _client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
                    logger.info(f"ChromaDB initialized at {settings.chroma_persist_dir}")
                except Exception as e:
                    logger.error(f"ChromaDB init failed: {e}")
                    _client = None
    return _client


def _get_collection(name: str):
    """컬렉션 가져오기 (없으면 생성)"""
    global _collections
    if name not in _collections:
        client = get_rag_client()
        if client is None:
            return None
        try:
            _collections[name] = client.get_or_create_collection(
                name=name,
                metadata={"hnsw:space": "cosine"},
            )
        except Exception as e:
            logger.error(f"Collection {name} error: {e}")
            return None
    return _collections[name]


# ── 시딩 (최초 1회) ──────────────────────────────────────────

def rag_seed(force: bool = False) -> bool:
    """
    자동화 패턴 데이터를 ChromaDB에 로드.
    이미 로드된 경우 스킵 (idempotent).
    Returns: True if seeded, False if skipped or error
    """
    global _seeded
    if _seeded and not force:
        return False

    from rag.patterns import AUTOMATION_PATTERNS, TOOL_COMBINATIONS

    # 패턴 컬렉션
    pat_col = _get_collection("automation_patterns")
    if pat_col is None:
        logger.warning("RAG: collection unavailable, skipping seed")
        return False

    try:
        existing = pat_col.count()
        if existing >= len(AUTOMATION_PATTERNS) and not force:
            logger.info(f"RAG: patterns already seeded ({existing} items)")
            _seeded = True
            return False

        # upsert (idempotent)
        ids       = [p["id"] for p in AUTOMATION_PATTERNS]
        documents = [_pattern_to_text(p) for p in AUTOMATION_PATTERNS]
        metadatas = [_pattern_to_metadata(p) for p in AUTOMATION_PATTERNS]

        pat_col.upsert(ids=ids, documents=documents, metadatas=metadatas)
        logger.info(f"RAG: seeded {len(AUTOMATION_PATTERNS)} automation patterns")

    except Exception as e:
        logger.error(f"RAG pattern seed error: {e}")
        return False

    # 도구 조합 컬렉션
    tool_col = _get_collection("tool_combinations")
    if tool_col:
        try:
            tc_ids  = [t["id"] for t in TOOL_COMBINATIONS]
            tc_docs = [_tool_combo_to_text(t) for t in TOOL_COMBINATIONS]
            tc_meta = [{
                "name": t["name"],
                "monthly_cost_usd": t["monthly_cost_usd"],
                "tech_level": t["tech_level"],
                "best_for": json.dumps(t["best_for"], ensure_ascii=False),
            } for t in TOOL_COMBINATIONS]
            tool_col.upsert(ids=tc_ids, documents=tc_docs, metadatas=tc_meta)
            logger.info(f"RAG: seeded {len(TOOL_COMBINATIONS)} tool combinations")
        except Exception as e:
            logger.error(f"RAG tool combo seed error: {e}")

    _seeded = True
    return True


def _pattern_to_text(p: dict) -> str:
    """패턴을 임베딩용 텍스트로 변환"""
    return (
        f"{p['title']}. "
        f"업종: {', '.join(p['business_types'])}. "
        f"문제: {p['problem']}. "
        f"해결: {p['solution']}. "
        f"도구: {', '.join(p['tools'])}. "
        f"태그: {', '.join(p['tags'])}."
    )


def _pattern_to_metadata(p: dict) -> dict:
    """Chroma 메타데이터 (JSON 직렬화 가능 값만)"""
    return {
        "title": p["title"],
        "business_types": json.dumps(p["business_types"], ensure_ascii=False),
        "tools": json.dumps(p["tools"], ensure_ascii=False),
        "time_saved_hours_weekly": p.get("time_saved_hours_weekly", 0),
        "complexity": p.get("complexity", "MEDIUM"),
        "pattern_type": p.get("pattern_type", "LINEAR"),
        "tags": json.dumps(p.get("tags", []), ensure_ascii=False),
    }


def _tool_combo_to_text(t: dict) -> str:
    return (
        f"{t['name']}. {t['description']}. "
        f"도구: {', '.join(t['tools'])}. "
        f"적합 용도: {', '.join(t['best_for'])}."
    )


# ── 검색 ─────────────────────────────────────────────────────

def rag_search(
    query: str,
    n_results: int = 5,
    collection_name: str = "automation_patterns",
    where: Optional[dict] = None,
) -> list[dict]:
    """
    자연어 쿼리로 패턴 검색.
    Returns: 유사 패턴 리스트 (distance, metadata 포함)
    """
    col = _get_collection(collection_name)
    if col is None:
        logger.warning("RAG: collection not available")
        return []

    try:
        kwargs: dict = {"query_texts": [query], "n_results": min(n_results, col.count() or 1)}
        if where:
            kwargs["where"] = where

        results = col.query(**kwargs)

        output = []
        for i, doc in enumerate(results["documents"][0]):
            meta = results["metadatas"][0][i] if results["metadatas"] else {}
            dist = results["distances"][0][i] if results["distances"] else 1.0
            output.append({
                "text": doc,
                "distance": round(dist, 4),
                "similarity": round(1 - dist, 4),
                "metadata": meta,
            })

        return output

    except Exception as e:
        logger.error(f"RAG search error: {e}")
        return []


def rag_search_patterns_for_business(
    business_type: str,
    repeat_tasks: list[str],
    n_results: int = 5,
) -> list[dict]:
    """
    비즈니스 컨텍스트 기반 최적 자동화 패턴 검색.
    인터뷰 결과를 바탕으로 관련 패턴 추천.
    """
    query = f"{business_type} 업무 자동화: {', '.join(repeat_tasks[:5])}"
    return rag_search(query, n_results=n_results)


def rag_search_tools(
    use_case: str,
    tech_level: str = "MEDIUM",
    n_results: int = 3,
) -> list[dict]:
    """
    사용 사례 기반 도구 조합 추천 검색.
    """
    query = f"{use_case} 자동화 도구 추천"
    return rag_search(
        query,
        n_results=n_results,
        collection_name="tool_combinations",
    )


def format_rag_context(patterns: list[dict], max_chars: int = 2000) -> str:
    """
    검색된 패턴을 LLM 컨텍스트용 텍스트로 포맷팅.
    토큰 절약을 위해 max_chars 제한.
    """
    if not patterns:
        return "관련 자동화 패턴 없음"

    lines = ["## 유사 업무 자동화 사례 (RAG)\n"]
    total = len(lines[0])

    for i, p in enumerate(patterns, 1):
        meta = p.get("metadata", {})
        sim = p.get("similarity", 0)

        entry = (
            f"### 패턴 {i}: {meta.get('title', 'N/A')} "
            f"(유사도 {sim:.0%})\n"
            f"- 업종: {meta.get('business_types', '')}\n"
            f"- 도구: {meta.get('tools', '')}\n"
            f"- 절약: 주 {meta.get('time_saved_hours_weekly', '?')}시간\n"
            f"- 복잡도: {meta.get('complexity', '?')}\n\n"
        )

        if total + len(entry) > max_chars:
            break
        lines.append(entry)
        total += len(entry)

    return "".join(lines)
