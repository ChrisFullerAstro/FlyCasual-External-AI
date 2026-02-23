# X-Wing AI Agent - Project Guide for Claude

## Project Overview

This is an LLM-powered AI agent that plays X-Wing Miniatures Game (2.5 edition). It integrates with FlyCasual, a Unity/C# open-source X-Wing simulator.

**Architecture:**
- **Python Backend** (`/xwing-agent/`) - FastAPI server with Claude-powered decision making
- **C# Integration** (`/FlyCasual/Assets/Scripts/ExternalAI/`) - Unity client that calls the Python API

## Key Design Principles

1. **Fresh context per round** - Each round starts with clean context to avoid bloat
2. **Persistent strategic memory** - StrategicPlan persists and evolves across rounds
3. **Human-like reasoning** - Agent uses tools (radar, simulate, threat) to analyze the board
4. **RAG rules access** - Vector search over X-Wing rules for accurate game knowledge

## Communication Flow

```
FlyCasual (C#)                    Python Backend
     |                                 |
     |-- POST /strategic-plan -------->|  (Game start - create strategy)
     |<-------- StrategicPlan ---------|
     |                                 |
     |-- POST /round/start ----------->|  (Each round)
     |<-------- session_id ------------|
     |                                 |
     |-- POST /decide {planning} ----->|  (Select maneuvers)
     |<-------- ManeuverDecisions -----|
     |                                 |
     |-- POST /decide {target} ------->|  (Select attack target)
     |<-------- TargetDecision --------|
     |                                 |
     |-- POST /round/end ------------->|  (End of round)
     |<--- RoundSummary + UpdatedPlan -|
```

## Project Structure

### Python (`/xwing-agent/src/xwing_agent/`)

| File/Directory | Purpose |
|----------------|---------|
| `main.py` | FastAPI app entrypoint |
| `config.py` | Pydantic Settings (env vars) |
| `api/routes.py` | HTTP endpoints |
| `models/game_state.py` | Ship, Position, Maneuver, GameState |
| `models/persistent.py` | StrategicPlan, RoundSummary |
| `models/decisions.py` | DecisionRequest/Response |
| `game/templates.py` | Maneuver template geometry (mm) |
| `game/simulation.py` | MovementSimulator for position prediction |
| `tools/radar.py` | Situational awareness (bearings, threats) |
| `tools/simulate.py` | Maneuver outcome analysis |
| `tools/threat.py` | Incoming fire assessment |
| `tools/rules.py` | RAG lookup over X-Wing rules |
| `agent/strategic.py` | One-time game start planning |
| `agent/round_agent.py` | Per-round decision making with tools |
| `agent/session.py` | Round session management |
| `storage/game_storage.py` | JSON persistence for plans/summaries |
| `rules/documents/*.md` | X-Wing 2.5 rules for RAG |

### C# (`/FlyCasual/Assets/Scripts/ExternalAI/`)

| File | Purpose |
|------|---------|
| `ExternalAiClient.cs` | HTTP client wrapper (port 33293) |
| `GameStateExporter.cs` | Export game state to JSON |
| `ExternalAiPlayer.cs` | AI player that calls Python backend |
| `Models/ExportModels.cs` | GameStateExport, ShipExport DTOs |
| `Models/ResponseModels.cs` | Response DTOs |

## Running the Project

### Setup
```bash
cd /Users/chrisfuller/code/personal/xwing-agent
make setup          # Creates venv, installs deps, creates .env
# Edit .env - add ANTHROPIC_API_KEY
make index-rules    # Build FAISS vector index from rules
```

### Run
```bash
make app            # Starts FastAPI on port 33293
```

### Test API
```bash
curl http://localhost:33293/api/v1/health
# {"status":"healthy"}
```

### Unity
1. Open `/Users/chrisfuller/code/personal/FlyCasual` in Unity
2. Play game, select "vs AI" mode
3. ExternalAiPlayer auto-falls back to AggressorAiPlayer if backend unavailable

## Implementation Status

### Implemented (matching prompt.md spec)

| Component | Status | Notes |
|-----------|--------|-------|
| Project structure | Complete | Matches spec |
| Config/Settings | Complete | Pydantic Settings |
| Game state models | Complete | Ship, Position, Maneuver, etc. |
| Persistent models | Complete | StrategicPlan, RoundSummary |
| Decision models | Complete | Request/Response types |
| Movement simulation | Complete | Templates, collision detection |
| RadarTool | Complete | Situational awareness |
| SimulateTool | Complete | Maneuver analysis |
| ThreatTool | Complete | Incoming fire assessment |
| RulesTool | Complete | FAISS RAG (needs `make index-rules`) |
| StrategicPlanningAgent | Complete | Game start strategy |
| RoundAgent | Complete | Planning/targeting decisions |
| SessionManager | Complete | Round session tracking |
| GameStorage | Complete | JSON persistence |
| FastAPI routes | Complete | All endpoints |
| C# ExternalAiClient | Complete | HTTP client |
| C# GameStateExporter | Complete | State export |
| C# ExternalAiPlayer | Complete | Unity AI integration |
| Rules documents | Complete | 6 markdown files |

### Not Yet Implemented

| Component | Notes |
|-----------|-------|
| Action selection | Prompt mentions ACTIVATION phase actions (focus, evade, etc.) but not implemented |
| Dice modification decisions | `DiceModDecision` model exists but endpoint not used |
| `rules/loader.py`, `rules/index.py` | Mentioned in spec but logic is in `tools/rules.py` |
| `api/dependencies.py` | Mentioned but not needed (deps in routes.py) |
| `game/arcs.py`, `game/geometry.py` | Merged into simulation.py |
| Test fixtures | `tests/fixtures/game_states/` not populated |
| `scripts/test_game.py` | Headless game simulation not created |

### Deviations from Spec

1. **Port**: Changed from 8000 to 33293 (user request - avoids conflicts)
2. **Some files merged**: geometry.py merged into simulation.py for simplicity
3. **Rules indexing**: Single `tools/rules.py` vs separate loader.py/index.py

## X-Wing 2.5 Rules Reference

The rules in `rules/documents/` have been verified against FlyCasual's implementation:

- **Range 0**: Can attack, but NO dice modifications allowed
- **Range 1**: +1 attack die
- **Range 3**: +1 defense die
- **Front Arc**: 80 degrees total (40 from centerline)
- **Initiative**: Lower moves first (0-6), higher attacks first (6-0)
- **Stress + Red Maneuver**: Downgrades to white 2-straight
- **Dice Modification Order**: Attacker(AfterRolled) -> Defender(Opposite) -> Attacker(Normal)

## Key FlyCasual Files

| File | Purpose |
|------|---------|
| `Model/Players/AggressorAiPlayer.cs` | Base AI player (extended by ExternalAiPlayer) |
| `Model/SquadBuilder/SquadBuilder.cs` | Modified to use ExternalAiPlayer for "vsAI" mode |
| `Model/Movement/MovementTypes/ManeuverHolder.cs` | Maneuver encoding ("2.F.S" = Speed 2 Forward Straight) |

## Maneuver Code Conversion

Python uses `2_straight` format, FlyCasual uses `2.F.S` format.

`ExternalAiPlayer.ConvertManeuverCode()` handles the mapping:
- `straight` -> `F` (Forward)
- `bank_left/right` -> `L/R` (direction) + `B` (Bank)
- `turn_left/right` -> `L/R` (direction) + `T` (Turn)
- `kturn` -> `F` + `K` (Koiogran)
- etc.

## Common Tasks

### Add a new tool
1. Create `tools/new_tool.py` with Tool class
2. Add to `RoundAgent._get_tools()` in `agent/round_agent.py`

### Modify agent prompts
Edit `agent/prompts.py` - contains STRATEGIC_SYSTEM_PROMPT, ROUND_SYSTEM_PROMPT, PLANNING_PROMPT, TARGET_PROMPT, ROUND_END_PROMPT

### Update rules
1. Edit/add files in `rules/documents/`
2. Run `make index-rules` to rebuild FAISS index

### Test without Unity
```bash
# Health check
curl http://localhost:33293/api/v1/health

# Strategic plan (need sample game state JSON)
curl -X POST http://localhost:33293/api/v1/strategic-plan \
  -H "Content-Type: application/json" \
  -d '{"game_id": "test", "game_state": {...}}'
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | Yes | - | Claude API key |
| `ANTHROPIC_MODEL` | No | claude-sonnet-4-20250514 | Model to use |
| `API_PORT` | No | 33293 | Server port |
| `PERCEPTION_ERROR` | No | 0.1 | Distance measurement error (0-0.5) |
| `LANGCHAIN_API_KEY` | No | - | For LangSmith tracing |

## Troubleshooting

### Python backend won't start
- Check `.env` has valid `ANTHROPIC_API_KEY`
- Run `make setup` if deps missing

### Unity can't connect
- Ensure Python backend running on port 33293
- ExternalAiPlayer falls back to AggressorAiPlayer if unavailable

### Newtonsoft.Json error in Unity
Window -> Package Manager -> "+" -> Add by name -> `com.unity.nuget.newtonsoft-json`

### Rules RAG returns nothing
Run `make index-rules` to build the FAISS vector index
