import asyncio
import structlog
from chhaya_v2.voice.state_machine import VoiceStateMachine, VoiceState
from chhaya_v2.voice.wake_word.detector import WakeWordDetector
from chhaya_v2.voice.stt.whisper_engine import WhisperEngine
from chhaya_v2.voice.tts.melo_backend import MeloTTSBackend
from chhaya_v2.voice.tts.piper_backend import PiperTTSBackend
from chhaya_v2.core.engine.config import settings

logger = structlog.get_logger(__name__)

class VoicePipeline:
    """Orchestrator for the voice interaction loop."""
    def __init__(self):
        self.state_machine = VoiceStateMachine()
        self.detector = WakeWordDetector()
        self.stt = WhisperEngine()

        if settings.tts_backend == "melo":
            self.tts = MeloTTSBackend()
        else:
            self.tts = PiperTTSBackend()

        self._running = False
        self._current_speech_task = None

    async def start(self):
        self._running = True
        logger.info("voice_pipeline_started")

        while self._running:
            self.state_machine.transition(VoiceState.IDLE)

            # 1. Wait for wake word
            detected = await self.detector.listen()
            if not detected:
                continue

            # 2. Wake word detected! Mute output to prevent audio feedback loop
            self.state_machine.transition(VoiceState.MUTED)
            logger.info("audio_feedback_prevented")

            # 3. Listen to user command (Mocked for Phase 2 implementation)
            self.state_machine.transition(VoiceState.LISTENING)
            audio_bytes = await self._capture_audio()

            # 4. Process Speech to Text
            self.state_machine.transition(VoiceState.PROCESSING)
            text = await self.stt.transcribe(audio_bytes)

            if not text:
                continue

            # 5. Get AI Response (Mocked passthrough for pipeline isolation)
            response_text = f"I heard you say: {text}"

            # 6. Speak response
            self.state_machine.transition(VoiceState.SPEAKING)
            self._current_speech_task = asyncio.create_task(self.tts.speak(response_text))

            try:
                await self._current_speech_task
            except asyncio.CancelledError:
                logger.info("speech_interrupted")

            self._current_speech_task = None

    async def _capture_audio(self) -> bytes:
        """Mock audio capture."""
        await asyncio.sleep(1.0)
        return b"mock_audio_data"

    def interrupt(self):
        """Allows user to interrupt JARVIS mid-sentence."""
        if self.state_machine.can_interrupt() and self._current_speech_task:
            self._current_speech_task.cancel()
            self.state_machine.transition(VoiceState.IDLE)

    def stop(self):
        self._running = False
        self.detector.stop()
        if self._current_speech_task:
            self._current_speech_task.cancel()
