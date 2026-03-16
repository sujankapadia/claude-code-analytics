"""
Hybrid Session Similarity Search Prototype

Combines three search layers:
1. FTS (keyword) — existing SQLite FTS5 via the API
2. Semantic (embeddings) — ChromaDB with message-level embeddings
3. Query expansion — local LLM via Ollama expands queries into synonyms

Prerequisites:
- API server running on localhost:8000 (claude-code-api)
- Ollama running with qwen3:8b (or another model — change OLLAMA_MODEL)
- pip install chromadb

Usage:
    python hybrid_search_prototype.py                          # Run default queries
    python hybrid_search_prototype.py "pagination" "dark mode" # Run specific queries

Results from 2026-03-15 testing (500 sessions, 3,434 user messages):
- "pagination" with expansion found 27 sessions (vs 7 without)
- "deploying to production" matched "let's continue with the deploy" at 0.53 similarity
- "error handling" expansion found logging/observability session via "graceful degradation"
"""

import contextlib
import json
import re
import sys
import time
import urllib.parse
import urllib.request

# Configuration
API_BASE = "http://localhost:8000/api"
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen3:8b"
MAX_SESSIONS = 500
MESSAGES_PER_SEMANTIC_QUERY = 15
MIN_SIMILARITY = 0.2
RRF_K = 60


def api_get(path):
    """Fetch from the API server."""
    with urllib.request.urlopen(f"{API_BASE}{path}") as r:  # nosec B310
        return json.loads(r.read())


def expand_query(query):
    """Expand a search query into alternative phrasings using a local LLM.

    Uses a simple prompt with no few-shot examples to avoid
    leaking test terms into expansions.
    """
    prompt = (
        f"List 6 alternative phrases a software developer might use "
        f'when discussing "{query}". Comma-separated only, no explanation.'
    )
    req = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(
            {
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
            }
        ).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:  # nosec B310
            resp = json.loads(r.read()).get("response", "").strip()
            # Strip thinking tags if the model uses them
            resp = re.sub(r"<think>.*?</think>", "", resp, flags=re.DOTALL).strip()
            return [t.strip() for t in resp.split(",") if t.strip()]
    except Exception as e:
        print(f"  LLM expansion failed: {e}")
        return []


def fts_search(query):
    """Run FTS search across all scopes, aggregate by session."""
    sessions = {}
    for scope, weight in [("Messages", 1.0), ("Tool Inputs", 1.5), ("Tool Results", 0.5)]:
        params = urllib.parse.urlencode({"q": query, "scope": scope, "per_page": "50"})
        try:
            with urllib.request.urlopen(f"{API_BASE}/search?{params}") as r:  # nosec B310
                data = json.loads(r.read())
            for sid, hits in data.get("results_by_session", {}).items():
                if sid not in sessions:
                    sessions[sid] = {"score": 0, "hits": 0, "samples": []}
                sessions[sid]["score"] += len(hits) * weight
                sessions[sid]["hits"] += len(hits)
                for h in hits[:1]:
                    snip = re.sub(
                        r"<[^>]+>",
                        "",
                        (h.get("snippet") or h.get("matched_content") or ""),
                    )[:100]
                    if snip:
                        sessions[sid]["samples"].append(snip)
        except Exception:
            pass
    return sessions


def semantic_search(collection, query, expansions, n_per=MESSAGES_PER_SEMANTIC_QUERY):
    """Run semantic search on original query + all expansions, merge by session."""
    all_queries = [query] + expansions
    sessions = {}

    for q in all_queries:
        results = collection.query(query_texts=[q], n_results=n_per)
        for j in range(len(results["ids"][0])):
            meta = results["metadatas"][0][j]
            sid = meta["session_id"]
            sim = 1 - results["distances"][0][j]
            if sim < MIN_SIMILARITY:
                continue
            doc = results["documents"][0][j].replace("\n", " ")[:100]

            if sid not in sessions:
                sessions[sid] = {
                    "best": 0,
                    "hits": 0,
                    "queries": set(),
                    "samples": [],
                }
            sessions[sid]["hits"] += 1
            sessions[sid]["queries"].add(q)
            if sim > sessions[sid]["best"]:
                sessions[sid]["best"] = sim
                sessions[sid]["samples"] = [f"({sim:.2f}) {doc}"]

    return sessions


def rrf_fusion(fts_sessions, sem_sessions, k=RRF_K):
    """Reciprocal Rank Fusion of FTS and semantic ranked lists."""
    fts_ranked = sorted(fts_sessions.items(), key=lambda x: -x[1]["score"])
    sem_ranked = sorted(sem_sessions.items(), key=lambda x: -x[1]["best"])

    scores = {}
    for rank, (sid, _) in enumerate(fts_ranked):
        scores[sid] = scores.get(sid, 0) + 1 / (k + rank + 1)
    for rank, (sid, _) in enumerate(sem_ranked):
        scores[sid] = scores.get(sid, 0) + 1 / (k + rank + 1)

    merged = []
    for sid in sorted(scores, key=lambda s: -scores[s]):
        merged.append(
            {
                "session_id": sid,
                "rrf": scores[sid],
                "fts": fts_sessions.get(sid, {}),
                "sem": sem_sessions.get(sid, {}),
            }
        )
    return merged


def build_index():
    """Load all sessions and index user messages in ChromaDB."""
    import chromadb

    print("Loading sessions and messages...")
    sessions_list = api_get(f"/sessions?limit={MAX_SESSIONS}")
    sessions_data = {
        s["session_id"]: (s.get("project_name") or "?").split("/")[-1] for s in sessions_list
    }

    all_docs, all_ids, all_meta = [], [], []
    for i, s in enumerate(sessions_list):
        sid = s["session_id"]
        project = sessions_data[sid]
        try:
            messages = api_get(f"/sessions/{sid}/messages")
        except Exception:
            continue

        for m in messages:
            if m["role"] != "user" or not m.get("content"):
                continue
            content = m["content"]
            if not isinstance(content, str) or len(content.strip()) < 20:
                continue
            if content.startswith("This session is being continued"):
                continue

            all_docs.append(content[:1000])
            all_ids.append(f"{sid}:{m['message_index']}")
            all_meta.append(
                {
                    "session_id": sid,
                    "project": project,
                    "message_index": m["message_index"],
                }
            )

        if (i + 1) % 100 == 0:
            print(f"  {i + 1}/{len(sessions_list)} sessions...")

    print(f"  {len(all_docs)} user messages to embed")

    # Index in ChromaDB (in-memory, ephemeral)
    print("Embedding messages...")
    client = chromadb.Client()
    with contextlib.suppress(Exception):
        client.delete_collection("messages")

    collection = client.create_collection("messages", metadata={"hnsw:space": "cosine"})

    start = time.time()
    for i in range(0, len(all_docs), 100):
        collection.add(
            documents=all_docs[i : i + 100],
            ids=all_ids[i : i + 100],
            metadatas=all_meta[i : i + 100],
        )
    elapsed = time.time() - start
    print(
        f"  Done: {len(all_docs)} messages in {elapsed:.1f}s ({len(all_docs) / elapsed:.0f} msgs/sec)"
    )

    return collection, sessions_data


def run_query(query, collection, sessions_data):
    """Run a full hybrid search for a query."""
    print(f"\n{'=' * 100}")
    print(f'  QUERY: "{query}"')
    print(f"{'=' * 100}")

    # Expand query
    print("  Expanding query via LLM...")
    expansions = expand_query(query)
    print(f"  Expansions: {', '.join(expansions[:6])}")

    # Run searches
    fts = fts_search(query)
    sem_no_exp = semantic_search(collection, query, [])
    sem_with_exp = semantic_search(collection, query, expansions)

    # Fuse
    hybrid = rrf_fusion(fts, sem_with_exp)

    # Compare approaches
    print(f"\n  {'Approach':<35s} {'Unique Sessions':>15s}")
    print(f"  {'-' * 55}")
    print(f"  {'FTS only':<35s} {len(fts):>15d}")
    print(f"  {'Semantic (no expansion)':<35s} {len(sem_no_exp):>15d}")
    print(f"  {'Semantic (with expansion)':<35s} {len(sem_with_exp):>15d}")

    # Show top 5 hybrid results
    print("\n  Hybrid Top 5:")
    for rank, r in enumerate(hybrid[:5]):
        project = sessions_data.get(r["session_id"], r["session_id"][:8])
        fts_h = r["fts"].get("hits", 0)
        sem_b = r["sem"].get("best", 0)
        sem_qs = r["sem"].get("queries", set())

        sources = []
        if fts_h:
            sources.append(f"FTS:{fts_h}")
        if sem_b:
            sources.append(f"Sem:{sem_b:.2f}")

        print(f"    #{rank + 1}  {project:22s}  rrf={r['rrf']:.4f}  ({', '.join(sources)})")

        for s in r["fts"].get("samples", [])[:1]:
            print(f"         FTS: {s[:85]}")
        for s in r["sem"].get("samples", [])[:1]:
            print(f"         Sem: {s[:85]}")
        if len(sem_qs) > 1:
            print(f"         Matched via: {', '.join(list(sem_qs)[:4])}")


def main():
    collection, sessions_data = build_index()

    queries = (
        sys.argv[1:]
        if len(sys.argv) > 1
        else [
            "pagination",
            "dark mode",
            "error handling",
            "deploying to production",
        ]
    )

    for query in queries:
        run_query(query, collection, sessions_data)


if __name__ == "__main__":
    main()
