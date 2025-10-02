# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

Fantasy Football MCP (Model Context Protocol) server integrating Yahoo Fantasy Sports API with advanced lineup optimization. Uses Sleeper API for expert rankings, defensive matchup analysis, and position-normalized FLEX decisions. Production server: `fantasy_football_multi_league.py`.

Supports multiple deployment strategies:
- **Local MCP** for Claude Code (stdio mode)
- **Remote MCP** for Claude.ai via Render (OAuth + HTTP/WebSocket)
- **Docker** containerization for cloud deployments

## Essential Commands

### Running & Testing
```bash
# Main FastMCP server (HTTP/SSE mode)
python fastmcp_server.py

# Run local MCP server with environment variables
./run_local_mcp.sh

# Deploy to Render
./deploy_to_render.sh
```

### Token Management
```bash
python refresh_yahoo_token.py   # Refresh expired token (expires hourly)
python reauth_yahoo.py          # Full re-authentication
python setup_yahoo_auth.py      # Initial Yahoo OAuth setup
```

### Development
```bash
pip install -r requirements.txt
black . --line-length 100       # Format code (see pyproject.toml)
ruff check .                     # Lint code
mypy src/                        # Type checking
pytest tests/ -v                 # Run tests (when available)
```

### Deployment
```bash
# Deploy to Render (auto-deploys from main branch)
./deploy_to_render.sh

# Build Docker image
docker build -t fantasy-football-mcp .

# Run Docker container locally
docker run -p 8080:8080 --env-file .env fantasy-football-mcp
```

## Architecture

### Core Optimization System

**Lineup Optimizer** (`lineup_optimizer.py`)
- Ultra-aggressive tier system: Elite (3x), Stud (2x), Solid (1.3x), Flex (1.0x), Bench (0.5x)
- Position normalization for FLEX decisions via `position_normalizer.py`
- Volatility/consistency scoring for floor vs ceiling strategies
- Week 17 rest adjustments for playoff teams

**Position Normalizer** (`position_normalizer.py`)
- Handles different scoring baselines: RB ~11pts, WR ~10pts, TE ~7pts
- Value Over Replacement (VOR) calculations
- FLEX value formula: `(VOR * scarcity * 0.3) + (projection * 0.7)`

**Matchup Analyzer** (`matchup_analyzer.py`)
- Sigmoid transformation with k=0.05 for matchup scores
- Non-linear scoring to differentiate elite/poor defenses

### Strategy Weights (Balanced)
```python
{
    "matchup": 0.10,   # Heavily reduced - player quality matters more
    "yahoo": 0.40,     # Trust expert projections
    "sleeper": 0.40,   # Trust expert projections
    "trending": 0.05,
    "momentum": 0.05
}
```

### FLEX Scoring
- 85% raw projection weight, 15% composite analysis
- Position normalization prevents TE trap
- Consistency bonuses for floor/ceiling strategies

### Draft Assistant System (`src/models/draft.py`, `src/agents/draft_evaluator.py`)
- **Multi-factor analysis**: VORP, scarcity, need, bye weeks, risk, upside
- **Strategy-based weighting**: Conservative (safety), Aggressive (upside), Balanced
- **Real-time recommendations**: Works during live drafts with current roster analysis
- **Statistical framework**: Value Over Replacement Player calculations and positional scarcity
- **Edge case handling**: Early/mid/late draft phases, positional runs, opportunity cost

## Server Architecture

### FastMCP Server (`fastmcp_server.py`)
- **Primary entry point** for all deployments (local, Render, fastmcp.cloud, Docker)
- **Mode**: HTTP/SSE with FastMCP framework
- **Protocol**: MCP 2.0 compliant with tool decorators
- **Authentication**: Yahoo API OAuth via environment variables
- **Use cases**:
  - Local development: `python fastmcp_server.py`
  - Claude Desktop: stdio mode via `~/.claude/config.json`
  - Production: Render/Docker/fastmcp.cloud deployments

### Core Implementation (`fantasy_football_multi_league.py`)
- **Role**: Tool logic and Yahoo API integration
- **Functions**: 35 functions across leagues, rosters, players, draft, admin
- **Dependencies**: Wraps yahoo_api_utils, lineup_optimizer, sleeper_api
- **Note**: Currently 2,675 lines - refactor planned to modular structure

## Critical Configuration

### Environment Variables (.env)
```env
YAHOO_CONSUMER_KEY=dj0yJmk9RUxycTRzNjJkdW1rJmQ9WVdrOVNtSXdNM3BWYUhJbWNHbzlNQT09JnM9Y29uc3VtZXJzZWNyZXQmc3Y9MCZ4PTNm
YAHOO_CONSUMER_SECRET=d56351e699f40c0c341cf9fd294d0340625d04dd
YAHOO_ACCESS_TOKEN=[current_token]
YAHOO_REFRESH_TOKEN=[current_refresh_token]
YAHOO_GUID=QQQ5VN577FJJ4GT2NLMJMIYEBU  # Required for multi-league

# For remote MCP servers (Render deployment)
DEBUG=true
ALLOWED_CLIENT_IDS=*
ALLOWED_REDIRECT_URIS=*
OAUTH_CLIENT_SECRET=secure-secret-change-this-in-production
CORS_ORIGINS=*
RENDER_EXTERNAL_URL=https://fantasy-football-mcp-server.onrender.com
```

### Claude Desktop Configuration (~/.claude/config.json)
```json
{
  "mcpServers": {
    "fantasy-football": {
      "command": "python",
      "args": [
        "/home/derek/apps/fantasy-football-mcp-server/fastmcp_server.py"
      ],
      "env": {
        "YAHOO_ACCESS_TOKEN": "...",
        "YAHOO_CONSUMER_KEY": "...",
        "YAHOO_CONSUMER_SECRET": "...",
        "YAHOO_REFRESH_TOKEN": "...",
        "YAHOO_GUID": "QQQ5VN577FJJ4GT2NLMJMIYEBU"
      }
    }
  }
}
```

### Yahoo API Response Patterns
```python
# Leagues
data["fantasy_content"]["users"]["0"]["user"][...]["leagues"]

# Teams - complex array structure
teams[key]["team"][0]  # List of dict elements
# Element 3: is_owned_by_current_login
# Element 23: managers list with GUIDs
```

### Cache TTLs (`yahoo_api_utils.py`)
- Leagues: 1 hour
- Standings: 5 minutes
- Matchups: 1 minute
- Players/stats: 15 minutes

## MCP Tools (18 Available)

**League**: `ff_get_leagues`, `ff_get_league_info`, `ff_get_standings`
**Team**: `ff_get_roster`, `ff_get_matchup`, `ff_build_lineup`, `ff_compare_teams`
**Players**: `ff_get_players`, `ff_get_waiver_wire`, `ff_get_draft_rankings`
**Draft**: `ff_get_draft_recommendation`, `ff_analyze_draft_state`, `ff_get_draft_results`
**Analytics**: `ff_analyze_reddit_sentiment`
**Admin**: `ff_refresh_token`, `ff_get_api_status`, `ff_clear_cache`

### Draft Tools Usage

**`ff_get_draft_recommendation`** - Live draft assistant
```python
# Get top 10 picks with balanced strategy
{
  "league_key": "461.l.61410",
  "strategy": "balanced",           # conservative, aggressive, balanced  
  "num_recommendations": 10,        # 1-20 recommendations
  "current_pick": 24               # optional overall pick number
}
```

**`ff_analyze_draft_state`** - Roster needs analysis  
```python
# Analyze current draft position and needs
{
  "league_key": "461.l.61410", 
  "strategy": "balanced"           # affects strategic advice
}
```

**Draft Strategies:**
- **Conservative**: Prioritize proven players, minimize risk
- **Aggressive**: Chase upside, target breakout candidates
- **Balanced**: Optimal mix of safety and upside potential

### Analytics Tools Usage

**`ff_analyze_reddit_sentiment`** - Social sentiment analysis
```python
# Analyze Reddit sentiment for multiple players
{
  "players": ["Josh Allen", "Christian McCaffrey", "Cooper Kupp"],
  "time_window_hours": 48  # optional, defaults to 48
}
```

**`ff_compare_teams`** - Team comparison for trades/matchups
```python
# Compare two teams in the same league
{
  "league_key": "461.l.61410",
  "team_key_a": "461.l.61410.t.1",
  "team_key_b": "461.l.61410.t.2"
}
```

## Model Performance Metrics

Target model performance (when validation suite is implemented):
- **80%+** accuracy on borderline decisions
- **80%+** FLEX decision accuracy (position-normalized)
- **+2.0** points per decision average
- **90%+** lineup efficiency
- **85%+** precision on start/sit calls

Known challenges:
- Week 17 (players resting for playoffs)
- Injury report timing delays
- Weather impact on game-time decisions

## Common Issues

**Token Expiration (401 errors)**
- Tokens expire hourly
- Auto-refresh in `yahoo_api_call()`
- Manual: `python refresh_yahoo_token.py`

**Rate Limiting**
- Yahoo: 1000 req/hour limit
- Implemented: 900/hour sliding window
- Check via `ff_get_api_status` tool
- Clear cache via `ff_clear_cache` tool if needed

**"Only showing one league"**
- Verify YAHOO_GUID in .env
- Check team ownership detection in `fantasy_football_multi_league.py`

**Claude.ai Remote MCP Connection (-32000 errors)**
- Known issue with Claude.ai's MCP implementation
- Use Claude Code (local) for reliable connection
- Monitor Render logs for OAuth debugging

## Git Workflow

Current branch: `main` (previously `sleeper-api-integration`)

Commit format:
```bash
git commit -m "type: Description

Details here

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>"
```

Types: feat, fix, docs, style, refactor, test, chore

## Active Leagues (2025)
1. Anyone But Andy (461.l.61410) - Team: BreesusChr1st
2. Superbowl or Bust (461.l.92016)
3. Forte Ounces to Freedom (461.l.914466)
4. Murderer's Row (461.l.96875)

## Render Deployment

Service URL: https://fantasy-football-mcp-server.onrender.com

Monitor deployment:
```bash
# Check deployment status
render deploys list fantasy-football-mcp-server

# View logs
render logs fantasy-football-mcp-server -o text

# Trigger manual deploy
git push origin main  # Auto-deploys from main branch
```

## Docker Build

```dockerfile
# Key configuration in Dockerfile:
FROM python:3.11-slim
CMD uvicorn simple_mcp_server:app --host 0.0.0.0 --port ${PORT:-8080}
```

Build and run locally:
```bash
docker build -t ff-mcp .
docker run -p 8080:8080 --env-file .env ff-mcp
```

## Code Quality Standards

- **Formatting**: Black with 100-char line length
- **Linting**: Ruff with E, W, F, I, B, C4, UP rules
- **Type checking**: MyPy with strict mode
- **Testing**: Pytest with asyncio support
- **Coverage**: Target 80%+ for critical paths

See `pyproject.toml` for detailed configuration.