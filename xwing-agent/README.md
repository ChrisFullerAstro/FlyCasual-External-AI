# X-Wing AI Agent

LLM-powered AI agent for X-Wing Miniatures Game, designed to integrate with FlyCasual.

## Overview

This project provides an intelligent AI opponent for X-Wing that uses Claude (Anthropic's LLM) to make tactical decisions. The AI features:

- **Strategic Planning**: Analyzes squad matchups at game start
- **Tactical Tools**: Radar scanning, maneuver simulation, threat assessment
- **Persistent Memory**: Strategic plan updates based on game events
- **Human-like Reasoning**: Uses tools to analyze before deciding

## Architecture

```
FlyCasual (Unity/C#)  <--HTTP-->  Python Agent (FastAPI + Claude)
```

The Python agent runs as a local server that FlyCasual communicates with via HTTP.

## Setup

### Python Backend

1. Create and activate a virtual environment:
```bash
cd xwing-agent
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -e ".[dev]"
```

3. Copy environment file and add your API key:
```bash
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

4. Run the server:
```bash
python scripts/run_dev.py
```

The server will start at `http://localhost:33293`.

### FlyCasual Integration

The C# integration files are in `FlyCasual/Assets/Scripts/ExternalAI/`.

To use the external AI:
1. Start the Python backend
2. In FlyCasual, use game mode "vsExternalAI" or "ExternalAIvsAI"

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/health` | GET | Health check |
| `/api/v1/strategic-plan` | POST | Create strategic plan at game start |
| `/api/v1/round/start` | POST | Start a new round session |
| `/api/v1/decide` | POST | Make a decision (planning/target) |
| `/api/v1/round/update` | POST | Update game state mid-round |
| `/api/v1/round/end` | POST | End round and generate summary |

## Project Structure

```
xwing-agent/
├── src/xwing_agent/
│   ├── api/            # FastAPI routes
│   ├── agent/          # LLM agents (strategic, round)
│   ├── game/           # Movement simulation
│   ├── models/         # Pydantic models
│   ├── storage/        # Game state persistence
│   └── tools/          # Agent tools (radar, simulate, threat)
├── tests/
└── scripts/
```

## Configuration

Environment variables (see `.env.example`):

| Variable | Description | Default |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Your Anthropic API key | Required |
| `ANTHROPIC_MODEL` | Claude model to use | claude-sonnet-4-20250514 |
| `API_PORT` | Server port | 33293 |
| `PERCEPTION_ERROR` | Randomness in distance estimates | 0.1 |

## Development

Run tests:
```bash
pytest
```

Format code:
```bash
ruff check --fix src/ tests/
```

## License

MIT
