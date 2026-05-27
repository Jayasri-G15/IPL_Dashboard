from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from pipeline import (
    PipelineResult,
    build_batting_summary,
    build_bowling_summary,
    build_match_metrics,
    build_team_results,
    build_toss_summary,
    build_venue_summary,
    load_cricsheet_archive,
)


ROOT_DIR = Path(__file__).resolve().parent
STATIC_DIR = ROOT_DIR / "static"
DATASET_PATH = ROOT_DIR / "ipl_json.zip"


app = FastAPI(title="IPL Analytics Dashboard")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@lru_cache(maxsize=1)
def load_dataset() -> PipelineResult:
    return load_cricsheet_archive(DATASET_PATH)


def _records(df: pd.DataFrame) -> list[dict[str, object]]:
    if df.empty:
        return []
    return json.loads(df.to_json(orient="records"))


def _sanitize_selected(values: list[str], valid: list[str]) -> list[str]:
    valid_set = set(valid)
    return [value for value in values if value in valid_set]


def _available_teams(matches: pd.DataFrame) -> list[str]:
    if matches.empty:
        return []
    return sorted(pd.unique(matches[["team_1", "team_2"]].values.ravel("K")).tolist())


def _available_venues(matches: pd.DataFrame) -> list[str]:
    if matches.empty:
        return []
    return sorted(matches["venue"].dropna().astype(str).unique().tolist())


def _selected_frames(teams: list[str], venues: list[str]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    result = load_dataset()
    matches = result.matches.copy()
    deliveries = result.deliveries.copy()

    teams = _sanitize_selected(teams, _available_teams(matches))
    venues = _sanitize_selected(venues, _available_venues(matches))

    if teams:
        matches = matches[matches["team_1"].isin(teams) | matches["team_2"].isin(teams)]
        deliveries = deliveries[deliveries["batting_team"].isin(teams) | deliveries["bowling_team"].isin(teams)]
    if venues:
        matches = matches[matches["venue"].isin(venues)]
        deliveries = deliveries[deliveries["venue"].isin(venues)]

    match_metrics = build_match_metrics(matches, deliveries)
    return matches, deliveries, match_metrics


def _summarize_teams(matches: pd.DataFrame) -> pd.DataFrame:
    season_team = build_team_results(matches)
    if season_team.empty:
        return pd.DataFrame()

    summary = (
        season_team.groupby("team", dropna=False)
        .agg(
            matches=("matches", "sum"),
            decisive_matches=("decisive_matches", "sum"),
            wins=("wins", "sum"),
            losses=("losses", "sum"),
            tied_or_no_results=("tied_or_no_results", "sum"),
        )
        .reset_index()
    )
    summary["win_rate"] = summary["wins"] / summary["decisive_matches"].replace(0, pd.NA)
    return summary.sort_values(["win_rate", "wins", "matches"], ascending=[False, False, False])


def _summarize_batters(deliveries: pd.DataFrame) -> pd.DataFrame:
    summary = build_batting_summary(deliveries)
    if summary.empty:
        return pd.DataFrame()

    collapsed = (
        summary.groupby("batter", dropna=False)
        .agg(
            runs=("runs", "sum"),
            balls=("balls", "sum"),
            fours=("fours", "sum"),
            sixes=("sixes", "sum"),
            dismissals=("dismissals", "sum"),
            boundary_runs=("boundary_runs", "sum"),
        )
        .reset_index()
    )
    collapsed["strike_rate"] = collapsed["runs"] / collapsed["balls"].replace(0, pd.NA) * 100
    collapsed["average"] = collapsed["runs"] / collapsed["dismissals"].replace(0, pd.NA)
    return collapsed.sort_values(["runs", "strike_rate"], ascending=[False, False])


def _summarize_bowlers(deliveries: pd.DataFrame) -> pd.DataFrame:
    summary = build_bowling_summary(deliveries)
    if summary.empty:
        return pd.DataFrame()

    collapsed = (
        summary.groupby("bowler", dropna=False)
        .agg(
            balls=("balls", "sum"),
            runs_conceded=("runs_conceded", "sum"),
            wickets=("wickets", "sum"),
        )
        .reset_index()
    )
    collapsed["economy"] = collapsed["runs_conceded"] / (collapsed["balls"] / 6).replace(0, pd.NA)
    collapsed["average"] = collapsed["runs_conceded"] / collapsed["wickets"].replace(0, pd.NA)
    collapsed["strike_rate"] = collapsed["balls"] / collapsed["wickets"].replace(0, pd.NA)
    return collapsed.sort_values(["wickets", "economy"], ascending=[False, True])


def _top_scorers_by_season(deliveries: pd.DataFrame) -> pd.DataFrame:
    scorers = build_batting_summary(deliveries)
    if scorers.empty:
        return pd.DataFrame()

    return (
        scorers.sort_values(["season", "runs"], ascending=[True, False])
        .groupby("season", as_index=False, sort=False)
        .head(1)
        .loc[:, ["season", "batter", "runs"]]
        .rename(columns={"batter": "top_scorer", "runs": "top_scorer_runs"})
    )


def _top_bowlers_by_season(deliveries: pd.DataFrame) -> pd.DataFrame:
    bowlers = build_bowling_summary(deliveries)
    if bowlers.empty:
        return pd.DataFrame()

    return (
        bowlers.sort_values(["season", "wickets", "economy"], ascending=[True, False, True])
        .groupby("season", as_index=False, sort=False)
        .head(1)
        .loc[:, ["season", "bowler", "wickets"]]
        .rename(columns={"bowler": "top_bowler", "wickets": "top_bowler_wickets"})
    )


def _dashboard_payload(matches: pd.DataFrame, deliveries: pd.DataFrame, match_metrics: pd.DataFrame) -> dict[str, object]:
    team_season = build_team_results(matches)
    teams = _summarize_teams(matches)
    batters = _summarize_batters(deliveries)
    bowlers = _summarize_bowlers(deliveries)
    venue_summary = build_venue_summary(match_metrics)
    toss_overall = build_toss_summary(match_metrics)

    toss_summary = pd.DataFrame()
    if not toss_overall.empty:
        toss_summary = (
            toss_overall.groupby("toss_decision", dropna=False)
            .agg(
                matches=("matches", "sum"),
                decisive_matches=("decisive_matches", "sum"),
                toss_winner_wins=("toss_winner_wins", "sum"),
            )
            .reset_index()
        )
        toss_summary["win_rate"] = toss_summary["toss_winner_wins"] / toss_summary["decisive_matches"].replace(0, pd.NA)

    metrics = {
        "matches": int(len(matches)),
        "seasons": int(matches["season"].nunique()) if not matches.empty else 0,
        "teams": int(pd.unique(matches[["team_1", "team_2"]].values.ravel("K")).size) if not matches.empty else 0,
        "players": int(pd.unique(pd.concat([deliveries["batter"], deliveries["bowler"]], ignore_index=True)).size) if not deliveries.empty else 0,
        "tossWinRate": float(match_metrics["toss_winner_won"].sum() / len(match_metrics)) if len(match_metrics) else 0.0,
    }

    return {
        "metrics": metrics,
        "teams": _records(teams),
        "teamSeason": _records(team_season),
        "batters": _records(batters),
        "bowlers": _records(bowlers),
        "toss": _records(toss_summary),
        "tossSeason": _records(toss_overall),
        "venues": _records(venue_summary),
    }


def _top_batting_innings(matches: pd.DataFrame, deliveries: pd.DataFrame) -> list[dict[str, object]]:
    merged = deliveries.merge(matches[["match_id", "team_1", "team_2"]], on="match_id", how="left")
    merged["is_four"] = merged["runs_batter"].eq(4)
    merged["is_six"] = merged["runs_batter"].eq(6)
    innings = (
        merged.groupby(["match_id", "batter", "batting_team", "season", "team_1", "team_2"], dropna=False)
        .agg(
            runs=("runs_batter", "sum"),
            balls=("legal_delivery", "sum"),
            fours=("is_four", "sum"),
            sixes=("is_six", "sum"),
        )
        .reset_index()
    )
    innings["strike_rate"] = innings["runs"] / innings["balls"].replace(0, pd.NA) * 100
    innings = innings.sort_values(["runs", "strike_rate"], ascending=[False, False]).head(10)
    return _records(innings)


def _highest_team_totals(match_metrics: pd.DataFrame) -> list[dict[str, object]]:
    if match_metrics.empty:
        return []
    totals = (
        match_metrics.loc[:, ["match_id", "season", "venue", "first_innings_runs", "first_innings_batting_team", "team_1", "team_2"]]
        .rename(columns={"first_innings_runs": "total", "first_innings_batting_team": "batting_team"})
        .sort_values(["total", "season"], ascending=[False, False])
        .head(10)
    )
    return _records(totals)


def _best_bowling_figures(deliveries: pd.DataFrame) -> list[dict[str, object]]:
    figures = (
        deliveries.groupby(["match_id", "bowler", "season", "venue"], dropna=False)
        .agg(
            wickets=("bowler_wickets", "sum"),
            runs=("bowler_runs_conceded", "sum"),
            balls=("legal_delivery", "sum"),
        )
        .reset_index()
    )
    figures["economy"] = figures["runs"] / (figures["balls"] / 6).replace(0, pd.NA)
    figures = figures.sort_values(["wickets", "economy"], ascending=[False, True]).head(10)
    return _records(figures)


def _top_scorers_for_seasons(deliveries: pd.DataFrame) -> pd.DataFrame:
    scorers = build_batting_summary(deliveries)
    if scorers.empty:
        return pd.DataFrame()
    return (
        scorers.sort_values(["season", "runs"], ascending=[True, False])
        .groupby("season", as_index=False, sort=False)
        .head(1)
        .loc[:, ["season", "batter", "runs"]]
        .rename(columns={"batter": "top_scorer", "runs": "top_scorer_runs"})
    )


def _top_bowlers_for_seasons(deliveries: pd.DataFrame) -> pd.DataFrame:
    bowlers = build_bowling_summary(deliveries)
    if bowlers.empty:
        return pd.DataFrame()
    return (
        bowlers.sort_values(["season", "wickets", "economy"], ascending=[True, False, True])
        .groupby("season", as_index=False, sort=False)
        .head(1)
        .loc[:, ["season", "bowler", "wickets"]]
        .rename(columns={"bowler": "top_bowler", "wickets": "top_bowler_wickets"})
    )


def _seasons_payload(matches: pd.DataFrame, deliveries: pd.DataFrame) -> dict[str, object]:
    seasons = pd.DataFrame({"season": sorted(matches["season"].dropna().astype(str).unique().tolist())})
    if seasons.empty:
        return {"seasons": []}

    counts = matches.groupby("season", dropna=False).size().reset_index(name="matches")
    avg_runs = (
        build_match_metrics(matches, deliveries)
        .groupby("season", dropna=False)["first_innings_runs"]
        .mean()
        .reset_index(name="avg_runs")
        if not matches.empty and not deliveries.empty
        else pd.DataFrame()
    )

    seasons = seasons.merge(counts, on="season", how="left")
    seasons = seasons.merge(_top_scorers_for_seasons(deliveries), on="season", how="left")
    seasons = seasons.merge(_top_bowlers_for_seasons(deliveries), on="season", how="left")
    if not avg_runs.empty:
        seasons = seasons.merge(avg_runs, on="season", how="left")
    return {"seasons": _records(seasons)}


@app.get("/", include_in_schema=False)
def home() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/options")
def options() -> dict[str, list[str]]:
    result = load_dataset()
    return {
        "teams": _available_teams(result.matches),
        "venues": _available_venues(result.matches),
    }


@app.get("/api/dashboard")
def dashboard(
    teams: list[str] = Query(default=[]),
    venues: list[str] = Query(default=[]),
) -> dict[str, object]:
    matches, deliveries, match_metrics = _selected_frames(teams, venues)
    return _dashboard_payload(matches, deliveries, match_metrics)


@app.get("/api/records")
def records() -> dict[str, object]:
    result = load_dataset()
    return {
        "topInnings": _top_batting_innings(result.matches, result.deliveries),
        "topTotals": _highest_team_totals(build_match_metrics(result.matches, result.deliveries)),
        "topBowling": _best_bowling_figures(result.deliveries),
    }


@app.get("/api/seasons")
def seasons() -> dict[str, object]:
    result = load_dataset()
    return _seasons_payload(result.matches, result.deliveries)


@app.post("/api/chat")
def chat(payload: dict[str, object]) -> dict[str, str]:
    result = load_dataset()
    matches = result.matches
    deliveries = result.deliveries

    question = str(payload.get("question", "")).strip().lower()
    if not question:
        return {"answer": "Ask me about teams, players, seasons, or records."}

    team_summary = _summarize_teams(matches)
    batting_summary = _summarize_batters(deliveries)
    bowling_summary = _summarize_bowlers(deliveries)

    if any(keyword in question for keyword in ["most title", "won the most", "most wins", "best team"]):
        if not team_summary.empty:
            top = team_summary.iloc[0]
            return {"answer": f"{top['team']} leads the dataset with {int(top['wins'])} wins and a {float(top['win_rate']):.1%} win rate."}

    if any(keyword in question for keyword in ["most run", "top scorer", "highest scorer", "best batter"]):
        if not batting_summary.empty:
            top = batting_summary.iloc[0]
            return {"answer": f"{top['batter']} is the top scorer here with {int(top['runs'])} runs and a strike rate of {float(top['strike_rate']):.1f}."}

    if any(keyword in question for keyword in ["most wicket", "top bowler", "best bowler"]):
        if not bowling_summary.empty:
            top = bowling_summary.iloc[0]
            return {"answer": f"{top['bowler']} leads the bowling charts with {int(top['wickets'])} wickets and an economy rate of {float(top['economy']):.2f}."}

    metrics = _dashboard_payload(matches, deliveries, build_match_metrics(matches, deliveries))["metrics"]
    return {
        "answer": (
            f"This IPL dashboard covers {metrics['matches']} matches across {metrics['seasons']} seasons. "
            f"Try asking about the top team, top scorer, or top bowler."
        )
    }


@app.get("/{path:path}", include_in_schema=False)
def spa_fallback(path: str) -> FileResponse:
    candidate = STATIC_DIR / path
    if path and candidate.is_file():
        return FileResponse(candidate)
    return FileResponse(STATIC_DIR / "index.html")
