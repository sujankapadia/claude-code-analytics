# Session Similarity Search Prototypes

Throwaway scripts used to validate the hybrid search design. Not production code.

## Prerequisites

- API server running: `claude-code-api` (port 8000)
- Ollama running with a model: `ollama run qwen3:8b`
- ChromaDB installed: `pip install chromadb`

## Scripts

### `hybrid_search_prototype.py`

Full hybrid search: FTS + ChromaDB message-level embeddings + LLM query expansion.

```bash
# Default queries (pagination, dark mode, error handling, deploying to production)
python hybrid_search_prototype.py

# Custom queries
python hybrid_search_prototype.py "infinite scrolling" "database setup"
```

Indexes ~3,400 user messages across ~500 sessions in ~70 seconds, then runs queries interactively.

## Key Findings (2026-03-15)

1. **Message-level embeddings >> session-level**: Session-level compressed too much signal. Message-level gave 6/10 overlap on synonym pairs vs 2/10.

2. **Query expansion is essential for keywords**: Bare "pagination" returned noise from embeddings. Expanding to "infinite scroll, load more, offset and limit" found 27 sessions vs 7.

3. **FTS and embeddings are complementary**: FTS finds exact matches in tool inputs/code. Embeddings find semantic matches in conversation. Neither alone is sufficient.

4. **ChromaDB's default model (all-MiniLM-L6-v2) works**: Handles natural language well. Struggles with bare technical keywords, but query expansion compensates.

5. **Local LLM expansion is reliable**: qwen3:8b produces good expansions with a simple one-line prompt, no few-shot examples needed. ~1-2s latency.
