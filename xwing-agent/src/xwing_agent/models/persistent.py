"""Models that persist across rounds."""
from pydantic import BaseModel, Field


class StrategicPlan(BaseModel):
    """
    Created at game start, updated after each round.

    This is the AI's high-level game plan that evolves as the
    game progresses and it learns about the opponent.
    """

    # Initial analysis (set once at game start)
    initial_analysis: str = Field(description="Initial assessment of both squads and matchup")
    my_squad_strengths: list[str] = Field(default_factory=list)
    my_squad_weaknesses: list[str] = Field(default_factory=list)
    enemy_threats: list[str] = Field(
        default_factory=list, description="Key threats in enemy squad to watch"
    )

    # Current strategy (updated each round)
    win_condition: str = Field(
        description="How we plan to win: destroy_ace, attrition, half_points, time"
    )
    target_priority: list[str] = Field(description="Ship IDs in priority order for targeting")
    engagement_style: str = Field(description="aggressive, defensive, flanking, jousting")
    ship_roles: dict[str, str] = Field(
        default_factory=dict, description="ship_id -> role (ace, blocker, flanker, support)"
    )

    # Living adjustments (accumulated over rounds)
    adjustments: list[str] = Field(
        default_factory=list, description="Strategic adjustments made during the game"
    )

    # Opponent patterns observed
    opponent_tendencies: str = Field(
        default="Unknown - observing", description="What we've learned about how opponent plays"
    )

    # Metadata
    created_turn: int = 1
    last_updated_turn: int = 1


class ShipSnapshot(BaseModel):
    """Snapshot of a ship's state for round summary."""

    ship_id: str
    ship_name: str
    position_description: str  # Natural language: "upper-left, facing right"
    hull: int
    shields: int
    stress: int
    tokens: list[str]
    is_destroyed: bool = False


class RoundSummary(BaseModel):
    """
    Produced at end of each round.

    Only the LAST round's summary is loaded into the next round's
    context to keep things compact.
    """

    round_number: int

    # Board state snapshot (natural language, not coordinates)
    my_ships: list[ShipSnapshot]
    enemy_ships: list[ShipSnapshot]
    position_summary: str = Field(
        description="High-level description: 'Vader center, TIEs flanking left'"
    )

    # What happened this round
    maneuvers_executed: dict[str, str] = Field(
        default_factory=dict, description="ship_id -> maneuver code"
    )
    damage_events: list[str] = Field(
        default_factory=list, description="'Vader dealt 2 damage to Luke'"
    )
    ships_destroyed: list[str] = Field(default_factory=list)
    notable_events: list[str] = Field(
        default_factory=list,
        description="'Luke used Force to evade crit', 'TIE blocked X-Wing'",
    )

    # Assessment
    what_went_well: str
    what_went_poorly: str
    enemy_patterns_observed: str = Field(
        description="'Enemy is jousting', 'Luke always banks left'"
    )

    # Forward-looking
    next_round_priorities: list[str]
    strategic_adjustments: list[str] = Field(
        default_factory=list, description="Adjustments to apply to StrategicPlan"
    )


class RoundEndOutput(BaseModel):
    """Structured output from end-of-round analysis."""

    round_summary: RoundSummary
    strategic_adjustments: list[str]
    updated_target_priority: list[str] | None = None
    updated_engagement_style: str | None = None
