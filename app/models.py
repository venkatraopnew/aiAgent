from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class CreateInterviewRequest(BaseModel):
    candidate_name: str
    candidate_phone: str
    role: str
    language: str = "en"
    intro: str = "Hi! This is an AI interview call. Are you ready to begin?"


class CreateInterviewResponse(BaseModel):
    interview_id: str


class StartCallResponse(BaseModel):
    call_sid: str


class InterviewPublic(BaseModel):
    interview_id: str
    candidate_name: str
    candidate_phone: str
    role: str
    language: str
    status: Literal["created", "calling", "in_progress", "completed", "failed"]
    transcript: list[dict] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


@dataclass
class InterviewState:
    interview_id: str = field(default_factory=lambda: uuid4().hex)
    candidate_name: str = ""
    candidate_phone: str = ""
    role: str = ""
    language: str = "en"
    intro: str = ""
    status: Literal["created", "calling", "in_progress", "completed", "failed"] = "created"
    call_sid: str | None = None
    transcript: list[dict] = field(default_factory=list)  # {role: "assistant"|"user", text: str, ts: iso}
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc)

    def to_public(self) -> InterviewPublic:
        return InterviewPublic(
            interview_id=self.interview_id,
            candidate_name=self.candidate_name,
            candidate_phone=self.candidate_phone,
            role=self.role,
            language=self.language,
            status=self.status,
            transcript=self.transcript,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

