from __future__ import annotations

from twilio.rest import Client

from ..settings import settings


def twilio_client() -> Client:
    return Client(settings.twilio_account_sid, settings.twilio_auth_token)


def start_outbound_call(*, to_number: str, interview_id: str) -> str:
    """
    Creates an outbound call. Twilio will request TwiML from /twilio/voice.
    """
    client = twilio_client()
    voice_url = f"{settings.app_base_url.rstrip('/')}/twilio/voice?interview_id={interview_id}"
    call = client.calls.create(
        to=to_number,
        from_=settings.twilio_from_number,
        url=voice_url,
        method="POST",
    )
    return call.sid

