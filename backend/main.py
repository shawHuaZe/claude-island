from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import Dict, Set
import asyncio
import json
import uuid
from datetime import datetime
import aiosqlite
import os

from models import SessionPhase, PermissionStatus, Session, Permission, HookEvent
from terminal import activate_terminal, get_claude_sessions_from_terminals

DATABASE_URL = os.path.join(os.path.dirname(__file__), "..", "..", "data", "claude_island.db")

# Ensure data directory exists
os.makedirs(os.path.dirname(DATABASE_URL), exist_ok=True)

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)

    async def broadcast(self, message: dict):
        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                disconnected.add(connection)
        for conn in disconnected:
            self.active_connections.discard(conn)


manager = ConnectionManager()

# Database helpers
async def init_db():
    async with aiosqlite.connect(DATABASE_URL) as db:
        await db.exec_driver_sql("PRAGMA foreign_keys = ON")
        # Create session table
        await db.exec_driver_sql("""
            CREATE TABLE IF NOT EXISTS session (
                id TEXT PRIMARY KEY,
                cwd TEXT NOT NULL DEFAULT '',
                phase TEXT NOT NULL DEFAULT 'idle',
                current_task TEXT NOT NULL DEFAULT '',
                user_prompt TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        # Create permission table
        await db.exec_driver_sql("""
            CREATE TABLE IF NOT EXISTS permission (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                tool_use_id TEXT NOT NULL,
                tool_name TEXT NOT NULL,
                tool_input TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                reason TEXT,
                created_at TEXT NOT NULL,
                responded_at TEXT,
                FOREIGN KEY (session_id) REFERENCES session(id)
            )
        """)
        # Add new columns if they don't exist (migration)
        try:
            await db.exec_driver_sql("ALTER TABLE session ADD COLUMN current_task TEXT NOT NULL DEFAULT ''")
        except:
            pass
        try:
            await db.exec_driver_sql("ALTER TABLE session ADD COLUMN user_prompt TEXT NOT NULL DEFAULT ''")
        except:
            pass
        await db.commit()


async def get_session(db: aiosqlite.Connection, session_id: str) -> dict | None:
    cursor = await db.execute("SELECT * FROM session WHERE id = ?", (session_id,))
    row = await cursor.fetchone()
    if row:
        return dict(row)
    return None


async def create_or_update_session(db: aiosqlite.Connection, session_id: str, cwd: str,
                                   phase: str, current_task: str = "", user_prompt: str = "") -> dict:
    now = datetime.utcnow().isoformat()

    # Check if session exists
    existing = await get_session(db, session_id)
    if existing:
        # Update existing session
        await db.execute("""
            UPDATE session SET
                cwd = ?, phase = ?, current_task = ?, user_prompt = ?, updated_at = ?
            WHERE id = ?
        """, (cwd, phase, current_task, user_prompt, now, session_id))
    else:
        # Insert new session
        await db.execute("""
            INSERT INTO session (id, cwd, phase, current_task, user_prompt, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (session_id, cwd, phase, current_task, user_prompt, now, now))
    await db.commit()
    return await get_session(db, session_id)


async def create_permission(db: aiosqlite.Connection, session_id: str, tool_use_id: str,
                           tool_name: str, tool_input: str) -> dict:
    perm_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    await db.execute("""
        INSERT INTO permission (id, session_id, tool_use_id, tool_name, tool_input, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (perm_id, session_id, tool_use_id, tool_name, tool_input, PermissionStatus.PENDING.value, now))
    await db.commit()
    cursor = await db.execute("SELECT * FROM permission WHERE id = ?", (perm_id,))
    row = await cursor.fetchone()
    return dict(row) if row else None


async def update_permission_status(db: aiosqlite.Connection, permission_id: str,
                                   status: PermissionStatus, reason: str = None) -> dict | None:
    now = datetime.utcnow().isoformat()
    await db.execute("""
        UPDATE permission SET status = ?, responded_at = ?, reason = ?
        WHERE id = ?
    """, (status.value, now, reason, permission_id))
    await db.commit()
    cursor = await db.execute("SELECT * FROM permission WHERE id = ?", (permission_id,))
    row = await cursor.fetchone()
    return dict(row) if row else None


@asynccontextmanager
async def get_db():
    async with aiosqlite.connect(DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        yield db


# FastAPI app
app = FastAPI(title="Claude Island Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    await init_db()


# Hook endpoints
@app.post("/hooks/{event_name}")
async def handle_hook(event_name: str, event: HookEvent):
    """Receive hook events from Claude Code"""
    async with get_db() as db:
        # Determine phase
        phase = _determine_phase(event_name, event.status, event.tool)

        # Extract current task from message or tool
        current_task = ""
        user_prompt = ""

        if event.message:
            user_prompt = event.message
            current_task = event.message[:50] if len(event.message) > 50 else event.message
        elif event.tool:
            current_task = event.tool

        # Create or update session
        session = await create_or_update_session(
            db, event.session_id, event.cwd, phase,
            current_task=current_task, user_prompt=user_prompt
        )

        # If permission request, create permission record
        permission_data = None
        if event_name == "PermissionRequest" and event.tool:
            tool_input_str = json.dumps(event.tool_input) if event.tool_input else None
            tool_use_id = event.tool_use_id or str(uuid.uuid4())
            permission_data = await create_permission(
                db, event.session_id, tool_use_id, event.tool, tool_input_str
            )

        # Broadcast to WebSocket clients
        broadcast_data = {
            "type": "hook_event",
            "event": event_name,
            "session": session,
            "permission": permission_data,
            "data": event.model_dump()
        }
        await manager.broadcast(broadcast_data)

    return {"status": "ok"}


def _determine_phase(event: str, status: str, tool: str = None) -> str:
    """Determine session phase from hook event"""
    if event == "PreCompact":
        return SessionPhase.COMPACTING.value

    if status == "waiting_for_approval":
        return SessionPhase.WAITING_FOR_APPROVAL.value

    status_map = {
        "waiting_for_input": SessionPhase.WAITING_FOR_INPUT.value,
        "running_tool": SessionPhase.PROCESSING.value,
        "processing": SessionPhase.PROCESSING.value,
        "starting": SessionPhase.PROCESSING.value,
        "compacting": SessionPhase.COMPACTING.value,
        "ended": SessionPhase.ENDED.value,
    }

    return status_map.get(status, SessionPhase.IDLE.value)


# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive
            data = await websocket.receive_text()
            await websocket.send_json({"type": "ack", "data": data})
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# Permission API
@app.get("/api/sessions")
async def list_sessions():
    """List all sessions"""
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM session ORDER BY updated_at DESC")
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    """Get session details"""
    async with get_db() as db:
        session = await get_session(db, session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        cursor = await db.execute(
            "SELECT * FROM permission WHERE session_id = ? ORDER BY created_at DESC",
            (session_id,)
        )
        permissions = [dict(row) for row in await cursor.fetchall()]

        return {**session, "permissions": permissions}


@app.get("/api/permissions/pending")
async def list_pending_permissions():
    """List all pending permissions"""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT p.*, s.cwd FROM permission p JOIN session s ON p.session_id = s.id "
            "WHERE p.status = 'pending' ORDER BY p.created_at DESC"
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


@app.post("/api/permissions/{permission_id}/approve")
async def approve_permission(permission_id: str, reason: str = None):
    """Approve a permission request"""
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM permission WHERE id = ?", (permission_id,))
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Permission not found")

        updated = await update_permission_status(db, permission_id, PermissionStatus.APPROVED, reason)

        await manager.broadcast({
            "type": "permission_update",
            "permission": updated
        })

        return updated


@app.post("/api/permissions/{permission_id}/deny")
async def deny_permission(permission_id: str, reason: str = None):
    """Deny a permission request"""
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM permission WHERE id = ?", (permission_id,))
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Permission not found")

        updated = await update_permission_status(db, permission_id, PermissionStatus.DENIED, reason)

        await manager.broadcast({
            "type": "permission_update",
            "permission": updated
        })

        return updated


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.post("/api/terminal/activate")
async def activate_terminal_endpoint():
    """Activate (bring to front) the Claude Code terminal window"""
    if sys.platform != "win32":
        return {"success": False, "message": "Not on Windows"}
    success, message = activate_terminal()
    return {"success": success, "message": message}


@app.get("/api/terminal/sessions")
async def get_terminal_sessions():
    """Get list of detected Claude Code terminal sessions"""
    if sys.platform != "win32":
        return {"sessions": []}
    sessions = get_claude_sessions_from_terminals()
    return {"sessions": sessions}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8080)
