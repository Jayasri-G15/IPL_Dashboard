from __future__ import annotations

import math

from app import dashboard
from pipeline import load_cricsheet_archive


def assert_close(actual: float, expected: float, label: str, tolerance: float = 0.0001) -> None:
    if actual is None and expected is None:
        return
    if actual is None or not math.isclose(float(actual), float(expected), abs_tol=tolerance):
        raise AssertionError(f"{label}: expected {expected}, got {actual}")


def main() -> None:
    result = load_cricsheet_archive("ipl_json.zip")
    data = dashboard(seasons=["All"], teams=None, venues=None)

    assert data["metrics"]["matches"] == len(result.matches)
    assert data["metrics"]["issues"] == len(result.issues)

    top_team = data["teams"][0]
    team = top_team["team"]
    team_matches = result.matches[(result.matches["team_1"].eq(team)) | (result.matches["team_2"].eq(team))]
    decisive = team_matches[team_matches["winner"].astype(str).str.len() > 0]
    wins = decisive[decisive["winner"].eq(team)]
    assert top_team["matches"] == len(team_matches)
    assert top_team["decisive_matches"] == len(decisive)
    assert top_team["wins"] == len(wins)
    assert_close(top_team["win_rate"], len(wins) / len(decisive), "top team win_rate")

    deliveries = result.deliveries
    top_batter = data["batters"][0]
    batter_rows = deliveries[deliveries["batter"].eq(top_batter["batter"])]
    assert_close(top_batter["runs"], batter_rows["runs_batter"].sum(), "top batter runs")
    assert_close(top_batter["balls"], batter_rows["legal_delivery"].sum(), "top batter balls")

    top_bowler = data["bowlers"][0]
    bowler_rows = deliveries[deliveries["bowler"].eq(top_bowler["bowler"])]
    assert_close(top_bowler["wickets"], bowler_rows["bowler_wickets"].sum(), "top bowler wickets")
    assert_close(top_bowler["runs_conceded"], bowler_rows["bowler_runs_conceded"].sum(), "top bowler runs conceded")

    decisive_matches = result.matches[result.matches["winner"].astype(str).str.len() > 0]
    toss_winner_wins = decisive_matches["winner"].eq(decisive_matches["toss_winner"]).sum()
    assert_close(data["metrics"]["tossWinRate"], toss_winner_wins / len(decisive_matches), "overall toss win rate")

    print("Dashboard audit passed.")
    print(f"Matches: {len(result.matches)}")
    print(f"Deliveries: {len(result.deliveries)}")
    print(f"Top team: {top_team['team']} ({top_team['win_rate']:.2%})")
    print(f"Top batter: {top_batter['batter']} ({top_batter['runs']:.0f} runs)")
    print(f"Top bowler: {top_bowler['bowler']} ({top_bowler['wickets']:.0f} wickets)")


if __name__ == "__main__":
    main()
