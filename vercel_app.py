from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

import pandas as pd
import plotly
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
PLOTLY_BUNDLE = Path(plotly.__file__).resolve().parent / "package_data" / "plotly.min.js"

IPL_CHAMPIONS = {
    "2007/08": "Rajasthan Royals",
    "2009": "Deccan Chargers",
    "2010": "Chennai Super Kings",
    "2011": "Chennai Super Kings",
    "2012": "Kolkata Knight Riders",
    "2013": "Mumbai Indians",
    "2014": "Kolkata Knight Riders",
    "2015": "Mumbai Indians",
    "2016": "Sunrisers Hyderabad",
    "2017": "Mumbai Indians",
    "2018": "Chennai Super Kings",
    "2019": "Mumbai Indians",
    "2020": "Mumbai Indians",
    "2021": "Chennai Super Kings",
    "2022": "Gujarat Titans",
    "2023": "Chennai Super Kings",
    "2024": "Kolkata Knight Riders",
}

IPL_FACTS = [
    (
        ["what is the ipl", "what is ipl", "tell me about ipl", "ipl meaning", "about ipl"],
        "The Indian Premier League is a franchise T20 cricket tournament with a 20-over innings format, playoffs, and a final to decide the champion.",
    ),
    (
        ["powerplay", "first 6 overs"],
        "The powerplay is the first 6 overs of an innings, when fielding restrictions make scoring opportunities more open.",
    ),
    (
        ["super over"],
        "A Super Over is a one-over tie-breaker used when a match finishes level and a winner has to be decided.",
    ),
    (
        ["orange cap", "most runs in a season"],
        "The Orange Cap goes to the batter with the most runs in a season.",
    ),
    (
        ["purple cap", "most wickets in a season"],
        "The Purple Cap goes to the bowler with the most wickets in a season.",
    ),
    (
        ["net run rate", "nrr"],
        "Net Run Rate is a tournament tiebreak metric based on runs scored and conceded per over across the season.",
    ),
    (
        ["auction"],
        "The IPL auction is the player market where franchises bid for players before a season, subject to squad rules and salary constraints.",
    ),
    (
        ["playoff", "final"],
        "The IPL playoff stage usually includes Qualifier 1, the Eliminator, Qualifier 2, and the Final.",
    ),
    (
        ["drs"],
        "DRS is the Decision Review System, which teams use to challenge on-field umpire decisions within the allowed review rules.",
    ),
    (
        ["retention", "retained players"],
        "Retention lets franchises keep selected players before an auction, using league-defined retention rules for that cycle.",
    ),
    (
        ["point table", "points table"],
        "Teams earn points for wins during the league stage, and the points table is typically separated using points, net run rate, and wins.",
    ),
]

TEAM_ABBREVIATIONS = {
    "csk": "Chennai Super Kings",
    "mi": "Mumbai Indians",
    "rcb": "Royal Challengers Bengaluru",
    "kkr": "Kolkata Knight Riders",
    "rr": "Rajasthan Royals",
    "dc": "Delhi Capitals",
    "srh": "Sunrisers Hyderabad",
    "pbks": "Punjab Kings",
    "gt": "Gujarat Titans",
    "lsg": "Lucknow Super Giants",
    "kxip": "Kings XI Punjab",
    "dd": "Delhi Daredevils",
    "rps": "Rising Pune Supergiants",
    "dc2": "Deccan Chargers",
    "gl": "Gujarat Lions",
    "pw": "Pune Warriors",
    "ktk": "Kochi Tuskers Kerala",
}

PLAYER_ALIASES = {
    "virat kohli": "V Kohli",
    "kohli": "V Kohli",
    "rohit sharma": "RG Sharma",
    "rohit": "RG Sharma",
    "ms dhoni": "MS Dhoni",
    "dhoni": "MS Dhoni",
    "mahendra singh dhoni": "MS Dhoni",
    "chris gayle": "CH Gayle",
    "gayle": "CH Gayle",
    "ab de villiers": "AB de Villiers",
    "abd": "AB de Villiers",
    "suresh raina": "SK Raina",
    "raina": "SK Raina",
    "shikhar dhawan": "S Dhawan",
    "dhawan": "S Dhawan",
    "david warner": "DA Warner",
    "warner": "DA Warner",
    "kl rahul": "KL Rahul",
    "rahul": "KL Rahul",
    "ravindra jadeja": "RA Jadeja",
    "jadeja": "RA Jadeja",
    "jasprit bumrah": "JJ Bumrah",
    "bumrah": "JJ Bumrah",
    "hardik pandya": "HH Pandya",
    "pandya": "HH Pandya",
    "kieron pollard": "KA Pollard",
    "pollard": "KA Pollard",
}


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


def _normalize_text(value: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", str(value).lower()).replace("  ", " ").strip()


def _question_years(question: str) -> list[str]:
    return re.findall(r"20\d{2}(?:/\d{2})?", question)


def _name_tokens(name: str) -> list[str]:
    return [token for token in _normalize_text(name).split() if len(token) > 2]


def _match_explicit_name(question: str, candidates: list[str], aliases: dict[str, str]) -> str | None:
    normalized_question = f" {_normalize_text(question)} "
    if not candidates:
        return None

    for alias, canonical in aliases.items():
        if f" {alias} " in normalized_question and canonical in candidates:
            return canonical

    exact_matches = [candidate for candidate in candidates if f" {_normalize_text(candidate)} " in normalized_question]
    if exact_matches:
        return sorted(exact_matches, key=len, reverse=True)[0]

    return None


def _match_player(question: str, candidates: list[str]) -> str | None:
    return _match_explicit_name(question, candidates, PLAYER_ALIASES)


def _match_team(question: str, candidates: list[str]) -> str | None:
    return _match_explicit_name(question, candidates, TEAM_ABBREVIATIONS)


def _match_venue(question: str, candidates: list[str]) -> str | None:
    normalized_question = f" {_normalize_text(question)} "
    for candidate in candidates:
        if f" {_normalize_text(candidate)} " in normalized_question:
            return candidate
    return None


def _all_time_team_summary(matches: pd.DataFrame) -> pd.DataFrame:
    summary = _summarize_teams(matches)
    return summary if not summary.empty else pd.DataFrame()


def _team_profile(team: str, matches: pd.DataFrame, deliveries: pd.DataFrame) -> str:
    team_rows = matches[(matches["team_1"] == team) | (matches["team_2"] == team)]
    if team_rows.empty:
        return f"I couldn't find any IPL data for {team}."

    wins = int((team_rows["winner"] == team).sum())
    decisive = int(team_rows["winner"].astype(str).str.len().gt(0).sum())
    win_rate = wins / decisive if decisive else 0.0

    batting = deliveries[deliveries["batting_team"] == team]
    bowling = deliveries[deliveries["bowling_team"] == team]

    batter_summary = _summarize_batters(batting)
    bowler_summary = _summarize_bowlers(bowling)
    top_batter = batter_summary.iloc[0] if not batter_summary.empty else None
    top_bowler = bowler_summary.iloc[0] if not bowler_summary.empty else None
    latest_season = str(team_rows["season"].dropna().astype(str).sort_values().iloc[-1]) if team_rows["season"].notna().any() else "unknown"

    parts = [
        f"{team} has played {len(team_rows)} matches in the loaded IPL archive and won {wins} of its decisive matches ({win_rate:.1%}).",
        f"The latest season captured in this dataset for them is {latest_season}.",
    ]
    if top_batter is not None:
        parts.append(f"Top batter in this dataset: {top_batter['batter']} with {int(top_batter['runs'])} runs.")
    if top_bowler is not None:
        parts.append(f"Top bowler in this dataset: {top_bowler['bowler']} with {int(top_bowler['wickets'])} wickets.")
    return " ".join(parts)


def _player_profile(player: str, deliveries: pd.DataFrame) -> str:
    batting = _summarize_batters(deliveries)
    bowling = _summarize_bowlers(deliveries)
    batter_row = batting[batting["batter"] == player]
    bowler_row = bowling[bowling["bowler"] == player]

    if batter_row.empty and bowler_row.empty:
        return f"I couldn't find {player} in the loaded IPL dataset. Try a different spelling or ask about a team, season, venue, or record."

    parts: list[str] = []
    if not batter_row.empty:
        row = batter_row.iloc[0]
        parts.append(f"{player} has scored {int(row['runs'])} runs in the loaded IPL archive at a strike rate of {float(row['strike_rate']):.1f} and an average of {float(row['average']):.1f}.")
    if not bowler_row.empty:
        row = bowler_row.iloc[0]
        parts.append(f"As a bowler, {player} has taken {int(row['wickets'])} wickets at an economy of {float(row['economy']):.2f}.")
    return " ".join(parts)


def _venue_profile(venue: str, match_metrics: pd.DataFrame) -> str:
    venue_rows = match_metrics[match_metrics["venue"] == venue]
    if venue_rows.empty:
        return f"I couldn't find {venue} in the loaded venue list."

    average_runs = float(venue_rows["first_innings_runs"].mean())
    chase_rate = float(venue_rows["chasing_won"].sum() / len(venue_rows)) if len(venue_rows) else 0.0
    bat_first_rate = float(venue_rows["batting_first_won"].sum() / len(venue_rows)) if len(venue_rows) else 0.0
    return (
        f"{venue} has {len(venue_rows)} matches in this archive. Average first-innings score: {average_runs:.1f}. "
        f"Chasing win rate: {chase_rate:.1%}. Bat-first win rate: {bat_first_rate:.1%}."
    )


def _season_profile(season: str, matches: pd.DataFrame, deliveries: pd.DataFrame) -> str:
    season_matches = matches[matches["season"].astype(str) == season]
    if season_matches.empty:
        return f"I couldn't find a season labeled {season} in the loaded IPL archive."

    champion = IPL_CHAMPIONS.get(season)
    top_scorer = _top_scorers_for_seasons(deliveries)
    top_bowler = _top_bowlers_for_seasons(deliveries)
    scorer_row = top_scorer[top_scorer["season"].astype(str) == season]
    bowler_row = top_bowler[top_bowler["season"].astype(str) == season]

    parts = [f"Season {season} in this archive includes {len(season_matches)} matches."]
    if champion:
        parts.append(f"Champion: {champion}.")
    if not scorer_row.empty:
        row = scorer_row.iloc[0]
        parts.append(f"Top scorer: {row['top_scorer']} with {int(row['top_scorer_runs'])} runs.")
    if not bowler_row.empty:
        row = bowler_row.iloc[0]
        parts.append(f"Top bowler: {row['top_bowler']} with {int(row['top_bowler_wickets'])} wickets.")
    return " ".join(parts)


def _match_fact(question: str) -> str | None:
    normalized_question = _normalize_text(question)
    for keywords, answer in IPL_FACTS:
        if any(keyword in normalized_question for keyword in keywords):
            return answer
    return None


def _champion_answer(question: str, matches: pd.DataFrame) -> str | None:
    normalized_question = _normalize_text(question)
    if not any(keyword in normalized_question for keyword in ["won", "winner", "champion", "title", "trophy", "who won"]):
        return None

    years = _question_years(question)
    if years:
        season = years[-1]
        if season in IPL_CHAMPIONS:
            return f"The IPL champion in {season} was {IPL_CHAMPIONS[season]}."
        return None

    if "all" in normalized_question and "time" in normalized_question:
        return "Recent IPL champions in the loaded archive are: " + ", ".join(f"{season}: {champion}" for season, champion in IPL_CHAMPIONS.items()) + "."

    all_time_wins = _all_time_team_summary(matches)
    if not all_time_wins.empty:
        top = all_time_wins.iloc[0]
        return f"{top['team']} leads the archive by all-time wins with {int(top['wins'])} victories and a {float(top['win_rate']):.1%} win rate."
    return None


def _title_counts() -> pd.DataFrame:
    counts = pd.Series(list(IPL_CHAMPIONS.values()), dtype="string").value_counts().reset_index()
    counts.columns = ["team", "titles"]
    return counts.sort_values(["titles", "team"], ascending=[False, True])


def _best_venue_by_metric(match_metrics: pd.DataFrame, metric: str, label: str) -> str | None:
    venue_summary = build_venue_summary(match_metrics)
    if venue_summary.empty:
        return None
    filtered = venue_summary[venue_summary["matches"] >= 10]
    top_rows = filtered if not filtered.empty else venue_summary
    top = top_rows.sort_values([metric, "matches"], ascending=[False, False]).iloc[0]
    value = float(top[metric])
    formatted = f"{value:.1%}" if "rate" in metric else f"{value:.1f}"
    return f"{top['venue']} is the leading {label} venue in this archive with {formatted} across {int(top['matches'])} matches."


def _answer_knowledge_question(question: str, matches: pd.DataFrame, deliveries: pd.DataFrame, match_metrics: pd.DataFrame) -> str:
    normalized_question = _normalize_text(question)
    fact = _match_fact(question)
    if fact:
        return fact

    if any(keyword in normalized_question for keyword in ["who has won the most titles", "most titles", "title leader", "championship leader"]):
        titles = _title_counts()
        if not titles.empty:
            top = titles.iloc[0]
            return f"{top['team']} leads the IPL title count in the archive with {int(top['titles'])} titles."

    champion = _champion_answer(question, matches)
    if champion:
        return champion

    if any(keyword in normalized_question for keyword in ["best venue for chasing", "venue is best for chasing", "which venue is best for chasing", "best chasing venue"]):
        best = _best_venue_by_metric(match_metrics, "chasing_win_rate", "chasing")
        if best:
            return best

    if any(keyword in normalized_question for keyword in ["highest scoring venue", "best batting venue", "best venue for batting"]):
        best = _best_venue_by_metric(match_metrics, "avg_first_innings_runs", "batting")
        if best:
            return best

    all_teams = _available_teams(matches)
    all_players = sorted(pd.unique(pd.concat([deliveries["batter"], deliveries["bowler"]], ignore_index=True).dropna().astype(str)).tolist()) if not deliveries.empty else []
    all_venues = _available_venues(matches)

    if any(keyword in normalized_question for keyword in ["team", "franchise", "squad", "club"]):
        team = _match_team(question, all_teams)
        if team:
            return _team_profile(team, matches, deliveries)

    if any(keyword in normalized_question for keyword in ["player", "batter", "bowler", "batting", "bowling", "cricketer"]):
        player = _match_player(question, all_players)
        if player:
            return _player_profile(player, deliveries)

    team = _match_team(question, all_teams)
    if team:
        return _team_profile(team, matches, deliveries)

    player = _match_player(question, all_players)
    if player:
        return _player_profile(player, deliveries)

    venue = _match_venue(question, all_venues)
    if venue:
        return _venue_profile(venue, match_metrics)

    years = _question_years(question)
    if years:
        return _season_profile(years[-1], matches, deliveries)

    if any(keyword in normalized_question for keyword in ["record", "records", "highest", "most", "best", "top"]):
        batters = _summarize_batters(deliveries)
        bowlers = _summarize_bowlers(deliveries)
        top_batter = batters.iloc[0] if not batters.empty else None
        top_bowler = bowlers.iloc[0] if not bowlers.empty else None
        if top_batter is not None and top_bowler is not None:
            return (
                f"Top batting record: {top_batter['batter']} with {int(top_batter['runs'])} runs. "
                f"Top bowling record: {top_bowler['bowler']} with {int(top_bowler['wickets'])} wickets."
            )

    metrics = _dashboard_payload(matches, deliveries, match_metrics)["metrics"]
    return (
        f"This IPL dashboard currently covers {metrics['matches']} matches across {metrics['seasons']} seasons. "
        f"Ask me about a team, player, venue, season, champion, record, auction, powerplay, or any other IPL topic."
    )


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


@app.get("/plotly.min.js", include_in_schema=False)
def plotly_bundle() -> FileResponse:
    return FileResponse(PLOTLY_BUNDLE, media_type="application/javascript")


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
    teams = payload.get("teams") if isinstance(payload.get("teams"), list) else []
    venues = payload.get("venues") if isinstance(payload.get("venues"), list) else []
    matches, deliveries, match_metrics = _selected_frames([str(item) for item in teams], [str(item) for item in venues])

    question = str(payload.get("question", "")).strip().lower()
    if not question:
        return {"answer": "Ask me about teams, players, seasons, or records."}

    return {"answer": _answer_knowledge_question(question, matches, deliveries, match_metrics)}


@app.get("/{path:path}", include_in_schema=False)
def spa_fallback(path: str) -> FileResponse:
    candidate = STATIC_DIR / path
    if path and candidate.is_file():
        return FileResponse(candidate)
    return FileResponse(STATIC_DIR / "index.html")
