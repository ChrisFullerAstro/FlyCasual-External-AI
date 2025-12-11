"""Radar tool for situational awareness."""
from pydantic import BaseModel

from xwing_agent.game.simulation import MovementSimulator
from xwing_agent.logging_config import get_logger
from xwing_agent.models.game_state import GameState, Ship

logger = get_logger(__name__)


class RadarContact(BaseModel):
    """A ship detected by radar."""

    ship_id: str
    ship_name: str
    ship_type: str
    is_friendly: bool

    range_band: int
    bearing: str  # "ahead", "ahead-left", "left", "behind-left", etc.
    distance_description: str  # "very close", "close", "medium", "far"

    in_my_arc: bool
    i_am_in_their_arc: bool
    health_status: str  # "healthy", "damaged", "critical"
    threat_level: str  # "none", "low", "medium", "high"


class RadarOutput(BaseModel):
    """Output from radar scan."""

    ship_id: str
    ship_name: str
    my_position: str
    contacts: list[RadarContact]


def _bearing_to_description(bearing: float) -> str:
    """Convert numeric bearing to natural language."""
    bearing = bearing % 360
    if bearing < 22.5 or bearing >= 337.5:
        return "directly ahead"
    elif bearing < 67.5:
        return "ahead-right"
    elif bearing < 112.5:
        return "right"
    elif bearing < 157.5:
        return "behind-right"
    elif bearing < 202.5:
        return "directly behind"
    elif bearing < 247.5:
        return "behind-left"
    elif bearing < 292.5:
        return "left"
    else:
        return "ahead-left"


def _distance_to_description(distance_mm: float) -> str:
    """Convert distance to natural language."""
    if distance_mm < 80:
        return "very close"
    elif distance_mm < 150:
        return "close"
    elif distance_mm < 250:
        return "medium range"
    return "far"


def _health_status(ship: Ship) -> str:
    """Assess health status."""
    pct = ship.health_percentage
    if pct > 0.75:
        return "healthy"
    elif pct > 0.35:
        return "damaged"
    return "critical"


def _describe_position(pos, board_width: float, board_height: float) -> str:
    """Describe a position in natural language."""
    half_w = board_width / 2
    half_h = board_height / 2

    # Horizontal position
    if pos.x < -half_w * 0.3:
        h_pos = "left"
    elif pos.x > half_w * 0.3:
        h_pos = "right"
    else:
        h_pos = "center"

    # Vertical position
    if pos.y > half_h * 0.3:
        v_pos = "upper"
    elif pos.y < -half_h * 0.3:
        v_pos = "lower"
    else:
        v_pos = "middle"

    # Facing
    heading = pos.heading
    if heading < 45 or heading >= 315:
        facing = "facing up"
    elif heading < 135:
        facing = "facing right"
    elif heading < 225:
        facing = "facing down"
    else:
        facing = "facing left"

    if v_pos == "middle" and h_pos == "center":
        return f"board center, {facing}"
    return f"{v_pos}-{h_pos}, {facing}"


class RadarTool:
    """Tool for getting situational awareness."""

    def __init__(self, game_state: GameState, perception_error: float = 0.1):
        self.state = game_state
        self.simulator = MovementSimulator(game_state, perception_error)

    def scan(self, ship_id: str) -> RadarOutput:
        """Get radar scan from a ship's perspective."""
        # Ensure ship_id is a string
        ship_id = str(ship_id)
        logger.info(f"Radar scan for {ship_id}")

        ship = self.state.get_ship(ship_id)
        if ship is None:
            # Log available ships for debugging
            available = [s.id for s in self.state.all_ships]
            logger.error(f"Ship {ship_id} not found. Available: {available}")
            raise ValueError(f"Ship {ship_id} not found")

        contacts = []
        is_mine = ship in self.state.my_ships

        for other in self.state.all_ships:
            if other.id == ship_id or other.is_destroyed:
                continue

            distance = ship.position.distance_to(other.position)
            bearing = ship.position.bearing_to(other.position)
            range_band = self.simulator.get_range_band(distance)

            is_friendly = (other in self.state.my_ships) == is_mine

            in_my_arc = range_band <= 3 and self.simulator.check_arc(
                ship.position, other.position, ship.primary_arc.value
            )
            i_in_their_arc = range_band <= 3 and self.simulator.check_arc(
                other.position, ship.position, other.primary_arc.value
            )

            # Threat assessment
            if is_friendly:
                threat = "none"
            elif i_in_their_arc:
                if range_band == 1 or other.attack >= 4:
                    threat = "high"
                elif range_band == 2:
                    threat = "medium"
                else:
                    threat = "low"
            else:
                threat = "low"

            contacts.append(
                RadarContact(
                    ship_id=other.id,
                    ship_name=other.name,
                    ship_type=other.ship_type,
                    is_friendly=is_friendly,
                    range_band=range_band,
                    bearing=_bearing_to_description(bearing),
                    distance_description=_distance_to_description(distance),
                    in_my_arc=in_my_arc,
                    i_am_in_their_arc=i_in_their_arc,
                    health_status=_health_status(other),
                    threat_level=threat,
                )
            )

        my_position = _describe_position(
            ship.position, self.state.board_width, self.state.board_height
        )

        return RadarOutput(
            ship_id=ship_id,
            ship_name=ship.name,
            my_position=my_position,
            contacts=contacts,
        )
