"""Per-round decision agent."""
import re

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import StructuredTool

from xwing_agent.agent.prompts import (
    PLANNING_PROMPT,
    ROUND_END_PROMPT,
    ROUND_SYSTEM_PROMPT,
    TARGET_PROMPT,
)
from xwing_agent.config import get_settings
from xwing_agent.logging_config import get_logger
from xwing_agent.models.decisions import ManeuverDecision, PlanningResponse, TargetDecision
from xwing_agent.models.game_state import GameState
from xwing_agent.models.persistent import (
    RoundEndOutput,
    RoundSummary,
    ShipSnapshot,
    StrategicPlan,
)
from xwing_agent.tools.radar import RadarTool
from xwing_agent.tools.rules import RulesTool
from xwing_agent.tools.simulate import SimulateTool
from xwing_agent.tools.threat import ThreatTool

logger = get_logger(__name__)
settings = get_settings()


class RoundAgent:
    """
    Handles all decisions for a single round.

    Fresh context each round, loads strategic plan and last summary.
    """

    def __init__(
        self,
        game_state: GameState,
        strategic_plan: StrategicPlan,
        last_round_summary: RoundSummary | None = None,
    ):
        self.state = game_state
        self.plan = strategic_plan
        self.last_summary = last_round_summary

        self.llm = ChatAnthropic(
            model=settings.anthropic_model,
            api_key=settings.anthropic_api_key.get_secret_value(),
            max_tokens=settings.anthropic_max_tokens,
        )

        # Initialize tools
        self.radar = RadarTool(game_state, settings.perception_error)
        self.simulate = SimulateTool(game_state, settings.perception_error)
        self.threat = ThreatTool(game_state, settings.perception_error)
        self.rules = RulesTool()

        # Conversation history for this round
        self.messages: list = []
        self.thinking_trace: list[dict] = []
        self.round_events: list[str] = []

    def _build_context(self) -> str:
        """Build the context loaded at round start."""
        parts = []

        # Strategic plan
        parts.append("## STRATEGIC PLAN")
        parts.append(f"Win condition: {self.plan.win_condition}")
        parts.append(f"Target priority: {', '.join(self.plan.target_priority)}")
        parts.append(f"Engagement style: {self.plan.engagement_style}")
        parts.append(f"Ship roles: {self.plan.ship_roles}")
        if self.plan.adjustments:
            parts.append(f"Recent adjustments: {'; '.join(self.plan.adjustments[-3:])}")
        parts.append(f"Opponent tendencies: {self.plan.opponent_tendencies}")

        # Last round summary
        if self.last_summary:
            parts.append("\n## LAST ROUND SUMMARY")
            parts.append(f"Position: {self.last_summary.position_summary}")
            if self.last_summary.damage_events:
                parts.append(f"Damage: {'; '.join(self.last_summary.damage_events)}")
            if self.last_summary.ships_destroyed:
                parts.append(f"Destroyed: {', '.join(self.last_summary.ships_destroyed)}")
            if self.last_summary.enemy_patterns_observed:
                parts.append(f"Enemy patterns: {self.last_summary.enemy_patterns_observed}")
            parts.append(f"Priorities: {', '.join(self.last_summary.next_round_priorities)}")

        # Current state
        parts.append("\n## CURRENT STATE")
        parts.append("My ships:")
        for ship in self.state.get_active_ships(mine=True):
            parts.append(
                f"  - {ship.name} ({ship.id}): {ship.current_hull}H/{ship.current_shields}S, "
                f"stress={ship.stress}, tokens={ship.tokens}"
            )

        parts.append("Enemy ships:")
        for ship in self.state.get_active_ships(mine=False):
            parts.append(
                f"  - {ship.name} ({ship.id}): {ship.current_hull}H/{ship.current_shields}S"
            )

        return "\n".join(parts)

    def _validate_ship_id(self, ship_id: str) -> str:
        """Validate and normalize ship_id. Raises ValueError if not found."""
        ship = self.state.get_ship(str(ship_id))
        if ship is None:
            my_ships = [(s.id, s.name) for s in self.state.get_active_ships(mine=True)]
            enemy_ships = [(s.id, s.name) for s in self.state.get_active_ships(mine=False)]
            raise ValueError(
                f"Ship '{ship_id}' not found. "
                f"My ships: {my_ships}. Enemy ships: {enemy_ships}. "
                f"Use the numeric ID (first element) or exact pilot name."
            )
        return ship.id

    def _safe_tool_call(self, func, *args, **kwargs) -> dict:
        """Execute a tool function safely, returning errors as dict."""
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.warning(f"Tool error: {e}")
            return {"error": str(e)}

    def _get_tools(self) -> list[StructuredTool]:
        """Get LangChain tools for the agent."""

        def radar_scan(ship_id: str) -> dict:
            """Scan from a ship's perspective. Use numeric ship ID (e.g., '2') or pilot name."""
            validated_id = self._validate_ship_id(ship_id)
            return self.radar.scan(validated_id).model_dump()

        def simulate_maneuvers(ship_id: str, maneuvers: list[str]) -> dict:
            """Simulate maneuvers for a ship. Use numeric ship ID and maneuver codes like '2_straight'."""
            validated_id = self._validate_ship_id(ship_id)
            return self.simulate.simulate(validated_id, maneuvers).model_dump()

        def assess_threat(ship_id: str) -> dict:
            """Assess threat level to a ship. Use numeric ship ID (e.g., '2') or pilot name."""
            validated_id = self._validate_ship_id(ship_id)
            return self.threat.assess(validated_id).model_dump()

        def lookup_rules(query: str) -> str:
            """Search X-Wing rules for clarification on game mechanics."""
            return self.rules.search(query)

        return [
            StructuredTool.from_function(
                func=lambda ship_id: self._safe_tool_call(radar_scan, ship_id),
                name="radar",
                description="Scan from a ship's perspective. Returns nearby ships, ranges, bearings, and threat levels. Use numeric ship ID (e.g., '2').",
            ),
            StructuredTool.from_function(
                func=lambda ship_id, maneuvers: self._safe_tool_call(simulate_maneuvers, ship_id, maneuvers),
                name="simulate_maneuvers",
                description="Simulate maneuvers for a ship. Returns predicted positions, collision risks, and tactical outcomes. Use numeric ship ID and maneuver codes like '2_straight', '3_bank_left'.",
            ),
            StructuredTool.from_function(
                func=lambda ship_id: self._safe_tool_call(assess_threat, ship_id),
                name="assess_threat",
                description="Assess threat level to a ship. Returns incoming fire estimates and survival recommendations. Use numeric ship ID (e.g., '2').",
            ),
            StructuredTool.from_function(
                func=lambda query: self._safe_tool_call(lookup_rules, query),
                name="lookup_rules",
                description="Search X-Wing rules for clarification on game mechanics.",
            ),
        ]

    async def decide_maneuvers(self) -> PlanningResponse:
        """Select maneuvers for all ships during planning phase."""
        logger.info(f"Planning phase for round {self.state.turn_number}")
        logger.info(f"My ships: {[(s.id, s.name) for s in self.state.get_active_ships(mine=True)]}")
        logger.info(f"Enemy ships: {[(s.id, s.name) for s in self.state.get_active_ships(mine=False)]}")

        context = self._build_context()
        logger.info(f"Context built:\n{context}")
        system_prompt = ROUND_SYSTEM_PROMPT.format(round_number=self.state.turn_number)

        # Build ship objectives from plan
        ship_objectives = []
        for ship in self.state.get_active_ships(mine=True):
            role = self.plan.ship_roles.get(ship.id, "engage")
            ship_objectives.append(f"- {ship.name} ({ship.id}): Role={role}")

        # Build available maneuvers
        available = []
        for ship in self.state.get_active_ships(mine=True):
            maneuvers = [m.code for m in ship.available_maneuvers]
            available.append(f"- {ship.id}: {', '.join(maneuvers)}")

        prompt = PLANNING_PROMPT.format(
            ship_objectives="\n".join(ship_objectives),
            available_maneuvers="\n".join(available),
        )

        # Set up agent with tools
        tools = self._get_tools()
        llm_with_tools = self.llm.bind_tools(tools)

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"{context}\n\n{prompt}"),
        ]

        # Agent loop
        thinking = []
        for iteration in range(settings.max_tool_iterations):
            response = await llm_with_tools.ainvoke(messages)
            messages.append(response)

            if response.tool_calls:
                # Execute tools
                for tool_call in response.tool_calls:
                    logger.info(f"Tool call: {tool_call['name']}({tool_call['args']})")
                    thinking.append(
                        {
                            "tool": tool_call["name"],
                            "input": tool_call["args"],
                        }
                    )

                    # Find and execute tool
                    for tool in tools:
                        if tool.name == tool_call["name"]:
                            result = tool.invoke(tool_call["args"])
                            logger.info(f"Tool result ({tool_call['name']}): {str(result)[:300]}...")
                            thinking.append(
                                {
                                    "tool_result": tool_call["name"],
                                    "output": str(result)[:500],
                                }
                            )
                            messages.append(
                                ToolMessage(
                                    tool_call_id=tool_call["id"],
                                    content=str(result),
                                )
                            )
                            break
            else:
                # No more tool calls - LLM is done thinking
                logger.info(f"LLM final response:\n{response.content}")
                break

        # Parse and validate decisions - retry if needed
        max_parse_retries = 2
        decisions = []

        for retry in range(max_parse_retries + 1):
            decisions = self._parse_maneuver_response(response.content)
            logger.info(f"Parsed {len(decisions)} maneuver decisions (attempt {retry + 1}):")
            for d in decisions:
                logger.info(f"  Ship {d.ship_id}: {d.maneuver_code} - {d.reasoning[:50]}...")

            # Validate we have decisions for all ships
            validation_errors = self._validate_decisions(decisions)

            if not validation_errors:
                logger.info("All decisions validated successfully")
                break

            if retry < max_parse_retries:
                # Ask LLM to fix the errors
                error_msg = self._build_retry_prompt(validation_errors)
                logger.warning(f"Decision validation failed, asking LLM to retry: {error_msg}")
                messages.append(HumanMessage(content=error_msg))
                response = await llm_with_tools.ainvoke(messages)
                messages.append(response)
                logger.info(f"LLM retry response:\n{response.content}")
            else:
                logger.warning(f"Max retries reached, using best-effort decisions with defaults")

        self.thinking_trace.append(
            {
                "phase": "planning",
                "thinking": thinking,
                "decisions": [d.model_dump() for d in decisions],
            }
        )

        # Store conversation for later in round
        self.messages = messages

        return PlanningResponse(
            maneuvers=decisions,
            strategic_thinking=response.content,
        )

    async def select_target(
        self,
        attacker_id: str,
        available_targets: list[str],
    ) -> TargetDecision:
        """Select attack target during engagement phase."""
        logger.info(f"Target selection for {attacker_id}")

        attacker = self.state.get_ship(attacker_id)

        # Format available targets
        target_info = []
        for tid in available_targets:
            target = self.state.get_ship(tid)
            if target:
                dist = attacker.position.distance_to(target.position)
                range_band = self.simulate.simulator.get_range_band(dist)
                target_info.append(
                    f"- {target.name} ({tid}): "
                    f"{target.current_hull}H/{target.current_shields}S, Range {range_band}"
                )

        prompt = TARGET_PROMPT.format(
            attacker_name=attacker.name,
            attacker_id=attacker_id,
            available_targets="\n".join(target_info),
            priority_targets=", ".join(self.plan.target_priority),
        )

        # Continue conversation
        self.messages.append(HumanMessage(content=prompt))

        response = await self.llm.ainvoke(self.messages)
        self.messages.append(response)

        # Parse target decision
        decision = self._parse_target_response(attacker_id, response.content)

        self.thinking_trace.append(
            {
                "phase": "engagement",
                "attacker": attacker_id,
                "decision": decision.model_dump(),
            }
        )

        return decision

    def record_event(self, event: str):
        """Record something that happened during the round."""
        self.round_events.append(event)

    async def end_round(self) -> tuple[RoundSummary, StrategicPlan]:
        """Generate round summary and update strategic plan."""
        logger.info(f"Ending round {self.state.turn_number}")

        # Build current board state description
        board_state = []
        for ship in self.state.get_active_ships(mine=True):
            board_state.append(f"My {ship.name}: {ship.current_hull}H/{ship.current_shields}S")
        for ship in self.state.get_active_ships(mine=False):
            board_state.append(f"Enemy {ship.name}: {ship.current_hull}H/{ship.current_shields}S")

        prompt = ROUND_END_PROMPT.format(
            round_number=self.state.turn_number,
            round_events="\n".join(self.round_events) or "No notable events recorded",
            board_state="\n".join(board_state),
        )

        structured_llm = self.llm.with_structured_output(RoundEndOutput)

        result = await structured_llm.ainvoke(
            [
                SystemMessage(content="Summarize the round and suggest strategic adjustments."),
                HumanMessage(content=prompt),
            ]
        )

        # Build ship snapshots
        my_ships = []
        for ship in self.state.my_ships:
            my_ships.append(
                ShipSnapshot(
                    ship_id=ship.id,
                    ship_name=ship.name,
                    position_description="",  # Would be filled by radar-like logic
                    hull=ship.current_hull,
                    shields=ship.current_shields,
                    stress=ship.stress,
                    tokens=ship.tokens,
                    is_destroyed=ship.is_destroyed,
                )
            )

        enemy_ships = []
        for ship in self.state.enemy_ships:
            enemy_ships.append(
                ShipSnapshot(
                    ship_id=ship.id,
                    ship_name=ship.name,
                    position_description="",
                    hull=ship.current_hull,
                    shields=ship.current_shields,
                    stress=ship.stress,
                    tokens=ship.tokens,
                    is_destroyed=ship.is_destroyed,
                )
            )

        summary = result.round_summary
        summary.my_ships = my_ships
        summary.enemy_ships = enemy_ships
        summary.round_number = self.state.turn_number

        # Update strategic plan
        updated_plan = self.plan.model_copy()
        updated_plan.adjustments.extend(result.strategic_adjustments)
        if result.updated_target_priority:
            updated_plan.target_priority = result.updated_target_priority
        if result.updated_engagement_style:
            updated_plan.engagement_style = result.updated_engagement_style
        updated_plan.last_updated_turn = self.state.turn_number

        return summary, updated_plan

    def _validate_decisions(self, decisions: list[ManeuverDecision]) -> list[str]:
        """Validate parsed decisions. Returns list of error messages."""
        errors = []
        my_ship_ids = {s.id for s in self.state.get_active_ships(mine=True)}
        decision_ship_ids = {d.ship_id for d in decisions}

        # Check for missing ships
        missing = my_ship_ids - decision_ship_ids
        for ship_id in missing:
            ship = self.state.get_ship(ship_id)
            errors.append(f"Missing maneuver for ship {ship_id} ({ship.name if ship else 'unknown'})")

        # Check for invalid ships
        invalid_ships = decision_ship_ids - my_ship_ids
        for ship_id in invalid_ships:
            errors.append(f"Decision for unknown ship {ship_id} - not one of our ships")

        # Check for invalid maneuvers
        for d in decisions:
            ship = self.state.get_ship(d.ship_id)
            if ship and not ship.get_maneuver(d.maneuver_code):
                available = [m.code for m in ship.available_maneuvers]
                errors.append(
                    f"Invalid maneuver '{d.maneuver_code}' for {ship.name}. "
                    f"Available: {available[:8]}..."
                )

        return errors

    def _build_retry_prompt(self, errors: list[str]) -> str:
        """Build a prompt asking the LLM to fix validation errors."""
        error_list = "\n".join(f"- {e}" for e in errors)

        # Include ship info for reference
        ship_info = []
        for ship in self.state.get_active_ships(mine=True):
            maneuvers = [m.code for m in ship.available_maneuvers]
            ship_info.append(f"- {ship.name} (ID: {ship.id}): {', '.join(maneuvers[:10])}...")

        return f"""Your response had validation errors that need to be fixed:

{error_list}

Please provide corrected maneuver decisions. Here are the ships that need maneuvers:

{chr(10).join(ship_info)}

Respond with the corrected format:
SHIP: <ship_id>
MANEUVER: <valid_maneuver_code>
REASONING: <your reasoning>

Use the NUMERIC ship ID (like "2") and valid maneuver codes (like "2_straight", "3_bank_left")."""

    def _get_default_maneuver(self, ship) -> str:
        """Get a safe default maneuver for a ship (prefer 2_straight or similar)."""
        # Prefer straight maneuvers, then banks, then turns
        for code in ["2_straight", "1_straight", "3_straight", "2_bank_left", "2_bank_right"]:
            if ship.get_maneuver(code):
                return code
        # Fall back to first available
        if ship.available_maneuvers:
            return ship.available_maneuvers[0].code
        return "2_straight"  # Ultimate fallback

    def _validate_maneuver(self, ship, maneuver_code: str) -> str | None:
        """Validate maneuver code for a ship. Returns valid code or None."""
        maneuver = ship.get_maneuver(maneuver_code)
        if maneuver:
            return maneuver_code
        # Try common variations
        for suffix in ["", "_straight", "_bank_left", "_bank_right"]:
            alt = f"{maneuver_code}{suffix}" if not suffix else maneuver_code.replace("_", suffix)
            if ship.get_maneuver(alt):
                return alt
        return None

    def _parse_maneuver_response(self, content: str) -> list[ManeuverDecision]:
        """Parse and validate maneuver decisions from LLM response."""
        decisions = []
        assigned_ships = set()

        # Look for SHIP: / MANEUVER: / REASONING: patterns
        pattern = (
            r"SHIP:\s*(\S+)\s*\n\s*MANEUVER:\s*(\S+)\s*\n\s*REASONING:\s*(.+?)(?=\n\s*SHIP:|\Z)"
        )
        matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)
        logger.info(f"Regex found {len(matches)} matches in response")

        for ship_id, maneuver, reasoning in matches:
            # Strip markdown formatting (e.g., **4** -> 4) but preserve underscores
            clean_ship_id = re.sub(r'[\*\#\`]', '', ship_id.strip())
            clean_maneuver = re.sub(r'[\*\#\`]', '', maneuver.strip())

            # Normalize ship_id to numeric ID (LLM may return name like "dengar")
            ship = self.state.get_ship(clean_ship_id)
            if not ship:
                logger.warning(f"Ship '{clean_ship_id}' not found, skipping")
                continue

            # Skip if not one of our ships
            if ship.id not in [s.id for s in self.state.get_active_ships(mine=True)]:
                logger.warning(f"Ship '{ship.id}' is not one of our active ships, skipping")
                continue

            # Validate maneuver code
            valid_maneuver = self._validate_maneuver(ship, clean_maneuver)
            if not valid_maneuver:
                available = [m.code for m in ship.available_maneuvers]
                logger.warning(f"Maneuver '{clean_maneuver}' not valid for {ship.name}. Available: {available[:10]}...")
                valid_maneuver = self._get_default_maneuver(ship)
                logger.info(f"Using default maneuver: {valid_maneuver}")

            logger.info(f"Validated: ship='{ship.id}' ({ship.name}), maneuver='{valid_maneuver}'")

            decisions.append(
                ManeuverDecision(
                    ship_id=ship.id,
                    maneuver_code=valid_maneuver,
                    reasoning=reasoning.strip()[:200],
                )
            )
            assigned_ships.add(ship.id)

        # Ensure ALL our ships have maneuvers (fallback for missing ships)
        for ship in self.state.get_active_ships(mine=True):
            if ship.id not in assigned_ships:
                logger.warning(f"No maneuver parsed for {ship.name} ({ship.id}), using default")
                default = self._get_default_maneuver(ship)
                decisions.append(
                    ManeuverDecision(
                        ship_id=ship.id,
                        maneuver_code=default,
                        reasoning="Default maneuver (LLM did not specify)",
                    )
                )

        return decisions

    def _parse_target_response(self, attacker_id: str, content: str) -> TargetDecision:
        """Parse target decision from LLM response."""
        # Look for TARGET: pattern
        match = re.search(r"TARGET:\s*(\S+)", content, re.IGNORECASE)
        if match:
            target_id = match.group(1).strip()
        else:
            # Fallback: use priority target
            target_id = self.plan.target_priority[0] if self.plan.target_priority else ""

        # Extract reasoning
        reason_match = re.search(r"REASONING:\s*(.+?)(?=\n|$)", content, re.IGNORECASE)
        reasoning = reason_match.group(1) if reason_match else content[:200]

        return TargetDecision(
            attacker_id=attacker_id,
            target_id=target_id,
            reasoning=reasoning,
        )
