#!/usr/bin/env python3
"""
Embed all conversation messages into ChromaDB for semantic search.

This script:
1. Reads all messages from the SQLite database
2. Generates embeddings using all-mpnet-base-v2
3. Stores in ChromaDB with metadata for filtering
"""

import sqlite3
import chromadb
from sentence_transformers import SentenceTransformer
from pathlib import Path
import sys
from typing import List, Dict
from datetime import datetime


def get_all_messages(db_path: str) -> List[Dict]:
    """
    Fetch all messages from SQLite with relevant metadata.

    Returns:
        List of dicts with message content and metadata
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # Return rows as dicts

    cursor = conn.cursor()

    query = """
    SELECT
        m.message_id,
        m.session_id,
        m.message_index,
        m.role,
        m.content,
        m.timestamp,
        s.project_id,
        p.project_name,
        s.start_time as session_start,
        s.message_count as session_message_count
    FROM messages m
    JOIN sessions s ON m.session_id = s.session_id
    JOIN projects p ON s.project_id = p.project_id
    WHERE m.content IS NOT NULL AND LENGTH(m.content) > 0
    ORDER BY m.timestamp
    """

    cursor.execute(query)
    messages = [dict(row) for row in cursor.fetchall()]

    conn.close()

    return messages


def create_preview(content: str, max_length: int = 100) -> str:
    """Create a preview of message content."""
    if len(content) <= max_length:
        return content
    return content[:max_length] + "..."


def embed_conversations(db_path: str, chroma_path: str, batch_size: int = 100):
    """
    Main embedding process.

    Args:
        db_path: Path to SQLite database
        chroma_path: Path to ChromaDB storage directory
        batch_size: Number of messages to embed at once
    """
    print("🚀 Starting conversation embedding process...")
    print(f"📊 Database: {db_path}")
    print(f"💾 ChromaDB: {chroma_path}\n")

    # Load messages from SQLite
    print("1️⃣  Loading messages from database...")
    messages = get_all_messages(db_path)
    print(f"   Found {len(messages):,} messages to embed\n")

    if not messages:
        print("❌ No messages found in database!")
        return

    # Initialize ChromaDB
    print("2️⃣  Initializing ChromaDB...")
    client = chromadb.PersistentClient(path=chroma_path)

    # Delete existing collection if it exists (for fresh start)
    try:
        client.delete_collection("conversations")
        print("   Deleted existing collection")
    except:
        pass

    collection = client.create_collection(
        name="conversations",
        metadata={"description": "Claude Code conversation history"}
    )
    print(f"   Created collection: conversations\n")

    # Load embedding model
    print("3️⃣  Loading embedding model (all-mpnet-base-v2)...")
    model = SentenceTransformer('all-mpnet-base-v2')
    print(f"   Model loaded: {model.get_sentence_embedding_dimension()} dimensions\n")

    # Process messages in batches
    print("4️⃣  Generating embeddings and storing in ChromaDB...")
    total = len(messages)

    for i in range(0, total, batch_size):
        batch = messages[i:i + batch_size]
        batch_end = min(i + batch_size, total)

        # Prepare data for this batch
        documents = [msg['content'] for msg in batch]
        ids = [f"msg_{msg['message_id']}" for msg in batch]
        metadatas = [
            {
                "message_id": str(msg['message_id']),
                "session_id": msg['session_id'],
                "project_id": msg['project_id'],
                "project_name": msg['project_name'],
                "role": msg['role'],
                "timestamp": msg['timestamp'] or "",
                "message_index": msg['message_index'],
                "preview": create_preview(msg['content']),
                "session_start": msg['session_start'] or "",
                "session_message_count": msg['session_message_count']
            }
            for msg in batch
        ]

        # Generate embeddings for this batch
        embeddings = model.encode(documents, show_progress_bar=False).tolist()

        # Add to ChromaDB
        collection.add(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )

        # Progress indicator
        progress = (batch_end / total) * 100
        print(f"   Progress: {batch_end:,}/{total:,} ({progress:.1f}%)")

    print(f"\n✅ Embedding complete!")
    print(f"   Total messages embedded: {total:,}")
    print(f"   Collection size: {collection.count():,}")

    # Show some stats
    print("\n📊 Statistics:")
    roles = {}
    projects = {}
    for msg in messages:
        roles[msg['role']] = roles.get(msg['role'], 0) + 1
        projects[msg['project_name']] = projects.get(msg['project_name'], 0) + 1

    print(f"   By role:")
    for role, count in sorted(roles.items()):
        print(f"     {role}: {count:,}")

    print(f"   By project (top 5):")
    for project, count in sorted(projects.items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"     {project}: {count:,}")


def main():
    """Main entry point."""
    # Default paths
    home = Path.home()
    db_path = home / "claude-conversations" / "conversations.db"
    chroma_path = home / "claude-conversations" / "chroma_db"

    # Check if database exists
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        print("   Run import_conversations.py first to create the database.")
        sys.exit(1)

    # Run embedding process
    try:
        embed_conversations(str(db_path), str(chroma_path))
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
