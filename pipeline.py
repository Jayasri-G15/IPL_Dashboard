from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
from zipfile import BadZipFile, ZipFile

import pandas as pd

CRICHEET_BOWLER_CREDIT_WICKETS = {
    "bowled",
    "caught",
    "caught and bowled",
    "lbw",
    "stumped",
    "hit wicket",
}


@dataclass
class ParseIssue:
    source: str
    level: str
    message: str


@dataclass
class PipelineResult:
    matches: pd.DataFrame
    deliveries: pd.DataFrame
    issues: pd.DataFrame


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return ", ".join(_as_text(item) for item in value if item is not None)
    return str(value)


def _first_value(value: Any) -> Any:
    if isinstance(value, list):
        return value[0] if value else None
    return value


def _safe_json_load(raw: str, source: str, issues: list[ParseIssue]) -> dict[str, Any] | None:
    try:
        loaded = json.loads(raw)
    except json.JSONDecodeError as exc:
        issues.append(ParseIssue(source, "error", f"Invalid JSON: {exc.msg}"))
        return None
    if not isinstance(loaded, dict):
        issues.append(ParseIssue(source, "error", "Top-level record is not a JSON object."))
        return None
    return loaded


def _iter_sources(source_path: str | Path) -> Iterable[tuple[str, str]]:
    path = Path(source_path)
    if path.is_dir():
        for item in sorted(path.glob("**/*.json")):
            yield item.name, item.read_text(encoding="utf-8")
        return

    if path.suffix.lower() == ".zip":
        try:
            with ZipFile(path) as archive:
                for entry in archive.infolist():
                    if entry.is_dir() or not entry.filename.lower().endswith(".json"):
                        continue
                    with archive.open(entry) as handle:
                        yield Path(entry.filename).name, handle.read().decode("utf-8", errors="replace")
            return
        except BadZipFile as exc:
            raise ValueError(f"Unable to open ZIP archive: {path}") from exc

    if path.is_file() and path.suffix.lower() == ".json":
        yield path.name, path.read_text(encoding="utf-8")
        return

    raise FileNotFoundError(f"Unsupported source path: {path}")


def _is_legal_delivery(delivery: dict[str, Any]) -> bool:
    extras = delivery.get("extras") or {}
    if not isinstance(extras, dict):
        return True
    return not extras.get("wides") and not extras.get("noballs")


def _bowler_runs_conceded(delivery: dict[str, Any]) -> float:
    runs = delivery.get("runs") or {}
    extras = delivery.get("extras") or {}
    if not isinstance(runs, dict):
        return 0.0
    if not isinstance(extras, dict):
        extras = {}
    return float(runs.get("total", 0)) - float(extras.get("byes", 0)) - float(extras.get("legbyes", 0))


def load_cricsheet_archive(source_path: str | Path) -> PipelineResult:
    issues: list[ParseIssue] = []
    match_rows: list[dict[str, Any]] = []
    delivery_rows: list[dict[str, Any]] = []

    for source_name, raw_json in _iter_sources(source_path):
        record = _safe_json_load(raw_json, source_name, issues)
        if record is None:
            continue

        info = record.get("info")
        innings = record.get("innings")
        if not isinstance(info, dict):
            issues.append(ParseIssue(source_name, "warning", "Missing or invalid info section."))
            continue
        if not isinstance(innings, list) or not innings:
            issues.append(ParseIssue(source_name, "warning", "Missing innings data."))
            continue

        teams = info.get("teams") or []
        if not isinstance(teams, list) or len(teams) < 2:
            issues.append(ParseIssue(source_name, "warning", "Skipping match with fewer than two teams."))
            continue

        outcome = info.get("outcome") or {}
        toss = info.get("toss") or {}
        season = _as_text(_first_value(info.get("season")))
        venue = _as_text(info.get("venue"))
        city = _as_text(info.get("city"))
        match_date = _as_text(_first_value(info.get("dates")))
        winner = _as_text(outcome.get("winner"))
        result = _as_text(outcome.get("result"))
        match_id = Path(source_name).stem

        match_rows.append(
            {
                "match_id": match_id,
                "source_file": source_name,
                "season": season,
                "date": match_date,
                "venue": venue,
                "city": city,
                "team_1": _as_text(teams[0]),
                "team_2": _as_text(teams[1]),
                "toss_winner": _as_text(toss.get("winner")),
                "toss_decision": _as_text(toss.get("decision")),
                "winner": winner,
                "result": result,
                "match_type": _as_text(info.get("match_type")),
            }
        )

        for innings_index, innings_entry in enumerate(innings, start=1):
            if not isinstance(innings_entry, dict):
                issues.append(ParseIssue(source_name, "warning", f"Invalid innings at index {innings_index}."))
                continue
            batting_team = _as_text(innings_entry.get("team"))
            overs = innings_entry.get("overs")
            if not isinstance(overs, list):
                issues.append(ParseIssue(source_name, "warning", f"Missing overs for innings {innings_index}."))
                continue

            for over_index, over_entry in enumerate(overs):
                if not isinstance(over_entry, dict):
                    issues.append(ParseIssue(source_name, "warning", f"Invalid over at innings {innings_index}, over {over_index}."))
                    continue
                over_number = over_entry.get("over", over_index)
                deliveries = over_entry.get("deliveries")
                if not isinstance(deliveries, list):
                    issues.append(ParseIssue(source_name, "warning", f"Missing deliveries at innings {innings_index}, over {over_number}."))
                    continue

                for ball_index, delivery in enumerate(deliveries, start=1):
                    if not isinstance(delivery, dict):
                        issues.append(ParseIssue(source_name, "warning", f"Invalid delivery at innings {innings_index}, over {over_number}, ball {ball_index}."))
                        continue
                    runs = delivery.get("runs") or {}
                    if not isinstance(runs, dict):
                        issues.append(ParseIssue(source_name, "warning", f"Missing runs object at innings {innings_index}, over {over_number}, ball {ball_index}."))
                        continue

                    batter = _as_text(delivery.get("batter"))
                    bowler = _as_text(delivery.get("bowler"))
                    non_striker = _as_text(delivery.get("non_striker"))
                    legal_delivery = _is_legal_delivery(delivery)
                    delivery_wickets = delivery.get("wickets") or []
                    wicket_count = len(delivery_wickets) if isinstance(delivery_wickets, list) else 0
                    dismissal_kinds = []
                    dismissed_players = []
                    bowler_wickets = 0

                    if isinstance(delivery_wickets, list):
                        for wicket in delivery_wickets:
                            if not isinstance(wicket, dict):
                                continue
                            kind = _as_text(wicket.get("kind"))
                            dismissed = _as_text(wicket.get("player_out"))
                            dismissal_kinds.append(kind)
                            dismissed_players.append(dismissed)
                            if kind in CRICHEET_BOWLER_CREDIT_WICKETS:
                                bowler_wickets += 1

                    bowling_team = next((team for team in teams if _as_text(team) != batting_team), "")
                    delivery_rows.append(
                        {
                            "match_id": match_id,
                            "source_file": source_name,
                            "season": season,
                            "date": match_date,
                            "venue": venue,
                            "innings": innings_index,
                            "over": int(over_number) if str(over_number).isdigit() else over_number,
                            "ball_in_over": ball_index,
                            "batting_team": batting_team,
                            "bowling_team": _as_text(bowling_team),
                            "batter": batter,
                            "bowler": bowler,
                            "non_striker": non_striker,
                            "runs_batter": float(runs.get("batter", 0)),
                            "runs_extras": float(runs.get("extras", 0)),
                            "runs_total": float(runs.get("total", 0)),
                            "legal_delivery": legal_delivery,
                            "wicket_count": wicket_count,
                            "dismissal_kinds": "; ".join(kind for kind in dismissal_kinds if kind),
                            "dismissed_players": "; ".join(player for player in dismissed_players if player),
                            "bowler_wickets": bowler_wickets,
                            "bowler_runs_conceded": _bowler_runs_conceded(delivery),
                        }
                    )

    matches_df = pd.DataFrame(match_rows)
    deliveries_df = pd.DataFrame(delivery_rows)
    issues_df = pd.DataFrame([issue.__dict__ for issue in issues])

    if not matches_df.empty:
        matches_df["season"] = matches_df["season"].replace("", pd.NA)
        matches_df["season"] = matches_df["season"].astype("string")
    if not deliveries_df.empty:
        deliveries_df["season"] = deliveries_df["season"].replace("", pd.NA)
        deliveries_df["season"] = deliveries_df["season"].astype("string")

    return PipelineResult(matches=matches_df, deliveries=deliveries_df, issues=issues_df)


def build_team_results(matches_df: pd.DataFrame) -> pd.DataFrame:
    if matches_df.empty:
        return pd.DataFrame()

    rows: list[dict[str, Any]] = []
    for _, match in matches_df.iterrows():
        for team in (match["team_1"], match["team_2"]):
            rows.append(
                {
                    "season": match["season"],
                    "team": team,
                    "match_id": match["match_id"],
                    "won": bool(match["winner"] and team == match["winner"]),
                    "lost": bool(match["winner"] and team != match["winner"]),
                    "tied_or_no_result": not bool(match["winner"]),
                }
            )
    team_matches = pd.DataFrame(rows)
    summary = (
        team_matches.groupby(["season", "team"], dropna=False)
        .agg(matches=("match_id", "count"), wins=("won", "sum"))
        .reset_index()
    )
    summary["win_rate"] = summary["wins"] / summary["matches"]
    return summary


def build_batting_summary(deliveries_df: pd.DataFrame) -> pd.DataFrame:
    if deliveries_df.empty:
        return pd.DataFrame()

    batting = deliveries_df.copy()
    batting["is_boundary_four"] = batting["runs_batter"] == 4
    batting["is_boundary_six"] = batting["runs_batter"] == 6
    batting["dismissed_batter"] = batting.apply(
        lambda row: row["batter"] in {player.strip() for player in str(row["dismissed_players"]).split(";") if player.strip()},
        axis=1,
    )

    summary = (
        batting.groupby(["season", "batter"], dropna=False)
        .agg(
            runs=("runs_batter", "sum"),
            balls=("legal_delivery", "sum"),
            fours=("is_boundary_four", "sum"),
            sixes=("is_boundary_six", "sum"),
            dismissals=("dismissed_batter", "sum"),
        )
        .reset_index()
    )
    summary["strike_rate"] = summary["runs"] / summary["balls"].replace(0, pd.NA) * 100
    summary["average"] = summary["runs"] / summary["dismissals"].replace(0, pd.NA)
    summary["boundary_runs"] = summary["fours"] * 4 + summary["sixes"] * 6
    return summary.sort_values(["season", "runs"], ascending=[True, False])


def build_bowling_summary(deliveries_df: pd.DataFrame) -> pd.DataFrame:
    if deliveries_df.empty:
        return pd.DataFrame()

    bowling = deliveries_df.copy()
    summary = (
        bowling.groupby(["season", "bowler"], dropna=False)
        .agg(
            balls=("legal_delivery", "sum"),
            runs_conceded=("bowler_runs_conceded", "sum"),
            wickets=("bowler_wickets", "sum"),
        )
        .reset_index()
    )
    summary["economy"] = summary["runs_conceded"] / (summary["balls"] / 6).replace(0, pd.NA)
    summary["average"] = summary["runs_conceded"] / summary["wickets"].replace(0, pd.NA)
    summary["strike_rate"] = summary["balls"] / summary["wickets"].replace(0, pd.NA)
    return summary.sort_values(["season", "wickets", "economy"], ascending=[True, False, True])


def build_match_metrics(matches_df: pd.DataFrame, deliveries_df: pd.DataFrame) -> pd.DataFrame:
    if matches_df.empty or deliveries_df.empty:
        return pd.DataFrame()

    first_innings = deliveries_df[deliveries_df["innings"] == 1].groupby("match_id", as_index=False).agg(
        first_innings_runs=("runs_total", "sum"),
        first_innings_balls=("legal_delivery", "sum"),
        first_innings_batting_team=("batting_team", "first"),
    )
    merged = matches_df.merge(first_innings, on="match_id", how="left")
    merged["toss_winner_won"] = merged["winner"].eq(merged["toss_winner"])
    merged["batting_first_won"] = merged["winner"].eq(merged["first_innings_batting_team"])
    merged["chasing_won"] = merged["winner"].ne(merged["first_innings_batting_team"])
    merged["result_label"] = merged["winner"].where(merged["winner"].astype(bool), merged["result"])
    return merged


def build_venue_summary(match_metrics_df: pd.DataFrame) -> pd.DataFrame:
    if match_metrics_df.empty:
        return pd.DataFrame()

    summary = (
        match_metrics_df.groupby("venue", dropna=False)
        .agg(
            matches=("match_id", "count"),
            avg_first_innings_runs=("first_innings_runs", "mean"),
            batting_first_wins=("batting_first_won", "sum"),
            chasing_wins=("chasing_won", "sum"),
            toss_winner_wins=("toss_winner_won", "sum"),
        )
        .reset_index()
    )
    summary["batting_first_win_rate"] = summary["batting_first_wins"] / summary["matches"]
    summary["chasing_win_rate"] = summary["chasing_wins"] / summary["matches"]
    summary["toss_winner_win_rate"] = summary["toss_winner_wins"] / summary["matches"]
    return summary.sort_values(["matches", "avg_first_innings_runs"], ascending=[False, False])


def build_toss_summary(match_metrics_df: pd.DataFrame) -> pd.DataFrame:
    if match_metrics_df.empty:
        return pd.DataFrame()

    summary = (
        match_metrics_df.groupby(["season", "toss_decision"], dropna=False)
        .agg(matches=("match_id", "count"), toss_winner_wins=("toss_winner_won", "sum"))
        .reset_index()
    )
    summary["toss_winner_win_rate"] = summary["toss_winner_wins"] / summary["matches"]
    return summary