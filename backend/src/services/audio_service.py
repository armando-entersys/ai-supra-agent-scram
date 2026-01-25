"""Audio service for voice-based AI conversations.

Provides Speech-to-Text (STT) and Text-to-Speech (TTS) capabilities
using Google Cloud services for natural voice interactions.
"""

from typing import Any, AsyncGenerator, Optional
import asyncio
import base64
import structlog
from google.cloud import speech_v1 as speech
from google.cloud import texttospeech_v1 as tts

from src.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


class AudioService:
    """Service for voice-based AI interactions."""

    def __init__(self) -> None:
        """Initialize audio service with Google Cloud clients."""
        self._stt_client: Optional[speech.SpeechAsyncClient] = None
        self._tts_client: Optional[tts.TextToSpeechAsyncClient] = None
        self._initialized = False

    async def _ensure_initialized(self) -> None:
        """Lazily initialize Google Cloud clients."""
        if self._initialized:
            return

        try:
            self._stt_client = speech.SpeechAsyncClient()
            self._tts_client = tts.TextToSpeechAsyncClient()
            self._initialized = True
            logger.info("Audio service initialized successfully")
        except Exception as e:
            logger.error("Failed to initialize audio service", error=str(e))
            raise

    async def speech_to_text(
        self,
        audio_content: bytes,
        language_code: str = "es-MX",
        sample_rate_hertz: int = 16000,
        encoding: str = "LINEAR16",
    ) -> dict[str, Any]:
        """Convert speech audio to text.

        Args:
            audio_content: Raw audio bytes
            language_code: Language code (e.g., 'es-MX', 'en-US')
            sample_rate_hertz: Audio sample rate
            encoding: Audio encoding format

        Returns:
            Dict with transcription and confidence score
        """
        await self._ensure_initialized()

        try:
            # Map encoding string to enum
            encoding_map = {
                "LINEAR16": speech.RecognitionConfig.AudioEncoding.LINEAR16,
                "FLAC": speech.RecognitionConfig.AudioEncoding.FLAC,
                "MP3": speech.RecognitionConfig.AudioEncoding.MP3,
                "WEBM_OPUS": speech.RecognitionConfig.AudioEncoding.WEBM_OPUS,
            }

            config = speech.RecognitionConfig(
                encoding=encoding_map.get(encoding, speech.RecognitionConfig.AudioEncoding.LINEAR16),
                sample_rate_hertz=sample_rate_hertz,
                language_code=language_code,
                enable_automatic_punctuation=True,
                model="latest_long",
                # Enable enhanced features
                use_enhanced=True,
                # Support multiple speakers
                enable_speaker_diarization=False,
                # Alternative transcriptions
                max_alternatives=1,
            )

            audio = speech.RecognitionAudio(content=audio_content)

            response = await self._stt_client.recognize(config=config, audio=audio)

            if not response.results:
                return {
                    "success": True,
                    "transcript": "",
                    "confidence": 0.0,
                    "alternatives": [],
                }

            # Get the best result
            best_result = response.results[0]
            best_alternative = best_result.alternatives[0]

            return {
                "success": True,
                "transcript": best_alternative.transcript,
                "confidence": best_alternative.confidence,
                "alternatives": [
                    {
                        "transcript": alt.transcript,
                        "confidence": alt.confidence,
                    }
                    for alt in best_result.alternatives[1:4]  # Up to 3 alternatives
                ],
            }

        except Exception as e:
            logger.error("Speech-to-text failed", error=str(e))
            return {
                "success": False,
                "error": str(e),
                "transcript": "",
                "confidence": 0.0,
            }

    async def speech_to_text_streaming(
        self,
        audio_stream: AsyncGenerator[bytes, None],
        language_code: str = "es-MX",
        sample_rate_hertz: int = 16000,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Convert streaming speech audio to text in real-time.

        Args:
            audio_stream: Async generator yielding audio chunks
            language_code: Language code
            sample_rate_hertz: Audio sample rate

        Yields:
            Dict with partial and final transcriptions
        """
        await self._ensure_initialized()

        try:
            config = speech.StreamingRecognitionConfig(
                config=speech.RecognitionConfig(
                    encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                    sample_rate_hertz=sample_rate_hertz,
                    language_code=language_code,
                    enable_automatic_punctuation=True,
                ),
                interim_results=True,  # Get partial results
            )

            async def request_generator():
                # First request must contain config only
                yield speech.StreamingRecognizeRequest(streaming_config=config)

                # Subsequent requests contain audio
                async for chunk in audio_stream:
                    yield speech.StreamingRecognizeRequest(audio_content=chunk)

            responses = await self._stt_client.streaming_recognize(
                requests=request_generator()
            )

            async for response in responses:
                for result in response.results:
                    yield {
                        "is_final": result.is_final,
                        "transcript": result.alternatives[0].transcript if result.alternatives else "",
                        "confidence": result.alternatives[0].confidence if result.alternatives else 0.0,
                        "stability": result.stability,
                    }

        except Exception as e:
            logger.error("Streaming speech-to-text failed", error=str(e))
            yield {
                "is_final": True,
                "error": str(e),
                "transcript": "",
                "confidence": 0.0,
            }

    async def text_to_speech(
        self,
        text: str,
        language_code: str = "es-MX",
        voice_name: Optional[str] = None,
        speaking_rate: float = 1.0,
        pitch: float = 0.0,
        audio_encoding: str = "MP3",
    ) -> dict[str, Any]:
        """Convert text to speech audio.

        Args:
            text: Text to synthesize
            language_code: Language code (e.g., 'es-MX', 'en-US')
            voice_name: Specific voice name (e.g., 'es-MX-Neural2-A')
            speaking_rate: Speed of speech (0.25 to 4.0)
            pitch: Voice pitch (-20.0 to 20.0)
            audio_encoding: Output format (MP3, LINEAR16, OGG_OPUS)

        Returns:
            Dict with audio content and metadata
        """
        await self._ensure_initialized()

        try:
            # Set up synthesis input
            synthesis_input = tts.SynthesisInput(text=text)

            # Configure voice
            # Default to Neural2 voices for better quality
            if not voice_name:
                voice_name = self._get_default_voice(language_code)

            voice = tts.VoiceSelectionParams(
                language_code=language_code,
                name=voice_name,
            )

            # Map encoding
            encoding_map = {
                "MP3": tts.AudioEncoding.MP3,
                "LINEAR16": tts.AudioEncoding.LINEAR16,
                "OGG_OPUS": tts.AudioEncoding.OGG_OPUS,
            }

            # Configure audio output
            audio_config = tts.AudioConfig(
                audio_encoding=encoding_map.get(audio_encoding, tts.AudioEncoding.MP3),
                speaking_rate=speaking_rate,
                pitch=pitch,
            )

            # Synthesize speech
            response = await self._tts_client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config,
            )

            return {
                "success": True,
                "audio_content": base64.b64encode(response.audio_content).decode("utf-8"),
                "audio_bytes": len(response.audio_content),
                "format": audio_encoding.lower(),
                "voice": voice_name,
                "language": language_code,
            }

        except Exception as e:
            logger.error("Text-to-speech failed", error=str(e))
            return {
                "success": False,
                "error": str(e),
                "audio_content": None,
            }

    def _get_default_voice(self, language_code: str) -> str:
        """Get the default Neural2 voice for a language."""
        # Map languages to Neural2 voices
        voice_map = {
            "es-MX": "es-MX-Neural2-A",  # Female, Mexican Spanish
            "es-ES": "es-ES-Neural2-A",  # Female, European Spanish
            "en-US": "en-US-Neural2-A",  # Female, US English
            "en-GB": "en-GB-Neural2-A",  # Female, British English
            "pt-BR": "pt-BR-Neural2-A",  # Female, Brazilian Portuguese
        }
        return voice_map.get(language_code, "es-MX-Neural2-A")

    async def detect_language(self, text: str) -> str:
        """Detect the language of input text.

        Args:
            text: Text to analyze

        Returns:
            Language code (e.g., 'es', 'en')
        """
        # Simple heuristic-based detection
        # In production, use Google Cloud Translation API or a proper ML model
        spanish_words = {"el", "la", "de", "que", "y", "en", "un", "es", "los", "las", "por", "con", "para", "como"}
        english_words = {"the", "a", "an", "is", "are", "of", "to", "and", "in", "for", "with", "that", "this"}

        words = set(text.lower().split())

        spanish_count = len(words & spanish_words)
        english_count = len(words & english_words)

        if spanish_count > english_count:
            return "es-MX"
        elif english_count > spanish_count:
            return "en-US"
        else:
            return "es-MX"  # Default to Spanish


# Singleton instance
_audio_service: Optional[AudioService] = None


def get_audio_service() -> Optional[AudioService]:
    """Get or create audio service instance.

    Returns:
        AudioService instance or None if initialization fails
    """
    global _audio_service
    if _audio_service is None:
        try:
            _audio_service = AudioService()
        except Exception as e:
            logger.error("Failed to create audio service", error=str(e))
            return None
    return _audio_service
