"""
Tests for Chhaya Voice Interface.
"""

from unittest.mock import patch, AsyncMock, MagicMock
import pytest
import asyncio

from chhaya_v1.interfaces.voice import VoiceInterface
from chhaya_v1.domain.models import AgentBlueprint
from chhaya_v1.core.execution_engine import ExecutionEngine
from chhaya_v1.interfaces.workspace import Workspace


class MockExecutionEngine:
    def run(self, blueprint, task, workspace):
        return "I am responding to your voice command."


class MockWorkspace(Workspace):
    @property
    def base_path(self): return "/tmp"
    def write_file(self, filename: str, content: str): pass
    def read_file(self, filename: str) -> str: return ""


@pytest.fixture
def voice_interface():
    engine = MockExecutionEngine()
    workspace = MockWorkspace()
    # Patch pygame init to avoid sound device errors in CI
    with patch("pygame.mixer.init"):
        interface = VoiceInterface(execution_engine=engine, workspace=workspace)
        return interface


@pytest.mark.asyncio
async def test_voice_interface_speak(voice_interface):
    """Test that the speak method correctly invokes edge-tts and pygame."""
    with patch("edge_tts.Communicate") as mock_communicate, \
         patch("pygame.mixer.music") as mock_music, \
         patch("os.remove") as mock_remove:

        mock_comm_instance = MagicMock()
        mock_comm_instance.save = AsyncMock()
        mock_communicate.return_value = mock_comm_instance

        # Make pygame not busy immediately to avoid infinite loop
        mock_music.get_busy.return_value = False

        await voice_interface._speak("Test speaking")

        mock_communicate.assert_called_once_with("Test speaking", "en-US-AriaNeural")
        mock_comm_instance.save.assert_called_once()
        mock_music.load.assert_called_once()
        mock_music.play.assert_called_once()
        mock_music.unload.assert_called_once()
        mock_remove.assert_called_once()


def test_voice_interface_listen_success(voice_interface):
    """Test that listening successfully returns recognized text."""
    with patch("speech_recognition.Microphone"), \
         patch.object(voice_interface.recognizer, "adjust_for_ambient_noise"), \
         patch.object(voice_interface.recognizer, "listen") as mock_listen, \
         patch.object(voice_interface.recognizer, "recognize_google") as mock_recognize:

        mock_audio = MagicMock()
        mock_listen.return_value = mock_audio
        mock_recognize.return_value = "Hey Chhaya do something"

        result = voice_interface._listen_for_audio()

        assert result == "hey chhaya do something"
        mock_recognize.assert_called_once_with(mock_audio)


def test_voice_interface_listen_timeout(voice_interface):
    """Test that timeouts return None."""
    import speech_recognition as sr
    with patch("speech_recognition.Microphone"), \
         patch.object(voice_interface.recognizer, "adjust_for_ambient_noise"), \
         patch.object(voice_interface.recognizer, "listen", side_effect=sr.WaitTimeoutError):

        result = voice_interface._listen_for_audio()

        assert result is None
