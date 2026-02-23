"""Movement template geometry."""
from dataclasses import dataclass

from xwing_agent.models.game_state import ManeuverType


@dataclass(frozen=True)
class TemplateGeometry:
    """Distance and rotation for a maneuver template."""

    distance: float  # mm
    rotation: float  # degrees, positive = clockwise


TEMPLATE_GEOMETRY: dict[ManeuverType, dict[int, TemplateGeometry]] = {
    ManeuverType.STRAIGHT: {
        0: TemplateGeometry(0, 0),
        1: TemplateGeometry(40, 0),
        2: TemplateGeometry(80, 0),
        3: TemplateGeometry(120, 0),
        4: TemplateGeometry(160, 0),
        5: TemplateGeometry(200, 0),
    },
    ManeuverType.BANK_LEFT: {
        1: TemplateGeometry(54, -45),
        2: TemplateGeometry(94, -45),
        3: TemplateGeometry(134, -45),
    },
    ManeuverType.BANK_RIGHT: {
        1: TemplateGeometry(54, 45),
        2: TemplateGeometry(94, 45),
        3: TemplateGeometry(134, 45),
    },
    ManeuverType.TURN_LEFT: {
        1: TemplateGeometry(35, -90),
        2: TemplateGeometry(62, -90),
        3: TemplateGeometry(89, -90),
    },
    ManeuverType.TURN_RIGHT: {
        1: TemplateGeometry(35, 90),
        2: TemplateGeometry(62, 90),
        3: TemplateGeometry(89, 90),
    },
    ManeuverType.KTURN: {
        2: TemplateGeometry(80, 180),
        3: TemplateGeometry(120, 180),
        4: TemplateGeometry(160, 180),
        5: TemplateGeometry(200, 180),
    },
    ManeuverType.SLOOP_LEFT: {
        2: TemplateGeometry(94, -135),
        3: TemplateGeometry(134, -135),
    },
    ManeuverType.SLOOP_RIGHT: {
        2: TemplateGeometry(94, 135),
        3: TemplateGeometry(134, 135),
    },
    ManeuverType.TALON_LEFT: {
        2: TemplateGeometry(62, -135),
        3: TemplateGeometry(89, -135),
    },
    ManeuverType.TALON_RIGHT: {
        2: TemplateGeometry(62, 135),
        3: TemplateGeometry(89, 135),
    },
    ManeuverType.REVERSE_STRAIGHT: {
        1: TemplateGeometry(-40, 0),
        2: TemplateGeometry(-80, 0),
    },
    ManeuverType.REVERSE_BANK_LEFT: {
        1: TemplateGeometry(-54, 45),
    },
    ManeuverType.REVERSE_BANK_RIGHT: {
        1: TemplateGeometry(-54, -45),
    },
    ManeuverType.STATIONARY: {
        0: TemplateGeometry(0, 0),
    },
}


def get_template(maneuver_type: ManeuverType, speed: int) -> TemplateGeometry | None:
    """Get geometry for a specific maneuver."""
    type_templates = TEMPLATE_GEOMETRY.get(maneuver_type)
    if type_templates is None:
        return None
    return type_templates.get(speed)
