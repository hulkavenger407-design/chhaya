import pytest
import asyncio
from chhaya_v2.voice.pipeline import VoicePipeline
from chhaya_v2.voice.state_machine import VoiceState

@pytest.mark.asyncio
async def test_pipeline_interrupt():
    pipeline = VoicePipeline()

    # Simulate being in speaking state
    pipeline.state_machine.transition(VoiceState.SPEAKING)

    async def dummy_speak():
        await asyncio.sleep(10)

    pipeline._current_speech_task = asyncio.create_task(dummy_speak())

    # Interrupt
    pipeline.interrupt()

    # Give the event loop a tiny slice to actually mark the task as cancelled
    await asyncio.sleep(0.01)

    # Task should be cancelled and state returned to IDLE
    assert pipeline._current_speech_task.cancelled()
    assert pipeline.state_machine.state == VoiceState.IDLE

@pytest.mark.asyncio
async def test_wake_word_stop():
    pipeline = VoicePipeline()

    task = asyncio.create_task(pipeline.detector.listen())
    # give it a tiny bit of time to start
    await asyncio.sleep(0.01)

    assert pipeline.detector.is_listening

    pipeline.stop()
    assert not pipeline.detector.is_listening

    # Wait for task to finish returning False
    res = await task
    assert res is False
