from __future__ import annotations

import os
from pathlib import Path

import httpx

from ..settings import settings


STORAGE_DIR = Path("storage/audio")
STORAGE_DIR.mkdir(parents=True, exist_ok=True)


async def tts_to_file(text: str, *, filename_stem: str) -> Path:
    """
    Generates an mp3 using ElevenLabs and stores it locally.
    Returns the path to the mp3 file.
    """
    out_path = STORAGE_DIR / f"{filename_stem}.mp3"

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{settings.elevenlabs_voice_id}"
    headers = {
        "xi-api-key": settings.elevenlabs_api_key,
        "accept": "audio/mpeg",
        "content-type": "application/json",
    }
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {"stability": 0.4, "similarity_boost": 0.8},
    }

    timeout = httpx.Timeout(60.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.post(url, headers=headers, json=payload)
        r.raise_for_status()
        out_path.write_bytes(r.content)

    # Ensure file is non-empty
    if out_path.stat().st_size == 0:
        raise RuntimeError("ElevenLabs returned empty audio")

    return out_path

