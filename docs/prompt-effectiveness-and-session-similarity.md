# Prompt Effectiveness Scoring & Session Similarity Clustering

Two complementary features that turn raw conversation history into actionable insights about how you work with AI coding assistants.

---

## 1. Prompt Effectiveness Scoring

### The Problem

Not all prompts are equal. Some lead to Claude immediately doing the right thing in 3 messages. Others spiral into 50+ messages of corrections, backtracking, and "no, not that." Most developers have no visibility into which of their prompting habits produce good outcomes and which waste time and tokens.

### What It Does

Assigns an **effectiveness score** (0-100) to each user prompt based on measurable downstream signals, then surfaces patterns about what makes prompts work well or poorly.

### Scoring Signals

Each signal is derived from data already in the database:

| Signal | Measures | Source |
|--------|----------|--------|
| **Correction density** | How often the user says "no," "not that," "instead," "undo" after a prompt | Message content (NLP keywords + patterns) |
| **Tool error rate** | % of tool calls that fail after this prompt's response chain | `tool_uses.is_error` |
| **Response chain length** | Messages between this prompt and the next user prompt | `messages.message_index` gaps |
| **Token efficiency** | Output tokens per successful tool call | `messages.output_tokens` / successful tool count |
| **Time to next prompt** | How long before the user needed to intervene again | `messages.timestamp` deltas |
| **Edit-after-write ratio** | How often Claude edits a file it just wrote (indicates first attempt was wrong) | Sequential Write/Edit tool calls on same file |

### Scoring Formula

Weighted composite — higher is better:

```
score = (
    30 * (1 - correction_density)     # No corrections needed
  + 20 * (1 - tool_error_rate)        # Tools succeed
  + 20 * brevity_factor               # Short response chains
  + 15 * token_efficiency             # Not wasteful
  + 15 * (1 - edit_after_write_ratio) # Gets it right first time
)
```

Weights are tunable. The formula should be transparent in the UI so users understand what drives the score.

### UI Concepts

**Session View Enhancement**
- Small colored badge next to each user message: green (80+), yellow (50-79), red (<50)
- Hover shows breakdown: "Score: 72 — 0 corrections, 1 tool error, 4-message chain"

**Prompt Effectiveness Dashboard**
- Distribution histogram of all prompt scores
- Top 10 most effective prompts (with links to sessions)
- Bottom 10 least effective prompts
- Score trends over time (are you getting better at prompting?)

**Personal Style Guide** (LLM-generated)
- Periodically analyze your top-scoring vs. bottom-scoring prompts
- Generate a "What works for you" summary:
  - "Your best prompts include specific file paths (avg score: 85)"
  - "Prompts starting with 'fix' score 20 points higher than 'change'"
  - "You get better results when you include expected behavior"

### Data Requirements

All signals come from existing `messages` and `tool_uses` tables. No new data collection needed. Scoring can be computed on-demand or pre-computed during import.

### Implementation Approach

**Phase 1: Core scoring engine** (backend)
- New service: `prompt_scoring.py`
- Compute scores for all user messages in a session
- Store in a new `prompt_scores` table or compute on-the-fly

**Phase 2: Session view integration** (frontend)
- Score badges on user messages
- Score breakdown tooltip

**Phase 3: Dashboard + Style Guide** (frontend + LLM analysis)
- New analytics page or tab
- LLM-powered style guide generation (reuse existing analysis infrastructure)

---

## 2. Session Similarity & Clustering

### The Problem

After hundreds of sessions, you've likely solved similar problems multiple times without knowing it. When you start a new task, you have no way to find past sessions where you (or Claude) already tackled something related. The search feature finds keyword matches, but can't answer "show me sessions where I did something like this."

### What It Does

Groups sessions by semantic similarity and surfaces relevant past sessions when you're working on related tasks.

### How It Works

**Embedding-based similarity:**

1. For each session, generate an embedding from a compact representation:
   - First user message (the task description)
   - Tool names used (characterizes the type of work)
   - File paths touched (characterizes the domain)
   - Project name

2. Store embeddings in the database (new `session_embeddings` table)

3. Use cosine similarity to find related sessions

### Compact Session Fingerprint

Rather than embedding the entire transcript (expensive, noisy), build a structured fingerprint:

```
Task: "Add pagination to the sessions API endpoint"
Tools: Bash(3), Read(12), Edit(8), Grep(5), Write(2)
Files: api/routers/sessions.py, frontend/src/pages/sessions.tsx, tests/test_sessions.py
Project: claude-code-analytics
Duration: 45m, Messages: 32, Outcome: committed
```

This fingerprint is small enough to embed cheaply and captures the essence of what happened.

### Embedding Strategy

Two options, not mutually exclusive:

**Option A: Local embeddings (offline, free)**
- Use a local model via Ollama (e.g., `nomic-embed-text`, `mxbai-embed-large`)
- Runs entirely on the user's machine
- ~100ms per session, batch-processable
- Store 768-1536 dim vectors in SQLite (as BLOB or in a vec extension)

**Option B: API embeddings (higher quality)**
- Use the configured OpenAI-compatible provider's embedding endpoint
- Better semantic understanding but costs money
- Good for users who already have API keys configured

### Similarity Search

Given a session (or a text query), find the N most similar sessions:

```sql
-- Pseudocode: find sessions with most similar embeddings
SELECT session_id, cosine_similarity(embedding, ?) as score
FROM session_embeddings
ORDER BY score DESC
LIMIT 10
```

For SQLite, use `sqlite-vec` extension or compute in Python with numpy.

### Clustering

Beyond pairwise similarity, cluster all sessions into groups:

- **K-means or HDBSCAN** on the embedding space
- Auto-label clusters using LLM: "Frontend styling work", "API endpoint development", "Bug fixing", "Documentation"
- Clusters reveal work patterns: "You spend 40% of your time on API development, 25% on frontend, 20% on debugging"

### UI Concepts

**Session Detail: "Related Sessions" Panel**
- Below the session stats, show 3-5 most similar past sessions
- "You worked on something similar 2 weeks ago in `lxr` — 87% similar"
- Click to open that session

**Cluster Explorer Page**
- Visual cluster map (2D projection of embeddings via t-SNE/UMAP)
- Each dot is a session, colored by cluster
- Click a cluster to see its sessions and auto-generated label
- Filter by project, date range

**"Have I done this before?" Search**
- Text input: describe what you're about to do
- Returns similar past sessions ranked by relevance
- Different from keyword search — understands semantic meaning

### Data Requirements

- New table: `session_embeddings` (session_id, embedding BLOB, fingerprint TEXT, created_at)
- New table: `session_clusters` (session_id, cluster_id, cluster_label)
- Embedding generation during import or as a batch job

### Implementation Approach

**Phase 1: Fingerprint generation** (backend)
- Generate compact fingerprints for all sessions
- Store in database

**Phase 2: Local embeddings** (backend)
- Integrate with Ollama for local embedding generation
- Cosine similarity search
- "Related Sessions" panel in session detail view

**Phase 3: Clustering** (backend + frontend)
- HDBSCAN clustering on embeddings
- LLM-powered cluster labeling
- Cluster explorer page with visualization

**Phase 4: "Have I done this before?"** (frontend)
- Semantic search input on a new page
- Embedding-based retrieval

---

## How They Connect

These features reinforce each other:

- **Effectiveness scores + similarity**: "The last time you did something similar, your prompts scored 85. Here's the prompt that worked best."
- **Clusters + effectiveness**: "Your API development cluster has an average prompt score of 72, but your debugging cluster is only 45 — you might benefit from more structured bug reports."
- **Style guide + similar sessions**: "For tasks like this, your most effective approach has been to start with a file read, then describe the change, rather than jumping straight to 'fix this bug.'"

## Open Questions

1. **Scoring calibration**: Should scores be absolute or relative to your own history? Relative means everyone starts at 50 and improves. Absolute means a 90 is a 90 regardless of who you are.

2. **Embedding model choice**: Local (free, private) vs. API (better quality). Default to local with Ollama, offer API as upgrade?

3. **Real-time vs. batch**: Score prompts during import (always up to date) or compute on demand (simpler)?

4. **Privacy**: Embeddings are one-way (can't reconstruct the text), but fingerprints contain file paths and task descriptions. Should fingerprints be opt-in?
