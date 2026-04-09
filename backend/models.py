from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class SessionPhase(str, Enum):
    IDLE = "idle"
    PROCESSING = "processing"
    WAITING_FOR_INPUT = "waiting_for_input"
    WAITING_FOR_APPROVAL = "waiting_for_approval"
    COMPACTING = "compacting"
    ENDED = "ended"


class PermissionStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"


class Session(SQLModel, table=True):
    id: str = Field(primary_key=True)
    cwd: str = ""
    phase: SessionPhase = SessionPhase.IDLE
    current_task: str = ""  # Current task description
    user_prompt: str = ""    # Latest user prompt
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Permission(SQLModel, table=True):
    id: str = Field(primary_key=True)
    session_id: str = Field(foreign_key="session.id")
    tool_use_id: str
    tool_name: str
    tool_input: Optional[str] = None  # JSON string
    status: PermissionStatus = PermissionStatus.PENDING
    reason: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    responded_at: Optional[datetime] = None


class HookEvent(SQLModel):
    session_id: str
    cwd: str
    event: str
    status: str
    tool: Optional[str] = None
    tool_input: Optional[dict] = None
    tool_use_id: Optional[str] = None
    notification_type: Optional[str] = None
    message: Optional[str] = None
