"""
Voice Interface for Chhaya.
Provides wake-word detection and high-quality female TTS using edge-tts.
"""

import asyncio
import os
import tempfile
from typing import Callable, Optional
import structlog
import speech_recognition as sr
import edge_tts
import pygame

from chhaya.core.execution_engine import ExecutionEngine
from chhaya.domain.models import AgentBlueprint, ModelTier, GuardrailLevel
from chhaya.interfaces.workspace import Workspace

logger = structlog.get_logger(__name__)

# We use an extremely high-quality female neural voice from Microsoft Edge
VOICE_MODEL = "en-US-AriaNeural"


class VoiceInterface:
    """
    Handles microphone input, wake-word detection, and TTS output.
    """

    def __init__(self, execution_engine: ExecutionEngine, workspace: Workspace):
        self.execution = execution_engine
        self.workspace = workspace
        self.recognizer = sr.Recognizer()

        # Initialize pygame mixer for audio playback
        pygame.mixer.init()

        # Create a default "Voice Assistant" blueprint on the fly
        self.agent_blueprint = AgentBlueprint(
            name="chhaya_voice_assistant",
            role="A helpful, conversational AI voice assistant named Chhaya.",
            system_prompt="You are Chhaya, a friendly and highly capable AI assistant. Provide concise, helpful answers suitable for text-to-speech spoken audio. Do not use markdown, emojis, or code blocks in your responses.",
            model_tier=ModelTier.EXECUTION_7B, # Fast execution for voice
            guardrail_level=GuardrailLevel.RELAXED,
            tools=[]
        )

    async def _speak(self, text: str):
        """
        Synthesizes text to speech using edge-tts and plays it.
        """
        logger.info("Chhaya speaking", text=text)

        try:
            communicate = edge_tts.Communicate(text, VOICE_MODEL)

            # Save to a temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
                temp_filename = fp.name

            await communicate.save(temp_filename)

            # Play the audio
            pygame.mixer.music.load(temp_filename)
            pygame.mixer.music.play()

            # Wait for playback to finish
            while pygame.mixer.music.get_busy():
                await asyncio.sleep(0.1)

            # Cleanup
            pygame.mixer.music.unload()
            os.remove(temp_filename)

        except Exception as e:
            logger.error("TTS synthesis/playback failed", error=str(e))

    def _listen_for_audio(self, prompt_text: Optional[str] = None) -> Optional[str]:
        """
        Listens to the microphone and returns the transcribed text.
        """
        with sr.Microphone() as source:
            if prompt_text:
                print(f"\n🎙️  {prompt_text}")

            # Adjust for ambient noise
            self.recognizer.adjust_for_ambient_noise(source, duration=0.5)

            try:
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
                text = self.recognizer.recognize_google(audio).lower()
                return text
            except sr.WaitTimeoutError:
                return None
            except sr.UnknownValueError:
                return None
            except sr.RequestError as e:
                logger.error("Speech recognition service error", error=str(e))
                return None
            except Exception as e:
                logger.error("Audio capture failed", error=str(e))
                return None

    async def start_loop(self):
        """
        Starts the continuous wake-word listening loop.
        """
        print("\n" + "="*50)
        print("🔊 Chhaya Voice Interface Active")
        print("Say 'hey chhaya' or 'chhaya' to wake me up.")
        print("Press Ctrl+C to exit.")
        print("="*50 + "\n")

        try:
            while True:
                # 1. Listen for wake word
                wake_text = self._listen_for_audio("Listening for wake word...")

                if wake_text and ("hey chhaya" in wake_text or "chhaya" in wake_text):
                    print("✨ Wake word detected!")
                    await self._speak("I'm listening.")

                    # 2. Listen for actual command
                    command_text = self._listen_for_audio("What do you need?")

                    if command_text:
                        print(f"🗣️  You said: {command_text}")

                        # 3. Execute through the Chhaya core
                        try:
                            # Run synchronously in this loop (in a real prod app, you might thread this)
                            response = self.execution.run(
                                blueprint=self.agent_blueprint,
                                task=command_text,
                                workspace=self.workspace
                            )

                            print(f"🤖 Chhaya: {response}")
                            # 4. Speak response
                            await self._speak(response)

                        except Exception as e:
                            logger.error("Agent execution failed during voice loop", error=str(e))
                            await self._speak("I'm sorry, I encountered an error while processing that.")
                    else:
                        await self._speak("I didn't catch that. Going back to sleep.")

                # Small sleep to prevent aggressive CPU spinning if errors occur
                await asyncio.sleep(0.1)

        except KeyboardInterrupt:
            print("\nShutting down voice interface.")
        finally:
            pygame.mixer.quit()
