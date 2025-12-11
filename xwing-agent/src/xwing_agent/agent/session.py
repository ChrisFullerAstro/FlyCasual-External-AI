"""Round session management."""
import uuid

from xwing_agent.agent.round_agent import RoundAgent
from xwing_agent.config import get_settings
from xwing_agent.logging_config import get_logger
from xwing_agent.models.game_state import GameState
from xwing_agent.models.persistent import RoundSummary, StrategicPlan
from xwing_agent.tools.radar import RadarTool
from xwing_agent.tools.simulate import SimulateTool
from xwing_agent.tools.threat import ThreatTool

logger = get_logger(__name__)


class RoundSession:
    """
    Manages a round agent session.

    The session lives for one round and tracks the agent instance.
    """

    def __init__(
        self,
        session_id: str,
        game_id: str,
        round_number: int,
        game_state: GameState,
        strategic_plan: StrategicPlan,
        last_summary: RoundSummary | None,
    ):
        self.session_id = session_id
        self.game_id = game_id
        self.round_number = round_number

        # Create the round agent
        self.agent = RoundAgent(
            game_state=game_state,
            strategic_plan=strategic_plan,
            last_round_summary=last_summary,
        )

        logger.info(f"Created round session {session_id} for game {game_id} round {round_number}")

    def update_state(self, game_state: GameState):
        """Update the game state (e.g., after movement)."""
        self.agent.state = game_state

        # Also update tools with new state
        settings = get_settings()
        self.agent.radar = RadarTool(game_state, settings.perception_error)
        self.agent.simulate = SimulateTool(game_state, settings.perception_error)
        self.agent.threat = ThreatTool(game_state, settings.perception_error)


class SessionManager:
    """Manages active round sessions."""

    def __init__(self):
        self._sessions: dict[str, RoundSession] = {}

    def create_session(
        self,
        game_id: str,
        round_number: int,
        game_state: GameState,
        strategic_plan: StrategicPlan,
        last_summary: RoundSummary | None,
    ) -> RoundSession:
        """Create a new round session."""
        session_id = str(uuid.uuid4())

        session = RoundSession(
            session_id=session_id,
            game_id=game_id,
            round_number=round_number,
            game_state=game_state,
            strategic_plan=strategic_plan,
            last_summary=last_summary,
        )

        self._sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> RoundSession | None:
        """Get an existing session."""
        return self._sessions.get(session_id)

    def end_session(self, session_id: str):
        """Remove a session."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.info(f"Ended session {session_id}")
