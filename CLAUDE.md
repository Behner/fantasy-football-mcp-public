# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

Fantasy Football MCP (Model Context Protocol) server integrating Yahoo Fantasy Sports API with advanced lineup optimization. Uses Sleeper API for expert rankings, defensive matchup analysis, and position-normalized FLEX decisions. Production server: `fantasy_football_multi_league.py` (1,155 lines - down from 2,675).

**Architecture**: Fully modularized with domain-driven handler organization. Core logic extracted to `src/api/`, `src/parsers/`, `src/services/`, and `src/handlers/`. Main file is now minimal orchestration layer only.

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

### Handler Organization (Phase 2b Complete)

All MCP tool handlers are now extracted into domain-organized modules under `src/handlers/`:

**Handler Modules**:
- `admin_handlers.py` - Token refresh, API status, cache management
- `league_handlers.py` - League discovery, info, standings, teams
- `roster_handlers.py` - Roster retrieval with enhanced data
- `matchup_handlers.py` - Matchups, lineup optimization, team comparison
- `player_handlers.py` - Player search, waiver wire analysis
- `draft_handlers.py` - Draft recommendations, rankings, state analysis
- `analytics_handlers.py` - Reddit sentiment analysis

**Dependency Injection Pattern**: Handlers receive dependencies via injection functions in `src/handlers/__init__.py`. This allows clean separation while maintaining access to Yahoo API, parsers, and helper functions.

**Main File**: `fantasy_football_multi_league.py` contains:
- Server initialization and global state management
- Helper functions (discover_leagues, get_user_team_info, etc.)
- Tool definitions and MCP protocol implementation
- Handler dependency injection via `src/handlers/__init__.py`
- Yahoo API client initialization and rate limiting setup

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

### Supporting Modules

**API Layer** (`src/api/`):
- Yahoo API client wrappers and response parsers
- Sleeper API integration for player rankings and defensive metrics

**Services** (`src/services/`):
- `reddit_service.py` - Reddit sentiment analysis integration
- `player_enhancement.py` - Player projection enhancement with bye week detection and recent stats

**Agents** (`src/agents/`):
- `draft_evaluator.py` - Draft recommendation logic and VORP calculations
- `reddit_analyzer.py` - Social sentiment analysis
- `statistical.py` - Statistical models and projections
- `optimization.py`, `hybrid_optimizer.py` - Lineup optimization engines
- `cache_manager.py` - Response caching and rate limiting

**Utils** (`src/utils/`):
- `constants.py` - League-wide constants and configuration
- `scoring.py` - Scoring system definitions
- `roster_configs.py` - Roster position requirements

**Models** (`src/models/`):
- Pydantic models for type safety and validation

### Player Enhancement Layer (NEW)

**Problem**: Sleeper API projections lag reality and don't account for bye weeks or recent breakout performances.

**Solution**: `src/services/player_enhancement.py` enriches player data before returning to users:

**Features**:
- ✅ **Bye Week Detection**: Zeros out projections for players on bye (compares current week vs Yahoo bye data)
- ✅ **Recent Stats Context**: Pulls last 1-3 weeks actual performance from Sleeper Stats API
- ✅ **Performance Flags**:
  - `BREAKOUT_CANDIDATE` - Recent avg > 150% of projection
  - `TRENDING_UP` - Recent performance exceeds projection
  - `DECLINING_ROLE` - Recent avg < 70% of projection
  - `HIGH_CEILING` - Recent high game > 2x projection
  - `CONSISTENT` - Steady performance near projection
- ✅ **Adjusted Projections**: Blends recent reality with Sleeper projections (60/40 or 70/30 depending on flags)

**Integration Point**: `lineup_optimizer.py:enhance_with_external_data()` (line ~516)

**New Player Fields**:
```python
player.bye                      # Bye week number from Yahoo
player.on_bye                   # Boolean: Is on bye this week?
player.recent_performance_data  # RecentPerformance object with L3W stats
player.performance_flags        # List of flag strings
player.enhancement_context      # Human-readable context message
player.adjusted_projection      # Reality-adjusted projection
```

**API Enhancement**: Added `sleeper_api.get_player_stats(season, week)` to fetch actual weekly performance data

**Example Output**:
```json
{
  "name": "Rico Dowdle",
  "position": "RB",
  "sleeper_projection": 4.0,
  "adjusted_projection": 14.8,
  "performance_flags": ["BREAKOUT_CANDIDATE", "TRENDING_UP"],
  "enhancement_context": "Recent breakout: averaging 18.5 pts over last 2 weeks (projection: 4.0)",
  "on_bye": false
}
```

```json
{
  "name": "Nico Collins",
  "position": "WR",
  "sleeper_projection": 0.0,
  "yahoo_projection": 0.0,
  "on_bye": true,
  "performance_flags": ["ON_BYE"],
  "enhancement_context": "Player is on bye Week 6",
  "expert_recommendation": "BYE WEEK - DO NOT START"
}
```

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
- **Role**: MCP server orchestration and protocol implementation
- **Functions**: Helper functions (discover_leagues, get_user_team_info, etc.)
- **Dependencies**: Coordinates between handlers, API layer, parsers, and services
- **Architecture**: Fully modularized - all handlers extracted to domain modules in `src/handlers/`
- **Pattern**: Dependency injection pattern via `inject_*_dependencies()` functions

**Key Helper Functions**:
- `discover_leagues()` - Detect all leagues for authenticated user via YAHOO_GUID
- `get_user_team_info()` - Find user's team in a specific league
- `get_user_team_key()` - Extract team key for league operations
- `get_all_teams_info()` - Retrieve all teams in a league for standings/comparison

## Critical Configuration

### Environment Variables (.env)
```env
YAHOO_CONSUMER_KEY=your_consumer_key_here
YAHOO_CONSUMER_SECRET=your_consumer_secret_here
YAHOO_ACCESS_TOKEN=your_access_token_here
YAHOO_REFRESH_TOKEN=your_refresh_token_here
YAHOO_GUID=your_yahoo_guid_here  # Required for multi-league support

# For remote MCP servers (Render deployment)
DEBUG=true
ALLOWED_CLIENT_IDS=*
ALLOWED_REDIRECT_URIS=*
OAUTH_CLIENT_SECRET=secure-secret-change-this-in-production
CORS_ORIGINS=*
RENDER_EXTERNAL_URL=https://your-app-name.onrender.com
```

### Claude Desktop Configuration (~/.claude/config.json)
```json
{
  "mcpServers": {
    "fantasy-football": {
      "command": "python",
      "args": [
        "/absolute/path/to/fantasy-football-mcp-server/fastmcp_server.py"
      ],
      "env": {
        "YAHOO_ACCESS_TOKEN": "your_access_token",
        "YAHOO_CONSUMER_KEY": "your_consumer_key",
        "YAHOO_CONSUMER_SECRET": "your_consumer_secret",
        "YAHOO_REFRESH_TOKEN": "your_refresh_token",
        "YAHOO_GUID": "your_yahoo_guid"
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

## MCP Prompts & Resources

The server exposes **13 prompt templates** and **10 resource guides** to help LLMs provide better fantasy football advice.

### Available Prompts (Pre-built Templates)

**Roster & Team Management:**
- `analyze_roster_strengths` - Evaluate roster depth, strengths, weaknesses
- `trade_evaluation` - Assess trade fairness and team fit
- `trade_proposal_generation` - Generate fair trade proposals between teams

**Weekly Strategy:**
- `start_sit_decision` - Start/sit recommendations with confidence levels
- `matchup_analysis` - Head-to-head matchup breakdowns
- `weekly_game_plan` - Complete weekly strategy and action plan

**Season Planning:**
- `bye_week_planning` - Multi-week bye week management strategy
- `playoff_preparation` - Championship preparation and roster optimization
- `season_long_strategy_check` - Overall season assessment and path to playoffs

**Player Management:**
- `waiver_wire_priority` - FAAB bids and waiver priority recommendations
- `injury_replacement_strategy` - Comprehensive injury replacement plans
- `streaming_dst_kicker` - Weekly streaming recommendations for DST/K

**Draft:**
- `draft_strategy_advice` - Pre-draft strategy based on league settings

### Available Resources (Reference Data)

**Configuration & Rules:**
- `config://scoring` - Standard/PPR scoring rules and point values
- `config://positions` - Position requirements and roster construction
- `config://strategies` - Draft strategies (Conservative, Balanced, Aggressive, Zero RB, etc.)

**Strategy Guides:**
- `guide://tool-selection` - Comprehensive tool usage guide for LLMs
- `guide://weekly-strategy` - Week-by-week strategic guidance (Early season → Playoffs)
- `guide://common-mistakes` - Common fantasy football mistakes to avoid
- `guide://playoff-strategies` - Championship preparation and playoff tactics
- `guide://dynasty-keeper` - Dynasty and keeper league strategies

**Data References:**
- `data://injury-status` - Injury designation meanings (Q, D, O, IR, etc.)
- `guide://advanced-stats` - Advanced metrics glossary (YPRR, target share, snap %, etc.)

### Using Prompts in Practice

Prompts provide pre-structured templates for common fantasy football questions:

```python
# Example: Get a start/sit recommendation prompt
prompt = start_sit_decision(
    league_key="461.l.61410",
    position="RB",
    player_names=["Derrick Henry", "Najee Harris", "James Conner"],
    week=5
)
# Returns a structured prompt asking for projections, matchup analysis,
# recent trends, injury status, etc. with clear output format
```

### Using Resources in Practice

Resources provide contextual knowledge that LLMs can reference:

```python
# Example: Access scoring rules for context
scoring = get_scoring_rules()
# Returns comprehensive scoring breakdown including PPR impact

# Example: Get playoff strategies
playoff_guide = get_playoff_strategies()
# Returns detailed playoff preparation checklist and strategies
```

### Benefits for LLMs

**Prompts enable:**
- Consistent output formatting across similar queries
- Comprehensive analysis checklists
- Confidence scoring and reasoning frameworks
- Multi-factor decision making

**Resources provide:**
- Domain knowledge without training data
- League-specific rule references
- Strategic frameworks and best practices
- Common pitfall awareness

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

## Testing & Development

### Running Tests
```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_waiver_wire.py -v

# Run with coverage report
pytest --cov=src --cov-report=html

# Run integration tests only (when available)
pytest -m integration

# Run live API tests (requires valid Yahoo credentials)
python test_live_api.py
```

### Test Files
- `test_live_api.py` - Live integration tests against Yahoo API (requires auth)
- `test_fixed_waiver.py` - Waiver wire functionality tests
- `tests/` - Pytest test suite with mocked API responses

## Git Workflow

Current branch: `main`

Commit format:
```bash
git commit -m "type: Description

Details here

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>"
```

Types: feat, fix, docs, style, refactor, test, chore

## Deployment Notes

### Authentication Setup
Before deploying or running locally, authenticate with Yahoo:
```bash
# Initial setup (interactive OAuth flow)
python setup_yahoo_auth.py

# Re-authenticate if tokens expire
python reauth_yahoo.py

# Refresh token only (automatic in server, manual if needed)
python refresh_yahoo_token.py
```

These scripts will update your `.env` file with valid credentials.

## Render Deployment

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