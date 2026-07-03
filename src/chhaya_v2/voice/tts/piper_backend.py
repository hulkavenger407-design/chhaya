import asyncio
import structlog

logger = structlog.get_logger(__name__)

class PiperTTSBackend:
    """Piper TTS fallback."""
    def __init__(self):
        logger.info("initialized_piper_tts")

    async def speak(self, text: str):
        if not text:
            return

        logger.info("piper_speaking", text=text[:50])
        speak_time = len(text) * 0.05
        await asyncio.sleep(speak_time)
        logger.debug("piper_finished_speaking")
