"""Audio API endpoints for voice-based AI conversations.

Provides endpoints for Speech-to-Text and Text-to-Speech functionality.
"""

from typing import Optional
import base64
import structlog
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field

from src.services.audio_service import get_audio_service

logger = structlog.get_logger()
router = APIRouter(prefix="/audio", tags=["Audio"])


# ─────────────────────────────────────────────────────────────────────────────
# Request/Response Models
# ─────────────────────────────────────────────────────────────────────────────

class TranscriptionResponse(BaseModel):
    """Response model for speech transcription."""
    success: bool
    transcript: str
    confidence: float = Field(ge=0.0, le=1.0)
    language: str = "es-MX"
    alternatives: list[dict] = []
    error: Optional[str] = None


class SynthesisRequest(BaseModel):
    """Request model for text-to-speech synthesis."""
    text: str = Field(..., min_length=1, max_length=5000)
    language_code: str = "es-MX"
    voice_name: Optional[str] = None
    speaking_rate: float = Field(default=1.0, ge=0.25, le=4.0)
    pitch: float = Field(default=0.0, ge=-20.0, le=20.0)
    audio_encoding: str = "MP3"


class SynthesisResponse(BaseModel):
    """Response model for speech synthesis."""
    success: bool
    audio_content: Optional[str] = None  # Base64 encoded audio
    audio_bytes: int = 0
    format: str = "mp3"
    voice: Optional[str] = None
    language: str = "es-MX"
    error: Optional[str] = None


class VoiceConversationRequest(BaseModel):
    """Request for a full voice conversation turn."""
    session_id: str
    audio_content: str  # Base64 encoded audio
    language_code: str = "es-MX"


class VoiceConversationResponse(BaseModel):
    """Response for a voice conversation turn."""
    success: bool
    user_transcript: str = ""
    assistant_response: str = ""
    response_audio: Optional[str] = None  # Base64 encoded audio
    error: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(
    audio: UploadFile = File(...),
    language_code: str = Form(default="es-MX"),
    sample_rate: int = Form(default=16000),
) -> TranscriptionResponse:
    """Transcribe uploaded audio file to text.

    Args:
        audio: Audio file (WAV, MP3, FLAC, or WEBM)
        language_code: Language code for transcription
        sample_rate: Audio sample rate in Hz

    Returns:
        Transcription result with confidence score
    """
    try:
        audio_service = get_audio_service()
        if not audio_service:
            raise HTTPException(
                status_code=503,
                detail="Audio service not available"
            )

        # Read audio content
        audio_content = await audio.read()

        # Determine encoding from content type
        content_type = audio.content_type or "audio/wav"
        encoding_map = {
            "audio/wav": "LINEAR16",
            "audio/wave": "LINEAR16",
            "audio/x-wav": "LINEAR16",
            "audio/mp3": "MP3",
            "audio/mpeg": "MP3",
            "audio/flac": "FLAC",
            "audio/webm": "WEBM_OPUS",
        }
        encoding = encoding_map.get(content_type, "LINEAR16")

        # Transcribe
        result = await audio_service.speech_to_text(
            audio_content=audio_content,
            language_code=language_code,
            sample_rate_hertz=sample_rate,
            encoding=encoding,
        )

        return TranscriptionResponse(
            success=result.get("success", False),
            transcript=result.get("transcript", ""),
            confidence=result.get("confidence", 0.0),
            language=language_code,
            alternatives=result.get("alternatives", []),
            error=result.get("error"),
        )

    except Exception as e:
        logger.error("Transcription endpoint error", error=str(e))
        return TranscriptionResponse(
            success=False,
            transcript="",
            confidence=0.0,
            error=str(e),
        )


@router.post("/transcribe/base64", response_model=TranscriptionResponse)
async def transcribe_audio_base64(
    audio_content: str,
    language_code: str = "es-MX",
    sample_rate: int = 16000,
    encoding: str = "LINEAR16",
) -> TranscriptionResponse:
    """Transcribe base64-encoded audio to text.

    Args:
        audio_content: Base64-encoded audio data
        language_code: Language code for transcription
        sample_rate: Audio sample rate in Hz
        encoding: Audio encoding (LINEAR16, MP3, FLAC, WEBM_OPUS)

    Returns:
        Transcription result
    """
    try:
        audio_service = get_audio_service()
        if not audio_service:
            raise HTTPException(
                status_code=503,
                detail="Audio service not available"
            )

        # Decode base64 audio
        audio_bytes = base64.b64decode(audio_content)

        # Transcribe
        result = await audio_service.speech_to_text(
            audio_content=audio_bytes,
            language_code=language_code,
            sample_rate_hertz=sample_rate,
            encoding=encoding,
        )

        return TranscriptionResponse(
            success=result.get("success", False),
            transcript=result.get("transcript", ""),
            confidence=result.get("confidence", 0.0),
            language=language_code,
            alternatives=result.get("alternatives", []),
            error=result.get("error"),
        )

    except Exception as e:
        logger.error("Base64 transcription error", error=str(e))
        return TranscriptionResponse(
            success=False,
            transcript="",
            confidence=0.0,
            error=str(e),
        )


@router.post("/synthesize", response_model=SynthesisResponse)
async def synthesize_speech(request: SynthesisRequest) -> SynthesisResponse:
    """Convert text to speech audio.

    Args:
        request: Synthesis parameters including text and voice settings

    Returns:
        Base64-encoded audio content
    """
    try:
        audio_service = get_audio_service()
        if not audio_service:
            raise HTTPException(
                status_code=503,
                detail="Audio service not available"
            )

        result = await audio_service.text_to_speech(
            text=request.text,
            language_code=request.language_code,
            voice_name=request.voice_name,
            speaking_rate=request.speaking_rate,
            pitch=request.pitch,
            audio_encoding=request.audio_encoding,
        )

        return SynthesisResponse(
            success=result.get("success", False),
            audio_content=result.get("audio_content"),
            audio_bytes=result.get("audio_bytes", 0),
            format=result.get("format", "mp3"),
            voice=result.get("voice"),
            language=result.get("language", request.language_code),
            error=result.get("error"),
        )

    except Exception as e:
        logger.error("Synthesis endpoint error", error=str(e))
        return SynthesisResponse(
            success=False,
            error=str(e),
        )


@router.get("/voices")
async def list_available_voices():
    """List available TTS voices.

    Returns:
        List of available voice configurations
    """
    # Return commonly used Neural2 voices
    voices = [
        {
            "name": "es-MX-Neural2-A",
            "language": "es-MX",
            "gender": "FEMALE",
            "description": "Mexican Spanish, female, neural voice",
        },
        {
            "name": "es-MX-Neural2-B",
            "language": "es-MX",
            "gender": "MALE",
            "description": "Mexican Spanish, male, neural voice",
        },
        {
            "name": "es-ES-Neural2-A",
            "language": "es-ES",
            "gender": "FEMALE",
            "description": "European Spanish, female, neural voice",
        },
        {
            "name": "en-US-Neural2-A",
            "language": "en-US",
            "gender": "FEMALE",
            "description": "US English, female, neural voice",
        },
        {
            "name": "en-US-Neural2-D",
            "language": "en-US",
            "gender": "MALE",
            "description": "US English, male, neural voice",
        },
    ]

    return {
        "voices": voices,
        "supported_languages": ["es-MX", "es-ES", "en-US", "en-GB", "pt-BR"],
        "supported_formats": ["MP3", "LINEAR16", "OGG_OPUS"],
    }


@router.post("/conversation", response_model=VoiceConversationResponse)
async def voice_conversation(request: VoiceConversationRequest) -> VoiceConversationResponse:
    """Handle a complete voice conversation turn.

    Takes audio input, transcribes it, processes with the AI agent,
    and returns both text and audio response.

    Args:
        request: Voice conversation request with audio content

    Returns:
        User transcript, assistant response, and synthesized audio
    """
    try:
        from src.mcp.orchestrator import get_or_create_orchestrator

        audio_service = get_audio_service()
        if not audio_service:
            raise HTTPException(
                status_code=503,
                detail="Audio service not available"
            )

        # 1. Transcribe user audio
        audio_bytes = base64.b64decode(request.audio_content)
        transcription = await audio_service.speech_to_text(
            audio_content=audio_bytes,
            language_code=request.language_code,
        )

        if not transcription.get("success") or not transcription.get("transcript"):
            return VoiceConversationResponse(
                success=False,
                error="Could not transcribe audio. Please try again.",
            )

        user_text = transcription["transcript"]

        # 2. Process with AI agent
        orchestrator = await get_or_create_orchestrator()
        if not orchestrator:
            return VoiceConversationResponse(
                success=False,
                user_transcript=user_text,
                error="AI agent not available",
            )

        # Collect the full response
        response_parts = []
        async for chunk in orchestrator.stream_response(
            user_message=user_text,
            session_id=request.session_id,
        ):
            if chunk.get("type") == "text":
                response_parts.append(chunk.get("content", ""))
            elif chunk.get("type") == "response_complete":
                break

        assistant_response = "".join(response_parts)

        # 3. Synthesize response to speech
        # Clean the response for better TTS (remove markdown formatting)
        clean_response = assistant_response
        clean_response = clean_response.replace("**", "")
        clean_response = clean_response.replace("##", "")
        clean_response = clean_response.replace("- ", "")
        clean_response = clean_response.replace("|", " ")

        synthesis = await audio_service.text_to_speech(
            text=clean_response[:4000],  # Limit length for TTS
            language_code=request.language_code,
            speaking_rate=1.0,
        )

        return VoiceConversationResponse(
            success=True,
            user_transcript=user_text,
            assistant_response=assistant_response,
            response_audio=synthesis.get("audio_content") if synthesis.get("success") else None,
        )

    except Exception as e:
        logger.error("Voice conversation error", error=str(e))
        return VoiceConversationResponse(
            success=False,
            error=str(e),
        )


@router.get("/health")
async def audio_health_check():
    """Check audio service health.

    Returns:
        Health status of audio service
    """
    audio_service = get_audio_service()

    return {
        "status": "healthy" if audio_service else "unavailable",
        "stt_available": audio_service is not None,
        "tts_available": audio_service is not None,
    }
