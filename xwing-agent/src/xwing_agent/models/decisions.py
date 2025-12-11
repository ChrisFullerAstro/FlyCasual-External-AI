"""Decision request/response models."""
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class DecisionType(str, Enum):
    PLANNING = "planning"
    ACTION = "action"
    TARGET = "target"
    DICE_MOD = "dice_mod"


class DecisionRequest(BaseModel):
    """Request from FlyCasual for a decision."""

    game_id: str
    session_id: str  # Round session ID
    decision_type: DecisionType

    # Context for the decision
    ship_id: str | None = None  # Ship needing decision (for action/target)
    available_options: list[str] | None = None
    context: dict[str, Any] | None = None  # Dice results, etc.


class ManeuverDecision(BaseModel):
    """Decision for a single ship's maneuver."""

    ship_id: str
    maneuver_code: str
    reasoning: str


class PlanningResponse(BaseModel):
    """Response for planning phase."""

    maneuvers: list[ManeuverDecision]
    strategic_thinking: str


class TargetDecision(BaseModel):
    """Decision for target selection."""

    attacker_id: str
    target_id: str
    weapon: str = "primary"
    reasoning: str


class DiceModDecision(BaseModel):
    """Decision for dice modification."""

    ship_id: str
    modifications: list[str]  # ["spend_focus", "reroll:blank,blank"]
    reasoning: str


class DecisionResponse(BaseModel):
    """Generic response wrapper."""

    decision_type: DecisionType
    success: bool = True
    error: str | None = None

    # One of these populated based on type
    planning: PlanningResponse | None = None
    target: TargetDecision | None = None
    dice_mod: DiceModDecision | None = None

    # Always include thinking trace
    thinking_trace: str = ""
