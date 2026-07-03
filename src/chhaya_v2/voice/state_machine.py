from enum import Enum, auto
import structlog

logger = structlog.get_logger(__name__)

class VoiceState(Enum):
    IDLE = auto()
    LISTENING = auto()
    PROCESSING = auto()
    SPEAKING = auto()
    MUTED = auto()

class VoiceStateMachine:
    def __init__(self):
        self.state = VoiceState.IDLE

    def transition(self, new_state: VoiceState):
        logger.debug("voice_state_transition", from_state=self.state.name, to_state=new_state.name)
        self.state = new_state

    def can_interrupt(self) -> bool:
        return self.state == VoiceState.SPEAKING
