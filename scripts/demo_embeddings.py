#!/usr/bin/env python3
"""
Demo: How semantic embeddings work with all-mpnet-base-v2

This script demonstrates:
1. Loading the model
2. Generating embeddings for sample conversations
3. Computing semantic similarity
4. Showing how search would work
"""

from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Tuple

# Sample conversation messages from typical Claude Code sessions
SAMPLE_MESSAGES = [
    # Error handling conversations
    "How do I handle async errors in TypeScript when using promises?",
    "What's the best way to catch exceptions in async/await functions?",
    "My try/catch block isn't catching promise rejections",

    # Database/SQLite conversations
    "How can I optimize SQLite query performance for large datasets?",
    "My database queries are running slowly, need help with indexes",
    "Best practices for using foreign keys in SQLite",

    # Git/version control
    "How do I undo a git commit that I already pushed?",
    "What's the difference between git reset and git revert?",
    "I need to resolve merge conflicts in my feature branch",

    # Testing conversations
    "How to write unit tests for async functions in Jest?",
    "My test is failing with 'cannot read property of undefined'",
    "Setting up test mocks for external API calls",

    # React/Frontend
    "How do I prevent unnecessary re-renders in React components?",
    "Using useEffect hook correctly to avoid infinite loops",
    "State management patterns in React applications",

    # Unrelated
    "What's the weather like today?",
    "Can you tell me a joke about programming?",
]


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Calculate cosine similarity between two vectors."""
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


def search_similar(
    query: str,
    documents: List[str],
    embeddings: np.ndarray,
    model: SentenceTransformer,
    top_k: int = 5
) -> List[Tuple[int, float, str]]:
    """
    Search for similar documents using semantic similarity.

    Returns:
        List of (index, similarity_score, document) tuples
    """
    # Embed the query
    query_embedding = model.encode(query, convert_to_tensor=False)

    # Compute similarities
    similarities = []
    for idx, doc_embedding in enumerate(embeddings):
        sim = cosine_similarity(query_embedding, doc_embedding)
        similarities.append((idx, sim, documents[idx]))

    # Sort by similarity (highest first)
    similarities.sort(key=lambda x: x[1], reverse=True)

    return similarities[:top_k]


def main():
    print("=" * 80)
    print("🧠 Semantic Embedding Demo with all-mpnet-base-v2")
    print("=" * 80)
    print()

    # Load model
    print("📥 Loading model (this will download ~420MB on first run)...")
    model = SentenceTransformer('all-mpnet-base-v2')
    print(f"✅ Model loaded: {model.get_sentence_embedding_dimension()} dimensions")
    print()

    # Generate embeddings
    print("🔄 Generating embeddings for sample conversations...")
    embeddings = model.encode(SAMPLE_MESSAGES, show_progress_bar=False)
    print(f"✅ Generated {len(embeddings)} embeddings")
    print(f"   Shape: {embeddings.shape} (messages × dimensions)")
    print(f"   Memory: {embeddings.nbytes / 1024:.1f} KB")
    print()

    # Show a sample embedding
    print("🔍 Example: First message embedding (showing first 10 values):")
    print(f"   Message: \"{SAMPLE_MESSAGES[0][:60]}...\"")
    print(f"   Vector:  {embeddings[0][:10]}")
    print(f"   (... and {len(embeddings[0]) - 10} more values)")
    print()

    # Demonstrate semantic similarity
    print("=" * 80)
    print("📊 Demonstrating Semantic Similarity")
    print("=" * 80)
    print()

    # Compare similar messages
    msg1_idx = 0  # async errors
    msg2_idx = 1  # async/await exceptions
    msg3_idx = 15 # weather (unrelated)

    sim_similar = cosine_similarity(embeddings[msg1_idx], embeddings[msg2_idx])
    sim_different = cosine_similarity(embeddings[msg1_idx], embeddings[msg3_idx])

    print(f"Message A: \"{SAMPLE_MESSAGES[msg1_idx]}\"")
    print(f"Message B: \"{SAMPLE_MESSAGES[msg2_idx]}\"")
    print(f"Similarity: {sim_similar:.4f} ⭐ HIGH (same topic)\n")

    print(f"Message A: \"{SAMPLE_MESSAGES[msg1_idx]}\"")
    print(f"Message C: \"{SAMPLE_MESSAGES[msg3_idx]}\"")
    print(f"Similarity: {sim_different:.4f} ❌ LOW (different topic)\n")

    # Show similarity matrix for error-handling messages
    print("📈 Similarity scores within 'error handling' topic:")
    error_indices = [0, 1, 2]
    for i in error_indices:
        for j in error_indices:
            if i < j:
                sim = cosine_similarity(embeddings[i], embeddings[j])
                print(f"   [{i}] ↔ [{j}]: {sim:.4f}")
    print()

    # Demonstrate search
    print("=" * 80)
    print("🔎 Semantic Search Demo")
    print("=" * 80)
    print()

    queries = [
        "promise error handling",
        "database performance tuning",
        "react performance optimization"
    ]

    for query in queries:
        print(f"Query: \"{query}\"")
        print("-" * 80)
        results = search_similar(query, SAMPLE_MESSAGES, embeddings, model, top_k=3)

        for rank, (idx, score, doc) in enumerate(results, 1):
            print(f"  {rank}. [Score: {score:.4f}] {doc}")
        print()

    # Show what a bad match looks like
    print("🎭 Example: Query with no relevant results")
    print("-" * 80)
    bad_query = "cooking recipes for pasta"
    print(f"Query: \"{bad_query}\"")
    results = search_similar(bad_query, SAMPLE_MESSAGES, embeddings, model, top_k=3)
    for rank, (idx, score, doc) in enumerate(results, 1):
        print(f"  {rank}. [Score: {score:.4f}] {doc}")
    print("\n   Notice: Even the 'best' match has a low score (< 0.3)")
    print()

    # Summary
    print("=" * 80)
    print("✨ Key Takeaways")
    print("=" * 80)
    print("• Similar meaning = high cosine similarity (> 0.5)")
    print("• Different topics = low similarity (< 0.3)")
    print("• Semantic search finds conceptually similar content, not just keywords")
    print("• Model understands: 'async errors' ≈ 'promise exceptions'")
    print("• Works across different phrasings of the same concept")
    print()
    print("🎯 For your 18K messages, this enables:")
    print("   'How did I handle X before?' → Find similar problems you solved")
    print()


if __name__ == "__main__":
    main()
