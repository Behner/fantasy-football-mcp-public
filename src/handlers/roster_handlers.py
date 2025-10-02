"""Roster MCP tool handlers."""

from typing import Any, Dict, List

# These will be injected from main file
get_user_team_info = None
yahoo_api_call = None
parse_team_roster = None


async def handle_ff_get_roster(arguments: dict) -> dict:
    """Get roster for a team with optional enhanced data.

    Args:
        arguments: Dict containing:
            - league_key: League identifier
            - team_key: Team identifier (optional, will auto-detect user's team)
            - data_level: "basic", "standard", or "enhanced" (default: "basic")
            - include_projections: Include projection data (default: True)
            - include_external_data: Include Sleeper API data (default: True)
            - include_analysis: Include analysis (default: True)
            - week: Specific week (optional)

    Returns:
        Dict with roster data and optional enhancements
    """
    league_key = arguments.get("league_key")
    team_key = arguments.get("team_key")
    data_level = arguments.get("data_level", "basic")
    include_projections = arguments.get("include_projections", True)
    include_external_data = arguments.get("include_external_data", True)
    include_analysis = arguments.get("include_analysis", True)
    week = arguments.get("week")

    if data_level == "basic":
        effective_projections = False
        effective_external = False
        effective_analysis = False
    elif data_level == "standard":
        effective_projections = True
        effective_external = False
        effective_analysis = False
    else:
        effective_projections = True
        effective_external = True
        effective_analysis = True

    if not include_projections:
        effective_projections = False
    if not include_external_data:
        effective_external = False
    if not include_analysis:
        effective_analysis = False

    needs_enhanced = effective_projections or effective_external or effective_analysis

    team_info = None
    if not team_key:
        team_info = await get_user_team_info(league_key)
        if team_info:
            team_key = team_info.get("team_key")
        else:
            return {
                "error": f"Could not find your team in league {league_key}",
                "suggestion": "Provide team_key explicitly if multiple teams exist",
            }

    data = await yahoo_api_call(f"team/{team_key}/roster")
    roster = parse_team_roster(data)

    if not roster:
        print(
            f"DEBUG: Empty roster for team {team_key}. Raw data keys: {list(data.keys()) if data else 'None'}"
        )
        if data:
            import json

            print("DEBUG: Truncated raw data:", json.dumps(data, indent=2)[:2000])

    if team_info is None or team_info.get("team_key") != team_key:
        team_info = await get_user_team_info(league_key)

    result: dict[str, Any] = {
        "status": "success",
        "league_key": league_key,
        "team_key": team_key,
        "team_name": team_info.get("team_name") if team_info else None,
        "draft_position": team_info.get("draft_position") if team_info else None,
        "draft_grade": team_info.get("draft_grade") if team_info else None,
        "roster": roster,
    }

    if not roster and data:
        result["debug_info"] = {
            "raw_response_keys": list(data.keys()),
            "fantasy_content_present": "fantasy_content" in data,
            "team_structure": str(type(data.get("fantasy_content", {}).get("team", []))),
            "note": "Empty roster - possibly off-season or parsing variation. Check logs for raw data.",
        }

    if not needs_enhanced:
        return result

    try:
        from lineup_optimizer import lineup_optimizer, Player  # type: ignore
    except ImportError as exc:
        result["note"] = f"Enhanced view unavailable: {exc}"
        return result

    try:
        optimizer_payload = {
            "league_key": league_key,
            "team_key": team_key,
            "roster": roster,
        }
        players = await lineup_optimizer.parse_yahoo_roster(optimizer_payload)
        if not players:
            raise ValueError("No players parsed from roster payload")
        players = await lineup_optimizer.enhance_with_external_data(players, week=week)
    except Exception as exc:
        result["note"] = f"Enhanced view unavailable: {exc}"
        return result

    def serialize_player(player: Player) -> Dict[str, Any]:
        base = {
            "name": player.name,
            "position": player.position,
            "team": player.team,
            "opponent": player.opponent,
            "status": player.status,
            "yahoo_projection": player.yahoo_projection if effective_projections else None,
            "sleeper_projection": player.sleeper_projection if effective_external else None,
            "sleeper_id": player.sleeper_id if effective_external else None,
            "sleeper_match_method": player.sleeper_match_method if effective_external else None,
            "floor_projection": player.floor_projection if effective_projections else None,
            "ceiling_projection": player.ceiling_projection if effective_projections else None,
            "consistency_score": player.consistency_score,
            "player_tier": player.player_tier,
            "matchup_score": player.matchup_score if effective_external else None,
            "matchup_description": player.matchup_description if effective_external else None,
            "trending_score": player.trending_score if effective_external else None,
            "risk_level": player.risk_level,
            # Expert advice fields
            "expert_tier": player.expert_tier if effective_external else None,
            "expert_recommendation": player.expert_recommendation if effective_external else None,
            "expert_confidence": player.expert_confidence if effective_external else None,
            "expert_advice": player.expert_advice if effective_external else None,
            "search_rank": player.search_rank if effective_external else None,
        }

        # Add analysis if flagged
        if effective_analysis:
            total_proj = (player.yahoo_projection or 0) + (player.sleeper_projection or 0)
            base["roster_analysis"] = {
                "projected_points": round(total_proj, 1),
                "tier_summary": f"{player.player_tier} tier player",
                "start_recommendation": "Start" if total_proj > 10 else "Bench/Consider",
            }

        return base

    players_by_position: Dict[str, List[Dict[str, Any]]] = {}
    for player in players:
        bucket = players_by_position.setdefault(player.position, [])
        bucket.append(serialize_player(player))

    for bucket in players_by_position.values():
        bucket.sort(key=lambda entry: entry.get("yahoo_projection", 0), reverse=True)

    result.update(
        {
            "total_players": len(players),
            "players_by_position": players_by_position,
            "all_players": [serialize_player(player) for player in players],
            "analysis_context": {
                "data_sources": ["Yahoo"] + (["Sleeper"] if effective_external else []),
                "data_level": data_level,
                "includes": {
                    "projections": effective_projections,
                    "external_data": effective_external,
                    "analysis": effective_analysis,
                },
                "week": week or "current",
                "enhancement_features": (
                    [
                        "Expert tiers and recommendations",
                        "Position rankings and confidence scores",
                        "Risk assessment and trending data",
                        "Sleeper player matching and IDs",
                    ]
                    if effective_external
                    else []
                ),
            },
        }
    )

    # Add overall analysis if flagged
    if effective_analysis:
        total_proj = sum(p.get("projected_points", 0) for p in result["all_players"])
        starters_count = sum(1 for pos in players_by_position if pos not in ["BN", "IR"])
        result["overall_analysis"] = {
            "total_projected_points": round(total_proj, 1),
            "starters_count": starters_count,
            "recommendation": (
                f"Strong lineup with {total_proj:.1f} projected points"
                if total_proj > 150
                else "Consider upgrades"
            ),
        }

    return result
