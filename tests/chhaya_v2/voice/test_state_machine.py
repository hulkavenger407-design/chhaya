from chhaya_v2.voice.state_machine import VoiceStateMachine, VoiceState

def test_voice_state_transitions():
    sm = VoiceStateMachine()
    assert sm.state == VoiceState.IDLE

    sm.transition(VoiceState.LISTENING)
    assert sm.state == VoiceState.LISTENING
    assert not sm.can_interrupt()

    sm.transition(VoiceState.SPEAKING)
    assert sm.state == VoiceState.SPEAKING
    assert sm.can_interrupt()
