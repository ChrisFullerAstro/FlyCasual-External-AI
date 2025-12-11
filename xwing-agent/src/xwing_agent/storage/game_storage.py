"""Persistent storage for game data."""
import json
import shutil
from pathlib import Path

from xwing_agent.config import get_settings
from xwing_agent.logging_config import get_logger
from xwing_agent.models.persistent import RoundSummary, StrategicPlan

logger = get_logger(__name__)
settings = get_settings()


class GameStorage:
    """Stores and retrieves game data (plans, summaries)."""

    def __init__(self, game_id: str):
        self.game_id = game_id
        self.game_dir = settings.storage_path / game_id
        self.game_dir.mkdir(parents=True, exist_ok=True)

    @property
    def plan_path(self) -> Path:
        return self.game_dir / "strategic_plan.json"

    @property
    def summary_path(self) -> Path:
        return self.game_dir / "last_round_summary.json"

    def save_plan(self, plan: StrategicPlan):
        """Save the strategic plan."""
        self.plan_path.write_text(plan.model_dump_json(indent=2))
        logger.info(f"Saved strategic plan for game {self.game_id}")

    def load_plan(self) -> StrategicPlan | None:
        """Load the strategic plan."""
        if not self.plan_path.exists():
            return None
        data = json.loads(self.plan_path.read_text())
        return StrategicPlan.model_validate(data)

    def save_summary(self, summary: RoundSummary):
        """Save the round summary (replaces previous)."""
        self.summary_path.write_text(summary.model_dump_json(indent=2))
        logger.info(f"Saved round {summary.round_number} summary for game {self.game_id}")

    def load_summary(self) -> RoundSummary | None:
        """Load the last round summary."""
        if not self.summary_path.exists():
            return None
        data = json.loads(self.summary_path.read_text())
        return RoundSummary.model_validate(data)

    def clear(self):
        """Clear all game data."""
        if self.game_dir.exists():
            shutil.rmtree(self.game_dir)
            logger.info(f"Cleared game data for {self.game_id}")
