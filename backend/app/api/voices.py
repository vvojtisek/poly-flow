from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app.api.deps import Auth
from app.domain import voices
from app.schemas.profiles import VoiceOut
from app.services.tts import Tts, TtsUnavailable, get_tts

router = APIRouter(prefix="/api/v1/voices", tags=["profiles"])

TtsDep = Annotated[Tts, Depends(get_tts)]


@router.get("", response_model=list[VoiceOut])
async def list_voices(_: Auth, tts: TtsDep) -> list[VoiceOut]:
    """Voices a profile can choose per language, with whether the speech service has them."""
    installed = await tts.installed()
    return [
        VoiceOut(
            id=v.id,
            language=v.language,
            name=v.name,
            gender=v.gender,
            default=voices.DEFAULT_VOICES[v.language] == v.id,
            installed=v.id in installed,
        )
        for v in voices.CATALOG
    ]


@router.get(
    "/{voice_id}/sample",
    response_class=FileResponse,
    responses={
        200: {"content": {"audio/wav": {}}, "description": "A fixed sample sentence"},
        404: {"description": "voice_not_found"},
        503: {"description": "audio_unavailable: the TTS service or this voice is not there"},
    },
)
async def voice_sample(voice_id: str, _: Auth, tts: TtsDep) -> FileResponse:
    """A short fixed sentence in the voice, for choosing between voices."""
    voice = voices.BY_ID.get(voice_id)
    if voice is None:
        raise HTTPException(404, "voice_not_found")
    if voice_id not in await tts.installed():
        # speech() would fall back to the default voice: a preview must not pretend.
        raise HTTPException(503, "audio_unavailable")
    try:
        path = await tts.speech(voice.language, voices.SAMPLES[voice.language], voice.id)
    except TtsUnavailable as exc:
        raise HTTPException(503, "audio_unavailable") from exc
    return FileResponse(
        path, media_type="audio/wav", headers={"Cache-Control": "private, max-age=86400"}
    )
