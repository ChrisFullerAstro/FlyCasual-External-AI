"""Movement simulation for predicting positions."""
import math
import random
from dataclasses import dataclass

from xwing_agent.game.templates import get_template
from xwing_agent.logging_config import get_logger
from xwing_agent.models.game_state import GameState, Maneuver, Position, Ship

logger = get_logger(__name__)


@dataclass
class SimulationResult:
    """Result of simulating a maneuver."""

    maneuver_code: str
    start_position: Position
    end_position: Position

    # Collision info
    would_collide: bool
    collision_with: list[str]
    would_flee: bool

    # Tactical situation after
    stress_after: int
    enemies_in_arc: list[str]
    enemies_can_shoot_me: list[str]
    range_to_enemies: dict[str, int]


class MovementSimulator:
    """Simulates ship movement and analyzes results."""

    def __init__(self, game_state: GameState, perception_error: float = 0.0):
        self.state = game_state
        self.perception_error = perception_error
        self._rng = random.Random()

    def _add_error(self, value: float) -> float:
        if self.perception_error <= 0:
            return value
        error = self._rng.gauss(0, value * self.perception_error)
        return value + error

    def calculate_end_position(
        self,
        start: Position,
        maneuver: Maneuver,
        add_error: bool = True,
    ) -> Position:
        """Calculate where a ship ends after a maneuver."""
        template = get_template(maneuver.type, maneuver.speed)
        if template is None:
            return start

        # For curved moves, use midpoint heading
        if template.rotation not in (0, 180):
            mid_heading = start.heading + (template.rotation / 2)
        else:
            mid_heading = start.heading

        move_angle = math.radians(mid_heading)
        distance = self._add_error(template.distance) if add_error else template.distance

        new_x = start.x + distance * math.sin(move_angle)
        new_y = start.y + distance * math.cos(move_angle)
        new_heading = (start.heading + template.rotation) % 360

        if add_error:
            new_x = self._add_error(new_x)
            new_y = self._add_error(new_y)

        return Position(x=new_x, y=new_y, heading=new_heading)

    def check_collisions(
        self, position: Position, base_size_mm: float = 40.0
    ) -> tuple[bool, list[str], bool]:
        """Check for collisions. Returns (has_collision, what_with, would_flee)."""
        collisions = []
        half_base = base_size_mm / 2
        half_width = self.state.board_width / 2
        half_height = self.state.board_height / 2

        # Board edges
        if (
            position.x - half_base < -half_width
            or position.x + half_base > half_width
            or position.y - half_base < -half_height
            or position.y + half_base > half_height
        ):
            collisions.append("board_edge")

        # Obstacles
        for obs in self.state.obstacles:
            if position.distance_to(obs.position) < (obs.radius + half_base):
                collisions.append(f"obstacle:{obs.id}")

        # Other ships
        for ship in self.state.all_ships:
            dist = position.distance_to(ship.position)
            min_dist = (base_size_mm + ship.base_size_mm) / 2
            if dist < min_dist:
                collisions.append(f"ship:{ship.id}")

        return len(collisions) > 0, collisions, "board_edge" in collisions

    def get_range_band(self, distance_mm: float) -> int:
        """Convert mm distance to range band (1, 2, 3, or 4 for beyond)."""
        if distance_mm <= 100:
            return 1
        elif distance_mm <= 200:
            return 2
        elif distance_mm <= 300:
            return 3
        return 4

    def check_arc(self, shooter: Position, target: Position, arc_type: str = "front") -> bool:
        """Check if target is in shooter's arc."""
        bearing = shooter.bearing_to(target)

        if arc_type == "front":
            return bearing <= 40 or bearing >= 320
        elif arc_type == "turret":
            return True
        elif arc_type == "rear":
            return 140 <= bearing <= 220
        elif arc_type == "full_front":
            return bearing <= 90 or bearing >= 270
        elif arc_type == "bullseye":
            return bearing <= 5 or bearing >= 355
        return False

    def simulate_maneuver(self, ship: Ship, maneuver: Maneuver) -> SimulationResult:
        """Simulate a maneuver and analyze the result."""
        end_pos = self.calculate_end_position(ship.position, maneuver)
        has_collision, collision_with, would_flee = self.check_collisions(
            end_pos, ship.base_size_mm
        )

        # Calculate stress
        stress_after = ship.stress
        if maneuver.is_red:
            stress_after += 1
        elif maneuver.removes_stress and stress_after > 0:
            stress_after -= 1

        # Analyze tactical situation
        enemies_in_arc = []
        enemies_can_shoot = []
        range_to_enemies = {}

        for enemy in self.state.get_active_ships(mine=False):
            dist = end_pos.distance_to(enemy.position)
            range_band = self.get_range_band(self._add_error(dist))
            range_to_enemies[enemy.id] = range_band

            if range_band <= 3 and self.check_arc(
                end_pos, enemy.position, ship.primary_arc.value
            ):
                enemies_in_arc.append(enemy.id)

            if range_band <= 3 and self.check_arc(
                enemy.position, end_pos, enemy.primary_arc.value
            ):
                enemies_can_shoot.append(enemy.id)

        return SimulationResult(
            maneuver_code=maneuver.code,
            start_position=ship.position,
            end_position=end_pos,
            would_collide=has_collision,
            collision_with=collision_with,
            would_flee=would_flee,
            stress_after=stress_after,
            enemies_in_arc=enemies_in_arc,
            enemies_can_shoot_me=enemies_can_shoot,
            range_to_enemies=range_to_enemies,
        )

    def simulate_all_maneuvers(self, ship: Ship) -> list[SimulationResult]:
        """Simulate all available maneuvers for comparison."""
        results = []
        for maneuver in ship.available_maneuvers:
            # Skip red maneuvers if stressed
            if ship.stress > 0 and maneuver.is_red:
                continue
            results.append(self.simulate_maneuver(ship, maneuver))
        return results
