"""
jarvis/voice/voice_pipeline.py

Complete voice pipeline for JARVIS:
  1. Wake word detection: OpenWakeWord — listens for "JARVIS" or "Hey JARVIS"
  2. Speech-to-text: Faster-Whisper (local, offline)
  3. Text-to-speech: Piper TTS (local, offline) — fast, natural voice

All processing is offline — no cloud APIs needed.
The pipeline runs in a background thread and calls a callback with transcribed text.
"""

import os
import sys
import queue
import threading
import tempfile
import time
from pathlib import Path
from typing import Callable, Optional


# ── Voice config ───────────────────────────────────────────────
SAMPLE_RATE      = 16000
WAKE_WORDS       = ["jarvis", "hey jarvis"]
SILENCE_TIMEOUT  = 2.0   # seconds of silence before ending utterance
MAX_RECORD_SECS  = 30    # max utterance length

# Piper TTS voice (download from: https://rhasspy.github.io/piper-samples/)
PIPER_MODEL      = "en_US-amy-medium"
PIPER_EXE        = r"C:\JARVIS_v1_AgentCore\JARVIS\piper\piper.exe"
PIPER_MODEL_PATH = r"C:\JARVIS_v1_AgentCore\JARVIS\piper\voices\en_US-amy-medium.onnx"


class VoicePipeline:
    """Full voice pipeline — wake word → STT → TTS."""

    def __init__(self, on_wake_word: Callable[[str], None] = None):
        """
        on_wake_word: callback(transcribed_text) called when wake word is
                      detected and the user has finished speaking.
        """
        self.on_wake_word = on_wake_word
        self._running     = False
        self._thread: Optional[threading.Thread] = None
        self._tts_queue: queue.Queue = queue.Queue()
        self._tts_thread: Optional[threading.Thread] = None

        self.stt_model  = None   # Loaded lazily
        self.oww_model  = None   # OpenWakeWord model

    # ── STT ────────────────────────────────────────────────────

    def _load_stt(self):
        """Load Faster-Whisper model (first call downloads ~150MB)."""
        if self.stt_model is None:
            try:
                from faster_whisper import WhisperModel
                print("  [Voice] Loading Whisper (base.en)...")
                self.stt_model = WhisperModel(
                    "base.en",
                    device="auto",         # uses CUDA if available, else CPU
                    compute_type="int8"    # quantized — fast on CPU
                )
                print("  [Voice] Whisper loaded.")
            except ImportError:
                print("  [Voice] faster-whisper not installed. Run: pip install faster-whisper")
                self.stt_model = None

    def transcribe(self, audio_path: str) -> str:
        """Transcribe a WAV file to text."""
        self._load_stt()
        if self.stt_model is None:
            return ""
        try:
            segments, _ = self.stt_model.transcribe(
                audio_path, language="en",
                vad_filter=True,
                vad_parameters={"min_silence_duration_ms": 500}
            )
            text = " ".join(seg.text.strip() for seg in segments)
            return text.strip()
        except Exception as e:
            print(f"  [Voice] STT error: {e}")
            return ""

    # ── TTS ────────────────────────────────────────────────────

    def speak(self, text: str):
        """Speak text. Non-blocking — queues to TTS thread."""
        self._tts_queue.put(text)

    def speak_sync(self, text: str):
        """Speak text synchronously (blocks until done)."""
        self._speak_piper(text)

    def _speak_piper(self, text: str):
        """Use Piper to speak text. Falls back to pyttsx3."""
        piper_exe = Path(PIPER_EXE)
        model     = Path(PIPER_MODEL_PATH)

        if piper_exe.exists() and model.exists():
            try:
                import subprocess
                import tempfile
                tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
                tmp.close()
                cmd = [
                    str(piper_exe), "--model", str(model),
                    "--output_file", tmp.name
                ]
                proc = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                proc.communicate(input=text.encode())
                # Play the wav
                import winsound
                winsound.PlaySound(tmp.name, winsound.SND_FILENAME)
                os.unlink(tmp.name)
                return
            except Exception as e:
                print(f"  [Voice] Piper TTS failed: {e} — falling back to pyttsx3")

        # Fallback: pyttsx3
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.setProperty("rate", 175)
            engine.setProperty("volume", 1.0)
            voices = engine.getProperty("voices")
            # Try to pick a female voice for JARVIS
            for v in voices:
                if "zira" in v.name.lower() or "female" in v.name.lower():
                    engine.setProperty("voice", v.id)
                    break
            engine.say(text)
            engine.runAndWait()
        except Exception as e:
            print(f"  [Voice] pyttsx3 TTS failed: {e}")

    def _tts_worker(self):
        """Background thread draining the TTS queue."""
        while self._running:
            try:
                text = self._tts_queue.get(timeout=0.5)
                self._speak_piper(text)
                self._tts_queue.task_done()
            except queue.Empty:
                continue

    # ── Wake word + recording ──────────────────────────────────

    def _load_oww(self):
        """Load OpenWakeWord model."""
        if self.oww_model is None:
            try:
                from openwakeword.model import Model
                print("  [Voice] Loading OpenWakeWord...")
                self.oww_model = Model(
                    wakeword_models=["hey_jarvis"],
                    inference_framework="onnx"
                )
                print("  [Voice] Wake word model ready.")
            except ImportError:
                print("  [Voice] openwakeword not installed. Run: pip install openwakeword")
                self.oww_model = None
            except Exception as e:
                print(f"  [Voice] OpenWakeWord load failed: {e}")
                self.oww_model = None

    def _record_utterance(self) -> str:
        """
        Record audio after wake word until silence.
        Returns path to WAV file.
        """
        try:
            import sounddevice as sd
            import soundfile as sf
            import numpy as np

            print("  [Voice] 🎙️  Listening...")
            self.speak_sync("Yes Sir?")

            chunks = []
            silence_start = None

            def callback(indata, frames, time_info, status):
                nonlocal silence_start
                chunks.append(indata.copy())
                rms = np.sqrt(np.mean(indata**2))
                if rms < 0.01:
                    if silence_start is None:
                        silence_start = time.time()
                else:
                    silence_start = None

            with sd.InputStream(samplerate=SAMPLE_RATE, channels=1,
                                dtype="float32", callback=callback):
                start = time.time()
                while True:
                    time.sleep(0.1)
                    if silence_start and (time.time() - silence_start) > SILENCE_TIMEOUT:
                        break
                    if (time.time() - start) > MAX_RECORD_SECS:
                        break

            audio = np.concatenate(chunks, axis=0)
            tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            sf.write(tmp.name, audio, SAMPLE_RATE)
            return tmp.name
        except Exception as e:
            print(f"  [Voice] Recording error: {e}")
            return ""

    def _listen_loop(self):
        """
        Main voice loop — constantly listens for wake word,
        then records and transcribes user command.
        """
        self._load_oww()
        self._load_stt()

        if self.oww_model is None:
            print("  [Voice] Wake word model unavailable — voice disabled.")
            return

        try:
            import sounddevice as sd
            import numpy as np
        except ImportError:
            print("  [Voice] sounddevice not installed. Run: pip install sounddevice soundfile")
            return

        chunk_size = int(SAMPLE_RATE * 0.08)  # 80ms chunks
        print("  [Voice] Listening for wake word 'JARVIS'...")

        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1,
                            dtype="int16") as stream:
            while self._running:
                try:
                    audio_chunk, _ = stream.read(chunk_size)
                    prediction = self.oww_model.predict(audio_chunk.flatten())

                    # Check if any wake word score exceeds threshold
                    activated = any(
                        score > 0.5
                        for scores in prediction.values()
                        for score in (scores if isinstance(scores, (list, tuple)) else [scores])
                    )

                    if activated:
                        print("  [Voice] Wake word detected!")
                        wav_path = self._record_utterance()
                        if wav_path:
                            text = self.transcribe(wav_path)
                            try:
                                os.unlink(wav_path)
                            except Exception:
                                pass
                            if text and self.on_wake_word:
                                print(f"  [Voice] Heard: '{text}'")
                                self.on_wake_word(text)
                        # Reset wake word model state
                        self.oww_model.reset()
                except Exception as e:
                    if self._running:
                        print(f"  [Voice] Loop error: {e}")
                    time.sleep(0.5)

    # ── Public control ─────────────────────────────────────────

    def start(self):
        """Start voice pipeline in background threads."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()
        self._tts_thread = threading.Thread(target=self._tts_worker, daemon=True)
        self._tts_thread.start()
        print("  [Voice] Pipeline started.")

    def stop(self):
        """Stop voice pipeline."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        if self._tts_thread:
            self._tts_thread.join(timeout=2)
        print("  [Voice] Pipeline stopped.")


# Singleton
_pipeline: Optional[VoicePipeline] = None

def get_voice_pipeline(callback: Callable = None) -> VoicePipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = VoicePipeline(on_wake_word=callback)
    elif callback:
        _pipeline.on_wake_word = callback
    return _pipeline
