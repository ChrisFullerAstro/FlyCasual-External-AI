"""Core game state models received from FlyCasual."""
from __future__ import annotations

import math
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field, computed_field


class Faction(str, Enum):
    REBEL = "rebel"
    IMPERIAL = "imperial"
    SCUM = "scum"
    RESISTANCE = "resistance"
    FIRST_ORDER = "first_order"
    REPUBLIC = "republic"
    SEPARATIST = "separatist"


class ManeuverDifficulty(str, Enum):
    BLUE = "blue"
    WHITE = "white"
    RED = "red"


class ManeuverType(str, Enum):
    STRAIGHT = "straight"
    BANK_LEFT = "bank_left"
    BANK_RIGHT = "bank_right"
    TURN_LEFT = "turn_left"
    TURN_RIGHT = "turn_right"
    KTURN = "kturn"
    SLOOP_LEFT = "sloop_left"
    SLOOP_RIGHT = "sloop_right"
    TALON_LEFT = "talon_left"
    TALON_RIGHT = "talon_right"
    REVERSE_STRAIGHT = "reverse_straight"
    REVERSE_BANK_LEFT = "reverse_bank_left"
    REVERSE_BANK_RIGHT = "reverse_bank_right"
    STATIONARY = "stationary"


class ArcType(str, Enum):
    FRONT = "front"
    REAR = "rear"
    FULL_FRONT = "full_front"
    BULLSEYE = "bullseye"
    TURRET = "turret"


class Position(BaseModel):
    """A position on the game board in millimeters from center."""

    x: float
    y: float
    heading: float = Field(ge=0, lt=360, description="Facing in degrees, 0=up")

    def distance_to(self, other: Position) -> float:
        """Euclidean distance to another position."""
        return math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)

    def bearing_to(self, other: Position) -> float:
        """Relative bearing to another position (0=ahead, 90=right, etc)."""
        dx = other.x - self.x
        dy = other.y - self.y
        absolute_bearing = math.degrees(math.atan2(dx, dy))
        relative = (absolute_bearing - self.heading) % 360
        return relative

    @computed_field
    @property
    def zone(self) -> str:
        """Grid zone A1-F6 (6x6 grid). A1=bottom-left, F6=top-right."""
        board_size = 914.4  # mm (3 feet)
        zone_size = board_size / 6  # 152.4mm per zone
        half = board_size / 2

        # Convert from center-origin to bottom-left origin
        adj_x = self.x + half
        adj_y = self.y + half

        col = min(5, max(0, int(adj_x / zone_size)))
        row = min(5, max(0, int(adj_y / zone_size)))

        return f"{chr(ord('A') + col)}{row + 1}"

    @computed_field
    @property
    def compass(self) -> str:
        """8-point compass direction ship is facing."""
        directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
        # Normalize heading to 0-360, then divide into 8 sectors of 45 degrees
        normalized = ((self.heading % 360) + 360) % 360
        index = round(normalized / 45) % 8
        return directions[index]


class Maneuver(BaseModel):
    """A maneuver from a ship's dial."""

    speed: int = Field(ge=0, le=5)
    type: ManeuverType
    difficulty: ManeuverDifficulty

    @computed_field
    @property
    def code(self) -> str:
        """Unique code like '2_bank_left'."""
        return f"{self.speed}_{self.type.value}"

    @computed_field
    @property
    def is_red(self) -> bool:
        return self.difficulty == ManeuverDifficulty.RED

    @computed_field
    @property
    def removes_stress(self) -> bool:
        return self.difficulty == ManeuverDifficulty.BLUE


class Ship(BaseModel):
    """A ship on the board."""

    # Identity
    id: str
    name: str  # Pilot name
    ship_type: str  # Chassis
    faction: Faction

    # Position
    position: Position

    # Stats
    initiative: int = Field(ge=0, le=7)
    attack: int = Field(ge=0)
    agility: int = Field(ge=0)
    hull: int = Field(ge=1)
    shields: int = Field(ge=0)

    # Current state
    current_hull: int
    current_shields: int
    stress: int = 0
    tokens: list[str] = Field(default_factory=list)

    # Dial
    available_maneuvers: list[Maneuver] = Field(default_factory=list)

    # Arc
    primary_arc: ArcType = ArcType.FRONT
    base_size: str = "small"  # small, medium, large

    # Upgrades (for strategic analysis)
    upgrades: list[str] = Field(default_factory=list)

    @computed_field
    @property
    def is_destroyed(self) -> bool:
        return self.current_hull <= 0

    @computed_field
    @property
    def total_health(self) -> int:
        return self.current_hull + self.current_shields

    @computed_field
    @property
    def health_percentage(self) -> float:
        max_health = self.hull + self.shields
        return self.total_health / max_health if max_health > 0 else 0

    @computed_field
    @property
    def base_size_mm(self) -> float:
        sizes = {"small": 40.0, "medium": 60.0, "large": 80.0}
        return sizes.get(self.base_size, 40.0)

    def has_token(self, token_type: str) -> bool:
        return any(t.startswith(token_type) for t in self.tokens)

    def get_maneuver(self, code: str) -> Maneuver | None:
        for m in self.available_maneuvers:
            if m.code == code:
                return m
        return None

    def get_upgrade_details(self) -> list[dict]:
        """Get full upgrade info including abilities from database."""
        from xwing_agent.data.upgrade_db import get_upgrade_info

        details = []
        for name in self.upgrades:
            info = get_upgrade_info(name) or {}
            details.append({
                "name": name,
                "types": info.get("types", []),
                "ability": info.get("ability", ""),
                "summary": info.get("summary", ""),
                "charges": info.get("charges"),
                "weapon": info.get("weapon"),
            })
        return details


class Obstacle(BaseModel):
    """An obstacle on the board."""

    id: str
    type: str  # asteroid, debris, gas_cloud
    position: Position
    radius: float


class GamePhase(str, Enum):
    SETUP = "setup"
    PLANNING = "planning"
    SYSTEM = "system"
    ACTIVATION = "activation"
    ENGAGEMENT = "engagement"
    END = "end"


class GameState(BaseModel):
    """Complete game state from FlyCasual."""

    game_id: str
    turn_number: int = Field(ge=1)
    phase: GamePhase

    board_width: float = 914.4  # 3 feet in mm
    board_height: float = 914.4

    my_ships: list[Ship]
    enemy_ships: list[Ship]
    obstacles: list[Obstacle] = Field(default_factory=list)

    my_points_destroyed: int = 0
    enemy_points_destroyed: int = 0

    @computed_field
    @property
    def all_ships(self) -> list[Ship]:
        return self.my_ships + self.enemy_ships

    def get_ship(self, ship_id: str) -> Ship | None:
        """Get ship by ID, name, or slug.

        Accepts:
        - Numeric ID: "2"
        - Pilot name: "Rear Admiral Chiraneau"
        - Slug: "rear-admiral-chiraneau"
        """
        ship_id = str(ship_id).strip()
        ship_id_lower = ship_id.lower()

        for ship in self.all_ships:
            # Exact ID match
            if ship.id == ship_id:
                return ship
            # Name match (case insensitive)
            if ship.name.lower() == ship_id_lower:
                return ship
            # Slug match (convert name to slug format)
            slug = ship.name.lower().replace(" ", "-")
            if slug == ship_id_lower:
                return ship
        return None

    def get_active_ships(self, mine: bool = True) -> list[Ship]:
        ships = self.my_ships if mine else self.enemy_ships
        return [s for s in ships if not s.is_destroyed]
