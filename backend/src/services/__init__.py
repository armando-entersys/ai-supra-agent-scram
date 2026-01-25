"""AI-SupraAgent Backend Services.

Provides various service modules for the application:
- audio_service: Speech-to-Text and Text-to-Speech capabilities
"""

from src.services.audio_service import AudioService, get_audio_service

__all__ = [
    "AudioService",
    "get_audio_service",
]
