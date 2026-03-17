from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from twilio.twiml.voice_response import Gather, VoiceResponse

from .models import (
    CreateInterviewRequest,
    CreateInterviewResponse,
    InterviewState,
    InterviewPublic,
    StartCallResponse,
)
from .services.elevenlabs_tts import tts_to_file
from .services.openai_agent import next_assistant_text
from .services.twilio_calls import start_outbound_call
from .store import store


app = FastAPI(title="AI Recruitment Phone Interviewer")

storage_dir = Path("storage")
storage_dir.mkdir(parents=True, exist_ok=True)
app.mount("/storage", StaticFiles(directory="storage"), name="storage")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.post("/api/interviews", response_model=CreateInterviewResponse)
def create_interview(payload: CreateInterviewRequest) -> CreateInterviewResponse:
    state = InterviewState(
        candidate_name=payload.candidate_name,
        candidate_phone=payload.candidate_phone,
        role=payload.role,
        language=payload.language,
        intro=payload.intro,
    )
    store.create(state)
    return CreateInterviewResponse(interview_id=state.interview_id)


@app.get("/api/interviews/{interview_id}", response_model=InterviewPublic)
def get_interview(interview_id: str) -> InterviewPublic:
    state = store.get(interview_id)
    if not state:
        raise HTTPException(status_code=404, detail="Interview not found")
    return state.to_public()


@app.post("/api/interviews/{interview_id}/start_call", response_model=StartCallResponse)
def api_start_call(interview_id: str) -> StartCallResponse:
    state = store.get(interview_id)
    if not state:
        raise HTTPException(status_code=404, detail="Interview not found")

    call_sid = start_outbound_call(to_number=state.candidate_phone, interview_id=interview_id)
    state.call_sid = call_sid
    state.status = "calling"
    state.touch()
    store.update(state)
    return StartCallResponse(call_sid=call_sid)


@app.get("/audio/{filename}")
def get_audio(filename: str) -> Response:
    path = Path("storage/audio") / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Audio not found")
    return FileResponse(path, media_type="audio/mpeg")


@app.post("/twilio/voice")
async def twilio_voice(request: Request) -> Response:
    """
    Main Twilio webhook (TwiML).

    Flow:
    - If no SpeechResult: greet + ask first question
    - Else: append candidate speech, ask OpenAI for next prompt, TTS via ElevenLabs, play, gather again
    """
    form = await request.form()
    interview_id = (request.query_params.get("interview_id") or form.get("interview_id") or "").strip()
    speech = (form.get("SpeechResult") or "").strip()

    state = store.get(interview_id) if interview_id else None
    if not state:
        vr = VoiceResponse()
        vr.say("Sorry, this interview session was not found. Goodbye.")
        return Response(content=str(vr), media_type="application/xml")

    vr = VoiceResponse()
    state.status = "in_progress"

    # First turn: intro + first AI question
    if not speech:
        if state.intro:
            intro_text = state.intro.strip()
            state.transcript.append({"role": "assistant", "text": intro_text, "ts": _now_iso()})

            intro_audio = await tts_to_file(intro_text, filename_stem=f"{state.interview_id}_intro")
            vr.play(f"{request.base_url}audio/{intro_audio.name}")

        assistant_text = next_assistant_text(state, candidate_text=None)
        state.transcript.append({"role": "assistant", "text": assistant_text, "ts": _now_iso()})
        audio = await tts_to_file(assistant_text, filename_stem=f"{state.interview_id}_{len(state.transcript)}")
        vr.play(f"{request.base_url}audio/{audio.name}")

        gather = Gather(
            input="speech",
            action=f"/twilio/voice?interview_id={state.interview_id}",
            method="POST",
            timeout=5,
            speech_timeout="auto",
        )
        gather.say("Please answer after the beep.")
        vr.append(gather)
        vr.redirect(f"/twilio/voice?interview_id={state.interview_id}", method="POST")

        state.touch()
        store.update(state)
        return Response(content=str(vr), media_type="application/xml")

    # Candidate answered
    state.transcript.append({"role": "user", "text": speech, "ts": _now_iso()})

    assistant_text = next_assistant_text(state, candidate_text=speech)
    state.transcript.append({"role": "assistant", "text": assistant_text, "ts": _now_iso()})

    audio = await tts_to_file(assistant_text, filename_stem=f"{state.interview_id}_{len(state.transcript)}")
    vr.play(f"{request.base_url}audio/{audio.name}")

    # Stop condition (simple heuristic)
    if "goodbye" in assistant_text.lower() or "bye" in assistant_text.lower():
        state.status = "completed"
        state.touch()
        store.update(state)
        vr.hangup()
        return Response(content=str(vr), media_type="application/xml")

    gather = Gather(
        input="speech",
        action=f"/twilio/voice?interview_id={state.interview_id}",
        method="POST",
        timeout=6,
        speech_timeout="auto",
    )
    gather.say("Please answer after the beep.")
    vr.append(gather)
    vr.redirect(f"/twilio/voice?interview_id={state.interview_id}", method="POST")

    state.touch()
    store.update(state)
    return Response(content=str(vr), media_type="application/xml")

