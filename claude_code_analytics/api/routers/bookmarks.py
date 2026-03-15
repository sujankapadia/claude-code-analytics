"""Router for message bookmarks."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from claude_code_analytics.api.dependencies import get_db_service
from claude_code_analytics.services.database_service import (
    DatabaseService,
)

router = APIRouter(tags=["bookmarks"])


class BookmarkCreate(BaseModel):
    session_id: str
    message_index: int
    name: str
    description: str = ""


class BookmarkUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


def _ensure_bookmarks_table(db: DatabaseService) -> None:
    """Create the bookmarks table if it doesn't exist."""
    conn = db._get_connection()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS bookmarks (
                bookmark_id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                message_index INTEGER NOT NULL,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
            )
        """
        )
        conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_bookmarks_session_message
            ON bookmarks(session_id, message_index)
        """
        )
        conn.commit()
    finally:
        conn.close()


def _enrich_bookmark(row: dict, conn) -> dict:
    """Add project_name and message snippet to a bookmark row."""
    cursor = conn.execute(
        """
        SELECT p.project_name
        FROM sessions s
        JOIN projects p ON s.project_id = p.project_id
        WHERE s.session_id = ?
        """,
        (row["session_id"],),
    )
    proj = cursor.fetchone()
    row["project_name"] = proj["project_name"] if proj else "Unknown"

    cursor = conn.execute(
        """
        SELECT SUBSTR(content, 1, 200) as snippet, role
        FROM messages
        WHERE session_id = ? AND message_index = ?
        """,
        (row["session_id"], row["message_index"]),
    )
    msg = cursor.fetchone()
    row["message_snippet"] = msg["snippet"] if msg else None
    row["message_role"] = msg["role"] if msg else None

    return row


@router.get("/bookmarks")
def list_bookmarks(
    project_id: str | None = None,
    db: DatabaseService = Depends(get_db_service),
):
    _ensure_bookmarks_table(db)
    conn = db._get_connection()
    try:
        if project_id:
            rows = conn.execute(
                """
                SELECT b.bookmark_id, b.session_id, b.message_index, b.name,
                       b.description, b.created_at
                FROM bookmarks b
                JOIN sessions s ON b.session_id = s.session_id
                WHERE s.project_id = ?
                ORDER BY b.created_at DESC
                """,
                (project_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT bookmark_id, session_id, message_index, name,
                       description, created_at
                FROM bookmarks
                ORDER BY created_at DESC
                """,
            ).fetchall()

        result = []
        for r in rows:
            row = {
                "bookmark_id": r["bookmark_id"],
                "session_id": r["session_id"],
                "message_index": r["message_index"],
                "name": r["name"],
                "description": r["description"],
                "created_at": r["created_at"],
            }
            result.append(_enrich_bookmark(row, conn))

        return result
    finally:
        conn.close()


@router.post("/bookmarks", status_code=201)
def create_bookmark(
    body: BookmarkCreate,
    db: DatabaseService = Depends(get_db_service),
):
    _ensure_bookmarks_table(db)
    conn = db._get_connection()
    try:
        # Verify the session and message exist
        cursor = conn.execute(
            "SELECT 1 FROM messages WHERE session_id = ? AND message_index = ?",
            (body.session_id, body.message_index),
        )
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Message not found")

        now = datetime.now(timezone.utc).isoformat()
        try:
            conn.execute(
                """
                INSERT INTO bookmarks (session_id, message_index, name, description, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (body.session_id, body.message_index, body.name, body.description, now),
            )
            conn.commit()
        except Exception as e:
            if "UNIQUE constraint" in str(e):
                raise HTTPException(
                    status_code=409, detail="Bookmark already exists for this message"
                )
            raise

        cursor = conn.execute(
            "SELECT bookmark_id FROM bookmarks WHERE session_id = ? AND message_index = ?",
            (body.session_id, body.message_index),
        )
        bookmark_id = cursor.fetchone()["bookmark_id"]

        row = {
            "bookmark_id": bookmark_id,
            "session_id": body.session_id,
            "message_index": body.message_index,
            "name": body.name,
            "description": body.description,
            "created_at": now,
        }
        return _enrich_bookmark(row, conn)
    finally:
        conn.close()


@router.patch("/bookmarks/{bookmark_id}")
def update_bookmark(
    bookmark_id: int,
    body: BookmarkUpdate,
    db: DatabaseService = Depends(get_db_service),
):
    _ensure_bookmarks_table(db)
    conn = db._get_connection()
    try:
        existing = conn.execute(
            "SELECT session_id, message_index, name, description, created_at FROM bookmarks WHERE bookmark_id = ?",
            (bookmark_id,),
        ).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Bookmark not found")

        new_name = body.name if body.name is not None else existing["name"]
        new_desc = body.description if body.description is not None else existing["description"]

        conn.execute(
            "UPDATE bookmarks SET name = ?, description = ? WHERE bookmark_id = ?",
            (new_name, new_desc, bookmark_id),
        )
        conn.commit()

        row = {
            "bookmark_id": bookmark_id,
            "session_id": existing["session_id"],
            "message_index": existing["message_index"],
            "name": new_name,
            "description": new_desc,
            "created_at": existing["created_at"],
        }
        return _enrich_bookmark(row, conn)
    finally:
        conn.close()


@router.delete("/bookmarks/{bookmark_id}", status_code=204)
def delete_bookmark(
    bookmark_id: int,
    db: DatabaseService = Depends(get_db_service),
):
    _ensure_bookmarks_table(db)
    conn = db._get_connection()
    try:
        existing = conn.execute(
            "SELECT 1 FROM bookmarks WHERE bookmark_id = ?", (bookmark_id,)
        ).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Bookmark not found")

        conn.execute("DELETE FROM bookmarks WHERE bookmark_id = ?", (bookmark_id,))
        conn.commit()
    finally:
        conn.close()


@router.get("/bookmarks/by-session/{session_id}")
def get_session_bookmarks(
    session_id: str,
    db: DatabaseService = Depends(get_db_service),
):
    """Get all bookmarks for a specific session (used by conversation viewer)."""
    _ensure_bookmarks_table(db)
    conn = db._get_connection()
    try:
        rows = conn.execute(
            """
            SELECT bookmark_id, session_id, message_index, name, description, created_at
            FROM bookmarks
            WHERE session_id = ?
            ORDER BY message_index
            """,
            (session_id,),
        ).fetchall()

        return [
            {
                "bookmark_id": r["bookmark_id"],
                "session_id": r["session_id"],
                "message_index": r["message_index"],
                "name": r["name"],
                "description": r["description"],
                "created_at": r["created_at"],
            }
            for r in rows
        ]
    finally:
        conn.close()
