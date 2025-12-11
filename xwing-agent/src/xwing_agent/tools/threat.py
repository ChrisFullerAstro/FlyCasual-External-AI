"""Threat assessment tool."""
from pydantic import BaseModel

from xwing_agent.game.simulation import MovementSimulator
from xwing_agent.logging_config import get_logger
from xwing_agent.models.game_state import GameState

logger = get_logger(__name__)


class IncomingThreat(BaseModel):
    """Details of an enemy that can shoot this ship."""

    ship_id: str
    ship_name: str
    range_band: int
    attack_dice: int
    in_bullseye: bool
    has_lock: bool
    has_focus: bool


class ThreatOutput(BaseModel):
    """Threat assessment output."""

    ship_id: str
    ship_name: str

    # Defense stats
    my_agility: int
    my_tokens: list[str]
    my_defense_estimate: int

    # Incoming fire
    threats: list[IncomingThreat]
    total_incoming_dice: int

    # Assessment
    threat_level: str  # "safe", "low", "medium", "high", "critical"
    survival_estimate: str
    recommendation: str


class ThreatTool:
    """Tool for assessing threat to a ship."""

    def __init__(self, game_state: GameState, perception_error: float = 0.1):
        self.state = game_state
        self.simulator = MovementSimulator(game_state, perception_error)

    def assess(self, ship_id: str) -> ThreatOutput:
        """Assess current threat level to a ship."""
        # Ensure ship_id is a string
        ship_id = str(ship_id)
        logger.info(f"Threat assessment for {ship_id}")

        ship = self.state.get_ship(ship_id)
        if ship is None:
            available = [s.id for s in self.state.all_ships]
            logger.error(f"Ship {ship_id} not found. Available: {available}")
            raise ValueError(f"Ship {ship_id} not found")

        threats = []
        total_dice = 0

        for enemy in self.state.get_active_ships(mine=False):
            distance = ship.position.distance_to(enemy.position)
            range_band = self.simulator.get_range_band(distance)

            # Check if enemy can shoot us
            if range_band > 3:
                continue
            if not self.simulator.check_arc(
                enemy.position, ship.position, enemy.primary_arc.value
            ):
                continue

            # Calculate attack dice
            dice = enemy.attack
            if range_band == 1:
                dice += 1

            # Check bullseye
            bearing = enemy.position.bearing_to(ship.position)
            in_bullseye = bearing <= 5 or bearing >= 355

            # Check tokens
            has_lock = any(t.startswith(f"lock:{ship.id}") for t in enemy.tokens)
            has_focus = enemy.has_token("focus")

            threats.append(
                IncomingThreat(
                    ship_id=enemy.id,
                    ship_name=enemy.name,
                    range_band=range_band,
                    attack_dice=dice,
                    in_bullseye=in_bullseye,
                    has_lock=has_lock,
                    has_focus=has_focus,
                )
            )
            total_dice += dice

        # Defense estimate
        defense = ship.agility
        if any(t.range_band == 3 for t in threats):
            defense += 1  # Range 3 bonus

        # Threat level
        if total_dice == 0:
            threat_level = "safe"
            survival = "Not under fire"
            recommendation = "Focus on offensive positioning"
        elif total_dice <= defense:
            threat_level = "low"
            survival = "Should survive with light damage"
            recommendation = "Standard token usage"
        elif total_dice <= defense + 2:
            threat_level = "medium"
            survival = "Likely to take some damage"
            recommendation = "Prioritize defensive tokens"
        elif total_dice <= defense + 4:
            threat_level = "high"
            survival = "Significant damage expected"
            recommendation = "Consider disengaging"
        else:
            threat_level = "critical"
            survival = "May not survive"
            recommendation = "Disengage immediately"

        return ThreatOutput(
            ship_id=ship_id,
            ship_name=ship.name,
            my_agility=ship.agility,
            my_tokens=ship.tokens,
            my_defense_estimate=defense,
            threats=threats,
            total_incoming_dice=total_dice,
            threat_level=threat_level,
            survival_estimate=survival,
            recommendation=recommendation,
        )
