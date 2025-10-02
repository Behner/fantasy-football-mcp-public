# Fantasy Football FastMCP Server

A production-ready Model Context Protocol (MCP) server for Yahoo Fantasy Football
with advanced lineup optimization, multi-league support, and comprehensive analytics.

## Features

- **Multi-League Support** – Automatically discovers and manages all Yahoo Fantasy
  Football leagues for the authenticated account
- **Advanced Lineup Optimization** – Sophisticated algorithm with position
  normalization, matchup analysis, and strategy-based recommendations
- **Complete League Operations** – Standings, rosters, matchups, waiver wire,
  draft tools, and Reddit sentiment analysis
- **FastMCP Native** – Single entry point (`fastmcp_server.py`) with HTTP/SSE
  transport for Claude Desktop and fastmcp.cloud
- **Production Ready** – Rate limiting, caching, automatic token refresh, and
  comprehensive error handling

## Available MCP Tools

### League & Team Management
- `ff_get_leagues` – List all leagues tied to the authenticated Yahoo account.
- `ff_get_league_info` – Retrieve metadata and your team summary for a league.
- `ff_get_standings` – View league standings with wins, losses and points.
- `ff_get_roster` – Inspect roster details for the logged-in team or a specific
  team key.
- `ff_get_matchup` – Review matchup information for a given week.
- `ff_compare_teams` – Compare two teams' rosters inside a league.
- `ff_build_lineup` – Build optimal lineup using strategy-based optimization and
  positional constraints.

### Player Discovery & Draft
- `ff_get_players` – Browse current free agents with ownership context.
- `ff_get_waiver_wire` – Surface top waiver targets with Yahoo stats. (Default: 30 players for comprehensive analysis)
- `ff_get_draft_rankings` – Pull Yahoo pre-draft rankings and ADP data.
- `ff_get_draft_results` – Review draft positions, grades and summary by team.
- `ff_get_draft_recommendation` – Strategy-aware draft pick suggestions.
- `ff_analyze_draft_state` – Summarize positional needs and strategy during a
  draft.
- `ff_analyze_reddit_sentiment` – Gather public sentiment and injury chatter
  from Reddit for one or more players.

### Operations & Maintenance
- `ff_get_api_status` – Check cache metrics and Yahoo rate limiting state.
- `ff_clear_cache` – Clear cached Yahoo responses (optionally by pattern).
- `ff_refresh_token` – Refresh the Yahoo OAuth access token on demand.

## Installation

```bash
git clone https://github.com/derekrbreese/fantasy-football-mcp.git
cd fantasy-football-mcp
pip install -r requirements.txt
```

## Configuration

Create a `.env` file (or configure environment variables in your deployment)
with the Yahoo credentials:

```env
YAHOO_CONSUMER_KEY=your_consumer_key
YAHOO_CONSUMER_SECRET=your_consumer_secret
YAHOO_ACCESS_TOKEN=your_access_token
YAHOO_REFRESH_TOKEN=your_refresh_token
YAHOO_GUID=your_yahoo_guid
```

## Running Locally

### Option 1: Direct Python (for development)
```bash
python fastmcp_server.py
```

### Option 2: Claude Desktop Integration
Add to `~/.claude/config.json`:
```json
{
  "mcpServers": {
    "fantasy-football": {
      "command": "python",
      "args": ["/path/to/fantasy-football-mcp-server/fastmcp_server.py"]
    }
  }
}
```

### Option 3: Using the helper script
```bash
./run_local_mcp.sh
```

## Deployment

### Render (Recommended)
```bash
./deploy_to_render.sh
```

The server auto-deploys from the `main` branch. Configure environment variables
in the Render dashboard.

### fastmcp.cloud
1. Connect your GitHub repository
2. Set start command: `python fastmcp_server.py`
3. Configure Yahoo environment variables
4. Deploy

### Docker
```bash
docker build -t fantasy-football-mcp .
docker run -p 8080:8080 --env-file .env fantasy-football-mcp
```

## Testing

Run the full automated suite with:

```bash
pytest
```

The tests exercise each FastMCP tool wrapper and the HTTP runner while mocking
out remote Yahoo API calls to keep the suite fast and deterministic.

## Project Structure

```
fantasy-football-mcp/
├── fastmcp_server.py                    # Main FastMCP server entry point
├── fantasy_football_multi_league.py     # Core tool implementations
├── lineup_optimizer.py                  # Advanced lineup optimization engine
├── matchup_analyzer.py                  # Defensive matchup analysis
├── position_normalizer.py               # Position-based value calculations
├── sleeper_api.py                       # Sleeper API integration
├── yahoo_api_utils.py                   # Rate limiting and caching
├── requirements.txt                     # Python dependencies
├── src/                                 # Supporting modules
│   ├── agents/                          # Optimization and analysis agents
│   ├── models/                          # Data models and schemas
│   ├── strategies/                      # Draft and lineup strategies
│   └── utils/                           # Utility functions
├── tests/                               # Test suite
├── config/                              # Configuration management
└── utils/                               # Authentication scripts
```

## Authentication Flow

1. Authenticate with Yahoo once using `reauth_yahoo.py` or the included scripts.
2. Store credentials as environment variables for the server.
3. Use the `ff_refresh_token` tool whenever an access token expires to obtain a
   new one automatically.

## Troubleshooting

- **Only one league showing** – Verify `YAHOO_GUID` and ensure leagues are
  active in the current season.
- **Authentication errors** – Confirm tokens and consumer keys are correct and
  refresh tokens have not been revoked.
- **Stale results** – Use `ff_clear_cache` or inspect `ff_get_api_status` for
  cache hit rates and rate limiting signals.

## License

MIT
