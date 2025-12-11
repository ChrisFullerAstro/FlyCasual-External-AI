"""Maneuver simulation tool."""
from pydantic import BaseModel

from xwing_agent.game.simulation import MovementSimulator
from xwing_agent.logging_config import get_logger
from xwing_agent.models.game_state import GameState

logger = get_logger(__name__)


class ManeuverAnalysis(BaseModel):
    """Analysis of a simulated maneuver."""

    maneuver: str

    # Position result
    end_position_description: str

    # Safety
    collision_risk: str  # "none", "possible", "likely", "certain"
    collision_details: list[str]
    would_flee_board: bool

    # Tactical outcome
    stress_after: int
    enemies_in_arc: list[str]
    enemies_can_shoot_me: list[str]
    range_summary: dict[str, int]

    # Overall assessment
    offensive_score: str  # "excellent", "good", "poor", "none"
    defensive_score: str  # "safe", "risky", "dangerous"
    assessment: str


class SimulationOutput(BaseModel):
    """Output from simulating maneuvers."""

    ship_id: str
    analyses: list[ManeuverAnalysis]


def _describe_position(pos, board_width: float, board_height: float) -> str:
    """Describe end position."""
    half_w = board_width / 2
    half_h = board_height / 2

    if pos.x < -half_w * 0.3:
        h = "left"
    elif pos.x > half_w * 0.3:
        h = "right"
    else:
        h = "center"

    if pos.y > half_h * 0.3:
        v = "upper"
    elif pos.y < -half_h * 0.3:
        v = "lower"
    else:
        v = "mid"

    heading = pos.heading
    if heading < 45 or heading >= 315:
        facing = "up"
    elif heading < 135:
        facing = "right"
    elif heading < 225:
        facing = "down"
    else:
        facing = "left"

    return f"{v}-{h}, facing {facing}"


class SimulateTool:
    """Tool for simulating maneuvers."""

    def __init__(self, game_state: GameState, perception_error: float = 0.1):
        self.state = game_state
        self.simulator = MovementSimulator(game_state, perception_error)

    def simulate(self, ship_id: str, maneuver_codes: list[str]) -> SimulationOutput:
        """Simulate specific maneuvers for a ship."""
        # Ensure ship_id is a string
        ship_id = str(ship_id)
        logger.info(f"Simulating {maneuver_codes} for {ship_id}")

        ship = self.state.get_ship(ship_id)
        if ship is None:
            available = [s.id for s in self.state.all_ships]
            logger.error(f"Ship {ship_id} not found. Available: {available}")
            raise ValueError(f"Ship {ship_id} not found")

        analyses = []

        for code in maneuver_codes:
            maneuver = ship.get_maneuver(code)
            if maneuver is None:
                logger.warning(f"Maneuver {code} not available for {ship_id}")
                continue

            result = self.simulator.simulate_maneuver(ship, maneuver)

            # Collision risk level
            if not result.would_collide:
                collision_risk = "none"
            elif result.would_flee:
                collision_risk = "certain - would flee!"
            elif len(result.collision_with) > 1:
                collision_risk = "likely"
            else:
                collision_risk = "possible"

            # Offensive score
            if len(result.enemies_in_arc) >= 2:
                offensive = "excellent"
            elif len(result.enemies_in_arc) == 1:
                offensive = "good"
            elif any(r <= 2 for r in result.range_to_enemies.values()):
                offensive = "poor"
            else:
                offensive = "none"

            # Defensive score
            if result.would_flee:
                defensive = "dangerous"
            elif len(result.enemies_can_shoot_me) >= 2:
                defensive = "dangerous"
            elif len(result.enemies_can_shoot_me) == 1:
                defensive = "risky"
            else:
                defensive = "safe"

            # Build assessment
            parts = []
            if result.enemies_in_arc:
                parts.append(f"shots on {len(result.enemies_in_arc)} enemies")
            else:
                parts.append("no shots")

            if result.enemies_can_shoot_me:
                parts.append(f"{len(result.enemies_can_shoot_me)} can shoot back")

            if result.would_flee:
                parts.append("WOULD FLEE BOARD")
            elif collision_risk != "none":
                parts.append(f"collision: {collision_risk}")

            if result.stress_after > ship.stress:
                parts.append("gains stress")
            elif result.stress_after < ship.stress:
                parts.append("clears stress")

            analyses.append(
                ManeuverAnalysis(
                    maneuver=code,
                    end_position_description=_describe_position(
                        result.end_position,
                        self.state.board_width,
                        self.state.board_height,
                    ),
                    collision_risk=collision_risk,
                    collision_details=result.collision_with,
                    would_flee_board=result.would_flee,
                    stress_after=result.stress_after,
                    enemies_in_arc=result.enemies_in_arc,
                    enemies_can_shoot_me=result.enemies_can_shoot_me,
                    range_summary=result.range_to_enemies,
                    offensive_score=offensive,
                    defensive_score=defensive,
                    assessment="; ".join(parts),
                )
            )

        return SimulationOutput(ship_id=ship_id, analyses=analyses)
