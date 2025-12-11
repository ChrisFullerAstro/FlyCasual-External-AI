"""Pytest fixtures."""
import pytest

from xwing_agent.models.game_state import (
    Faction,
    GamePhase,
    GameState,
    Maneuver,
    ManeuverDifficulty,
    ManeuverType,
    Position,
    Ship,
)


@pytest.fixture
def sample_position():
    return Position(x=0, y=0, heading=0)


@pytest.fixture
def sample_maneuver():
    return Maneuver(
        speed=2,
        type=ManeuverType.STRAIGHT,
        difficulty=ManeuverDifficulty.WHITE,
    )


@pytest.fixture
def sample_ship(sample_position):
    return Ship(
        id="tie_1",
        name="Academy Pilot",
        ship_type="TIE Fighter",
        faction=Faction.IMPERIAL,
        position=sample_position,
        initiative=1,
        attack=2,
        agility=3,
        hull=3,
        shields=0,
        current_hull=3,
        current_shields=0,
        available_maneuvers=[
            Maneuver(speed=1, type=ManeuverType.STRAIGHT, difficulty=ManeuverDifficulty.WHITE),
            Maneuver(speed=2, type=ManeuverType.STRAIGHT, difficulty=ManeuverDifficulty.WHITE),
            Maneuver(speed=2, type=ManeuverType.BANK_LEFT, difficulty=ManeuverDifficulty.WHITE),
            Maneuver(speed=2, type=ManeuverType.BANK_RIGHT, difficulty=ManeuverDifficulty.WHITE),
        ],
    )


@pytest.fixture
def sample_game_state(sample_ship):
    enemy = Ship(
        id="xwing_1",
        name="Rookie Pilot",
        ship_type="X-Wing",
        faction=Faction.REBEL,
        position=Position(x=0, y=200, heading=180),
        initiative=2,
        attack=3,
        agility=2,
        hull=4,
        shields=2,
        current_hull=4,
        current_shields=2,
        available_maneuvers=[],
    )

    return GameState(
        game_id="test-game",
        turn_number=1,
        phase=GamePhase.PLANNING,
        my_ships=[sample_ship],
        enemy_ships=[enemy],
    )
