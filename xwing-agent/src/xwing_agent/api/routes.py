"""FastAPI route definitions."""
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from xwing_agent.agent.session import SessionManager
from xwing_agent.agent.strategic import StrategicPlanningAgent
from xwing_agent.logging_config import get_logger
from xwing_agent.models.decisions import (
    DecisionRequest,
    DecisionResponse,
    DecisionType,
)
from xwing_agent.models.game_state import GameState
from xwing_agent.models.persistent import RoundSummary, StrategicPlan
from xwing_agent.storage.game_storage import GameStorage

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1", tags=["xwing"])


def validate_planning_response(response: DecisionResponse) -> DecisionResponse:
    """Validate planning response before sending to client.

    Ensures no null/empty critical fields that would crash the C# client.
    """
    if response.planning is None:
        logger.error("Planning response is None")
        raise ValueError("Planning response cannot be None")

    if response.planning.maneuvers is None:
        logger.error("Maneuvers list is None")
        raise ValueError("Maneuvers list cannot be None")

    for i, m in enumerate(response.planning.maneuvers):
        if not m.ship_id:
            logger.error(f"Maneuver {i} has empty ship_id")
            raise ValueError(f"Maneuver {i} has empty ship_id")
        if not m.maneuver_code:
            logger.error(f"Maneuver {i} for ship {m.ship_id} has empty maneuver_code")
            raise ValueError(f"Maneuver {i} for ship {m.ship_id} has empty maneuver_code")

    logger.info(f"Validated planning response: {len(response.planning.maneuvers)} maneuvers")
    return response


def validate_target_response(response: DecisionResponse) -> DecisionResponse:
    """Validate target response before sending to client."""
    if response.target is None:
        logger.error("Target response is None")
        raise ValueError("Target response cannot be None")

    if not response.target.attacker_id:
        logger.error("Target has empty attacker_id")
        raise ValueError("Target attacker_id cannot be empty")

    if not response.target.target_id:
        logger.error("Target has empty target_id")
        raise ValueError("Target target_id cannot be empty")

    logger.info(f"Validated target response: {response.target.attacker_id} -> {response.target.target_id}")
    return response


def validate_strategic_plan(plan: StrategicPlan) -> StrategicPlan:
    """Validate strategic plan before sending to client."""
    if not plan.win_condition:
        logger.error("Strategic plan has empty win_condition")
        raise ValueError("Strategic plan win_condition cannot be empty")

    if plan.target_priority is None:
        logger.error("Strategic plan has None target_priority")
        raise ValueError("Strategic plan target_priority cannot be None")

    logger.info(f"Validated strategic plan: {plan.win_condition}")
    return plan

# Global session manager
session_manager = SessionManager()


# === Request/Response Models ===


class StrategicPlanRequest(BaseModel):
    game_id: str
    game_state: dict[str, Any]


class StrategicPlanResponse(BaseModel):
    plan: StrategicPlan


class RoundStartRequest(BaseModel):
    game_id: str
    round_number: int
    game_state: dict[str, Any]


class RoundStartResponse(BaseModel):
    session_id: str


class RoundEndRequest(BaseModel):
    session_id: str
    game_state: dict[str, Any]
    events: list[str] = []


class RoundEndResponse(BaseModel):
    summary: RoundSummary
    updated_plan: StrategicPlan


class StateUpdateRequest(BaseModel):
    session_id: str
    game_state: dict[str, Any]
    event: str | None = None


# === Endpoints ===


@router.post("/strategic-plan", response_model=StrategicPlanResponse)
async def create_strategic_plan(request: StrategicPlanRequest):
    """
    Create strategic plan at game start.

    Called once after setup/placement is complete.
    """
    logger.info(f"Strategic plan request for game {request.game_id}")

    try:
        game_state = GameState.model_validate(request.game_state)

        agent = StrategicPlanningAgent()
        plan = await agent.create_plan(game_state)

        # Validate before saving/returning
        validate_strategic_plan(plan)

        # Save plan
        storage = GameStorage(request.game_id)
        storage.save_plan(plan)

        return StrategicPlanResponse(plan=plan)

    except Exception as e:
        logger.exception(f"Failed to create strategic plan: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/round/start", response_model=RoundStartResponse)
async def start_round(request: RoundStartRequest):
    """
    Start a new round session.

    Creates a fresh RoundAgent with the current state.
    """
    logger.info(f"Starting round {request.round_number} for game {request.game_id}")

    try:
        game_state = GameState.model_validate(request.game_state)

        # Load persistent data
        storage = GameStorage(request.game_id)
        plan = storage.load_plan()
        if plan is None:
            raise HTTPException(
                status_code=400, detail="No strategic plan found. Call /strategic-plan first."
            )

        summary = storage.load_summary()

        # Create session
        session = session_manager.create_session(
            game_id=request.game_id,
            round_number=request.round_number,
            game_state=game_state,
            strategic_plan=plan,
            last_summary=summary,
        )

        return RoundStartResponse(session_id=session.session_id)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to start round: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/decide", response_model=DecisionResponse)
async def make_decision(request: DecisionRequest):
    """
    Make a decision within an active round session.

    The session_id must reference an active round session.
    """
    logger.info(f"Decision request: type={request.decision_type}, session={request.session_id}")

    session = session_manager.get_session(request.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        if request.decision_type == DecisionType.PLANNING:
            planning_result = await session.agent.decide_maneuvers()
            response = DecisionResponse(
                decision_type=DecisionType.PLANNING,
                planning=planning_result,
                thinking_trace=str(session.agent.thinking_trace),
            )
            # Validate before returning to ensure C# client won't crash
            return validate_planning_response(response)

        elif request.decision_type == DecisionType.TARGET:
            if not request.ship_id or not request.available_options:
                raise HTTPException(
                    status_code=400,
                    detail="ship_id and available_options required for target selection",
                )

            target_result = await session.agent.select_target(
                attacker_id=request.ship_id,
                available_targets=request.available_options,
            )
            response = DecisionResponse(
                decision_type=DecisionType.TARGET,
                target=target_result,
                thinking_trace=str(session.agent.thinking_trace),
            )
            # Validate before returning to ensure C# client won't crash
            return validate_target_response(response)

        else:
            raise HTTPException(
                status_code=400,
                detail=f"Decision type {request.decision_type} not yet implemented",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Decision failed: {e}")
        return DecisionResponse(
            decision_type=request.decision_type,
            success=False,
            error=str(e),
        )


@router.post("/round/update")
async def update_round_state(request: StateUpdateRequest):
    """
    Update game state during a round.

    Called after movements, to keep the agent's state current.
    """
    session = session_manager.get_session(request.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        game_state = GameState.model_validate(request.game_state)
        session.update_state(game_state)

        if request.event:
            session.agent.record_event(request.event)

        return {"status": "updated"}

    except Exception as e:
        logger.exception(f"Update failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/round/end", response_model=RoundEndResponse)
async def end_round(request: RoundEndRequest):
    """
    End the current round and generate summary.

    Updates strategic plan and saves both to storage.
    """
    session = session_manager.get_session(request.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        # Update state with final round state
        game_state = GameState.model_validate(request.game_state)
        session.update_state(game_state)

        # Record any final events
        for event in request.events:
            session.agent.record_event(event)

        # Generate summary and updated plan
        summary, updated_plan = await session.agent.end_round()

        # Save to storage
        storage = GameStorage(session.game_id)
        storage.save_summary(summary)
        storage.save_plan(updated_plan)

        # Clean up session
        session_manager.end_session(request.session_id)

        return RoundEndResponse(summary=summary, updated_plan=updated_plan)

    except Exception as e:
        logger.exception(f"Round end failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/game/reset/{game_id}")
async def reset_game(game_id: str):
    """Reset all data for a game."""
    storage = GameStorage(game_id)
    storage.clear()
    return {"status": "reset", "game_id": game_id}


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
