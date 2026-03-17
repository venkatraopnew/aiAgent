from __future__ import annotations

from threading import Lock

from .models import InterviewState


class InterviewStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._by_id: dict[str, InterviewState] = {}

    def create(self, state: InterviewState) -> InterviewState:
        with self._lock:
            self._by_id[state.interview_id] = state
            return state

    def get(self, interview_id: str) -> InterviewState | None:
        with self._lock:
            return self._by_id.get(interview_id)

    def update(self, state: InterviewState) -> None:
        with self._lock:
            self._by_id[state.interview_id] = state


store = InterviewStore()

