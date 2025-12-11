"""Strategic planning agent - runs once at game start."""
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from xwing_agent.agent.prompts import STRATEGIC_SYSTEM_PROMPT
from xwing_agent.config import get_settings
from xwing_agent.logging_config import get_logger
from xwing_agent.models.game_state import GameState
from xwing_agent.models.persistent import StrategicPlan
from xwing_agent.tools.rules import RulesTool

logger = get_logger(__name__)
settings = get_settings()


class StrategicPlanOutput(StrategicPlan):
    """For structured output."""

    pass


class StrategicPlanningAgent:
    """Creates the initial strategic plan for a game."""

    def __init__(self):
        self.llm = ChatAnthropic(
            model=settings.anthropic_model,
            api_key=settings.anthropic_api_key.get_secret_value(),
            max_tokens=settings.anthropic_max_tokens,
        )
        self.rules_tool = RulesTool()

    def _format_squad(self, ships, label: str) -> str:
        """Format a squad for the prompt."""
        lines = [f"## {label}"]
        for ship in ships:
            lines.append(
                f"- {ship.name} ({ship.ship_type}): "
                f"I{ship.initiative}, {ship.attack}A/{ship.agility}D, "
                f"{ship.hull}H/{ship.shields}S"
            )
            if ship.upgrades:
                lines.append(f"  Upgrades: {', '.join(ship.upgrades)}")
        return "\n".join(lines)

    async def create_plan(self, game_state: GameState) -> StrategicPlan:
        """Create strategic plan for the game."""
        logger.info(f"Creating strategic plan for game {game_state.game_id}")

        # Build prompt
        my_squad = self._format_squad(game_state.my_ships, "MY SQUADRON")
        enemy_squad = self._format_squad(game_state.enemy_ships, "ENEMY SQUADRON")

        prompt = f"""Analyze these squads and create a strategic plan.

{my_squad}

{enemy_squad}

## OBSTACLES
{len(game_state.obstacles)} obstacles on the board.

Consider the matchup and develop:
1. Initial analysis of strengths/weaknesses
2. Win condition (how do we win?)
3. Target priority (who to focus first)
4. Engagement style (aggressive/defensive/flanking)
5. Role for each of my ships
6. Key threats to watch

Be specific and tactical."""

        # Get structured output
        structured_llm = self.llm.with_structured_output(StrategicPlanOutput)

        plan = await structured_llm.ainvoke(
            [
                SystemMessage(content=STRATEGIC_SYSTEM_PROMPT),
                HumanMessage(content=prompt),
            ]
        )

        # Ensure metadata is set
        plan.created_turn = 1
        plan.last_updated_turn = 1

        logger.info(f"Strategic plan created: {plan.win_condition}")
        logger.info(f"=== STRATEGIC PLAN ===")
        logger.info(f"Analysis: {plan.initial_analysis}")
        logger.info(f"My strengths: {plan.my_squad_strengths}")
        logger.info(f"My weaknesses: {plan.my_squad_weaknesses}")
        logger.info(f"Enemy threats: {plan.enemy_threats}")
        logger.info(f"Win condition: {plan.win_condition}")
        logger.info(f"Target priority: {plan.target_priority}")
        logger.info(f"Engagement style: {plan.engagement_style}")
        logger.info(f"Ship roles: {plan.ship_roles}")
        logger.info(f"======================")
        return plan
