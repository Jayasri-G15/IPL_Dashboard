from __future__ import annotations

import tempfile
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

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


st.set_page_config(page_title="IPL Analytics Dashboard", page_icon="🏏", layout="wide")

st.markdown(
    """
<style>
    .stApp {
        background:
            radial-gradient(circle at top right, rgba(255, 195, 113, 0.16), transparent 32%),
            radial-gradient(circle at top left, rgba(21, 128, 61, 0.14), transparent 28%),
            linear-gradient(180deg, #08111f 0%, #0f172a 46%, #111827 100%);
        color: #e5e7eb;
    }
    h1, h2, h3, h4, p, label, .stMarkdown, .stDataFrame {
        color: #e5e7eb !important;
    }
    .card {
        background: rgba(15, 23, 42, 0.85);
        border: 1px solid rgba(148, 163, 184, 0.18);
        border-radius: 16px;
        padding: 1rem 1.1rem;
        box-shadow: 0 12px 30px rgba(0, 0, 0, 0.24);
    }
    .metric-title {
        font-size: 0.78rem;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: #cbd5e1;
        margin-bottom: 0.35rem;
    }
    .metric-value {
        font-size: 1.9rem;
        font-weight: 700;
        color: #fff7ed;
    }
    .metric-subtitle {
        color: #94a3b8;
        font-size: 0.86rem;
    }
</style>
""",
    unsafe_allow_html=True,
)


def default_dataset_path() -> Path:
    candidate = Path(__file__).with_name("ipl_json.zip")
    if candidate.exists():
        return candidate
    return Path(r"C:\Users\jayas\Downloads\IPL_Dashboard\ipl_json.zip")


@st.cache_data(show_spinner=False)
def load_pipeline_from_path(path: str) -> PipelineResult:
    return load_cricsheet_archive(path)


def format_ratio(numerator: float, denominator: float) -> str:
    if not denominator:
        return "0.0%"
    return f"{(numerator / denominator) * 100:.1f}%"


def render_metric(title: str, value: str, subtitle: str) -> None:
    st.markdown(
        f"""
        <div class="card">
            <div class="metric-title">{title}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-subtitle">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    st.title("IPL Analytics Dashboard")
    st.caption("Interactive match, player, toss, and venue analysis built from Cricsheet IPL JSON data.")

    uploaded = st.sidebar.file_uploader("Upload Cricsheet IPL ZIP", type=["zip"])
    path_value = st.sidebar.text_input("Dataset path", value=str(default_dataset_path()))
    dataset_path = Path(path_value)

    if uploaded is not None:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as handle:
            handle.write(uploaded.getbuffer())
            dataset_path = Path(handle.name)

    if not dataset_path.exists():
        st.error(f"Dataset not found: {dataset_path}")
        st.stop()

    with st.spinner("Parsing Cricsheet archive..."):
        result = load_pipeline_from_path(str(dataset_path))

    matches_df = result.matches
    deliveries_df = result.deliveries
    issues_df = result.issues

    if matches_df.empty or deliveries_df.empty:
        st.error("No usable matches were parsed from the selected dataset.")
        st.dataframe(issues_df.head(20), use_container_width=True)
        st.stop()

    team_results = build_team_results(matches_df)
    batting_summary = build_batting_summary(deliveries_df)
    bowling_summary = build_bowling_summary(deliveries_df)
    match_metrics = build_match_metrics(matches_df, deliveries_df)
    venue_summary = build_venue_summary(match_metrics)
    toss_summary = build_toss_summary(match_metrics)

    seasons = sorted([season for season in matches_df["season"].dropna().astype(str).unique().tolist() if season])
    teams = sorted(pd.unique(matches_df[["team_1", "team_2"]].values.ravel("K")).tolist())
    venues = sorted(matches_df["venue"].dropna().astype(str).unique().tolist())

    selected_seasons = st.sidebar.multiselect("Seasons", options=["All"] + seasons, default=["All"])
    selected_teams = st.sidebar.multiselect("Teams", options=teams, default=teams[: min(6, len(teams))])
    selected_venues = st.sidebar.multiselect("Venues", options=venues, default=[])

    filtered_matches = matches_df.copy()
    filtered_deliveries = deliveries_df.copy()
    if "All" not in selected_seasons:
        filtered_matches = filtered_matches[filtered_matches["season"].isin(selected_seasons)]
        filtered_deliveries = filtered_deliveries[filtered_deliveries["season"].isin(selected_seasons)]
    if selected_teams:
        filtered_matches = filtered_matches[
            filtered_matches["team_1"].isin(selected_teams) | filtered_matches["team_2"].isin(selected_teams)
        ]
        filtered_deliveries = filtered_deliveries[
            filtered_deliveries["batting_team"].isin(selected_teams) | filtered_deliveries["bowling_team"].isin(selected_teams)
        ]
    if selected_venues:
        filtered_matches = filtered_matches[filtered_matches["venue"].isin(selected_venues)]
        filtered_deliveries = filtered_deliveries[filtered_deliveries["venue"].isin(selected_venues)]

    filtered_match_metrics = match_metrics[match_metrics["match_id"].isin(filtered_matches["match_id"])]
    filtered_team_results = team_results[team_results["team"].isin(selected_teams)] if selected_teams else team_results

    total_matches = len(filtered_matches)
    total_seasons = filtered_matches["season"].nunique()
    total_teams = pd.unique(filtered_matches[["team_1", "team_2"]].values.ravel("K")).size
    total_players = pd.unique(pd.concat([filtered_deliveries["batter"], filtered_deliveries["bowler"]], ignore_index=True)).size
    parse_warnings = 0 if issues_df.empty else len(issues_df)

    cols = st.columns(5)
    with cols[0]:
        render_metric("Matches", f"{total_matches:,}", f"Across {total_seasons} seasons")
    with cols[1]:
        render_metric("Teams", f"{total_teams:,}", "Distinct participating sides")
    with cols[2]:
        render_metric("Players", f"{total_players:,}", "Batters and bowlers seen in ball-by-ball data")
    with cols[3]:
        render_metric("Data issues", f"{parse_warnings:,}", "Skipped or flagged records")
    with cols[4]:
        toss_rate = format_ratio(filtered_match_metrics["toss_winner_won"].sum(), len(filtered_match_metrics)) if len(filtered_match_metrics) else "0.0%"
        render_metric("Toss winner win rate", toss_rate, "How often the toss winner also won the match")

    tab_team, tab_players, tab_toss, tab_venue, tab_quality = st.tabs([
        "Team Performance",
        "Players",
        "Toss Impact",
        "Venues",
        "Data Quality",
    ])

    with tab_team:
        st.subheader("Win rates by team")
        team_overall = (
            filtered_team_results.groupby("team", as_index=False)
            .agg(matches=("matches", "sum"), wins=("wins", "sum"))
        )
        team_overall["win_rate"] = team_overall["wins"] / team_overall["matches"]
        team_overall = team_overall[team_overall["matches"] >= 5].sort_values("win_rate", ascending=False)

        left, right = st.columns([1.2, 1])
        with left:
            top_overall = team_overall.head(12)
            fig = px.bar(
                top_overall,
                x="win_rate",
                y="team",
                orientation="h",
                text=top_overall["win_rate"].map(lambda v: f"{v:.1%}"),
                title="Overall win rate leaderboard",
                color="win_rate",
                color_continuous_scale="Viridis",
            )
            fig.update_layout(height=500, xaxis_tickformat=".0%", yaxis_title="")
            st.plotly_chart(fig, use_container_width=True)
        with right:
            season_team = filtered_team_results[filtered_team_results["team"].isin(selected_teams or teams)]
            if not season_team.empty:
                season_team = (
                    season_team.groupby(["season", "team"], as_index=False)
                    .agg(matches=("matches", "sum"), wins=("wins", "sum"))
                )
                season_team["win_rate"] = season_team["wins"] / season_team["matches"]
                fig = px.line(
                    season_team,
                    x="season",
                    y="win_rate",
                    color="team",
                    markers=True,
                    title="Season-by-season win rate",
                )
                fig.update_layout(height=500, yaxis_tickformat=".0%")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Select at least one team to view the season trend.")

        st.dataframe(team_overall.head(20), use_container_width=True)

    with tab_players:
        st.subheader("Best batsmen and bowlers")
        season_choice = st.selectbox("Season focus", options=["All"] + seasons, index=0)
        batting_focus = batting_summary if season_choice == "All" else batting_summary[batting_summary["season"] == season_choice]
        bowling_focus = bowling_summary if season_choice == "All" else bowling_summary[bowling_summary["season"] == season_choice]

        batting_focus = batting_focus[batting_focus["balls"] >= 30].sort_values(["runs", "strike_rate"], ascending=[False, False])
        bowling_focus = bowling_focus[bowling_focus["balls"] >= 30].sort_values(["wickets", "economy"], ascending=[False, True])

        b_left, b_right = st.columns(2)
        with b_left:
            st.markdown("**Top batters**")
            if not batting_focus.empty:
                batting_chart = batting_focus.head(10).copy()
                batting_chart["label"] = batting_chart["batter"]
                fig = px.bar(
                    batting_chart,
                    x="runs",
                    y="label",
                    orientation="h",
                    color="strike_rate",
                    color_continuous_scale="Plasma",
                    hover_data=["balls", "average", "fours", "sixes"],
                    title="Runs scored by batter",
                )
                fig.update_layout(height=520, yaxis_title="")
                st.plotly_chart(fig, use_container_width=True)
                st.dataframe(
                    batting_chart[["season", "batter", "runs", "balls", "strike_rate", "average", "fours", "sixes"]],
                    use_container_width=True,
                )
            else:
                st.info("Not enough batting data for the selected season filter.")
        with b_right:
            st.markdown("**Top bowlers**")
            if not bowling_focus.empty:
                bowling_chart = bowling_focus.head(10).copy()
                bowling_chart["label"] = bowling_chart["bowler"]
                fig = px.bar(
                    bowling_chart,
                    x="wickets",
                    y="label",
                    orientation="h",
                    color="economy",
                    color_continuous_scale="RdYlGn_r",
                    hover_data=["balls", "runs_conceded", "average", "strike_rate"],
                    title="Wickets taken by bowler",
                )
                fig.update_layout(height=520, yaxis_title="")
                st.plotly_chart(fig, use_container_width=True)
                st.dataframe(
                    bowling_chart[["season", "bowler", "wickets", "balls", "runs_conceded", "economy", "average", "strike_rate"]],
                    use_container_width=True,
                )
            else:
                st.info("Not enough bowling data for the selected season filter.")

    with tab_toss:
        st.subheader("Toss impact analysis")
        if not filtered_match_metrics.empty:
            decision_summary = (
                filtered_match_metrics.groupby("toss_decision", as_index=False)
                .agg(matches=("match_id", "count"), toss_winner_wins=("toss_winner_won", "sum"))
            )
            decision_summary["win_rate"] = decision_summary["toss_winner_wins"] / decision_summary["matches"]

            c1, c2 = st.columns(2)
            with c1:
                fig = px.bar(
                    decision_summary,
                    x="toss_decision",
                    y="win_rate",
                    color="win_rate",
                    color_continuous_scale="Blues",
                    text=decision_summary["win_rate"].map(lambda v: f"{v:.1%}"),
                    title="Toss winner match win rate by decision",
                )
                fig.update_layout(height=420, yaxis_tickformat=".0%", xaxis_title="Toss decision")
                st.plotly_chart(fig, use_container_width=True)
            with c2:
                toss_focus = toss_summary if season_choice == "All" else toss_summary[toss_summary["season"] == season_choice]
                fig = px.line(
                    toss_focus,
                    x="season",
                    y="toss_winner_win_rate",
                    color="toss_decision",
                    markers=True,
                    title="Toss winner win rate over seasons",
                )
                fig.update_layout(height=420, yaxis_tickformat=".0%")
                st.plotly_chart(fig, use_container_width=True)

            st.dataframe(decision_summary, use_container_width=True)
        else:
            st.info("No match data available for toss analysis after filtering.")

    with tab_venue:
        st.subheader("Venue-wise trends")
        venue_focus = venue_summary[venue_summary["matches"] >= 5].copy()
        if selected_venues:
            venue_focus = venue_focus[venue_focus["venue"].isin(selected_venues)]

        if not venue_focus.empty:
            venue_chart = venue_focus.sort_values("avg_first_innings_runs", ascending=False).head(15)
            fig = px.scatter(
                venue_chart,
                x="avg_first_innings_runs",
                y="batting_first_win_rate",
                size="matches",
                color="toss_winner_win_rate",
                hover_name="venue",
                title="Ground profile: first innings scoring vs batting-first success",
                color_continuous_scale="Turbo",
            )
            fig.update_layout(height=520, xaxis_title="Average first innings runs", yaxis_tickformat=".0%")
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(
                venue_chart[["venue", "matches", "avg_first_innings_runs", "batting_first_win_rate", "chasing_win_rate", "toss_winner_win_rate"]],
                use_container_width=True,
            )
        else:
            st.info("No venues meet the current filter threshold.")

    with tab_quality:
        st.subheader("Fault tolerance and data quality")
        st.write(
            "The parser skips broken files and partial records instead of corrupting the aggregates. "
            "Rows with missing critical fields, invalid JSON, or malformed innings/deliveries are recorded below."
        )
        st.dataframe(issues_df.head(100), use_container_width=True)

        st.markdown("### Analysis notes")
        st.markdown(
            "- Batsman strike rate, average, and boundary counts are derived from ball-by-ball delivery records because the raw Cricsheet JSON does not provide precomputed batting metrics.\n"
            "- Bowler economy and bowling average are derived from delivery-level runs and wickets; byes and leg-byes are excluded from bowler runs conceded when present.\n"
            "- Matches with no decisive winner are retained for participation counts but excluded from win-rate calculations."
        )


if __name__ == "__main__":
    main()