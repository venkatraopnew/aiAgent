from __future__ import annotations

from openai import OpenAI

from ..models import InterviewState
from ..settings import settings


_client = OpenAI(api_key=settings.openai_api_key)


SYSTEM_PROMPT = """You are an AI recruiter conducting a short phone screening.
Rules:
- Be concise and friendly.
- Ask ONE question at a time.
- Keep questions relevant to the role.
- If the candidate answers, ask a brief follow-up or move to next question.
- If the candidate is unclear, ask for clarification.
- After ~6 questions total, wrap up politely and say goodbye.
"""


def next_assistant_text(state: InterviewState, candidate_text: str | None) -> str:
    messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]

    messages.append(
        {
            "role": "system",
            "content": f"Role: {state.role}. Candidate: {state.candidate_name}. Language: {state.language}.",
        }
    )

    for turn in state.transcript[-20:]:
        messages.append({"role": turn["role"], "content": turn["text"]})

    if candidate_text is None:
        messages.append({"role": "user", "content": "Start the interview now."})
    else:
        messages.append({"role": "user", "content": candidate_text})

    resp = _client.chat.completions.create(
        model=settings.openai_model,
        messages=messages,
        temperature=0.5,
    )
    return (resp.choices[0].message.content or "").strip() or "Thanks. Could you tell me a bit more?"

