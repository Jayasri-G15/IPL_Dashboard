from __future__ import annotations

import base64
import tempfile
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
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

def _theme_tokens(theme: str) -> dict[str, str]:
    if theme == "Light":
        return {
            "bg_1": "#f8fafc",
            "bg_2": "#ecfeff",
            "bg_3": "#dbeafe",
            "text": "#0f172a",
            "subtext": "#334155",
            "panel": "rgba(255, 255, 255, 0.88)",
            "stroke": "rgba(15, 23, 42, 0.12)",
            "hero": "linear-gradient(120deg, rgba(14, 165, 233, 0.16), rgba(245, 158, 11, 0.14))",
            "sidebar": "linear-gradient(180deg, #f8fafc, #edf7ff)",
            "button": "linear-gradient(120deg, #0f766e, #0ea5e9)",
            "button_hover": "linear-gradient(120deg, #0e7490, #0284c7)",
            "accent": "#0f766e",
            "accent_2": "#f97316",
            "chart_bg": "rgba(255,255,255,0.92)",
            "chart_grid": "rgba(15, 23, 42, 0.1)",
        }
    return {
        "bg_1": "#071225",
        "bg_2": "#0f2944",
        "bg_3": "#071a31",
        "text": "#f8fafc",
        "subtext": "#dbeafe",
        "panel": "rgba(8, 21, 42, 0.78)",
        "stroke": "rgba(148, 163, 184, 0.2)",
        "hero": "linear-gradient(120deg, rgba(34, 197, 94, 0.22), rgba(249, 115, 22, 0.2))",
        "sidebar": "linear-gradient(180deg, rgba(8, 17, 32, 0.95), rgba(7, 30, 56, 0.92))",
        "button": "linear-gradient(120deg, #14532d, #166534)",
        "button_hover": "linear-gradient(120deg, #166534, #15803d)",
        "accent": "#22c55e",
        "accent_2": "#f97316",
        "chart_bg": "rgba(8, 21, 42, 0.42)",
        "chart_grid": "rgba(255,255,255,0.1)",
    }


def _make_cricket_hero_art(theme: str) -> str:
    tokens = _theme_tokens(theme)
    if theme == "Light":
        svg = f'''
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 420" role="img" aria-label="Cricket analytics illustration">
          <defs>
            <linearGradient id="g1" x1="0" x2="1" y1="0" y2="1">
              <stop offset="0%" stop-color="#e0f2fe"/>
              <stop offset="100%" stop-color="#fff7ed"/>
            </linearGradient>
            <linearGradient id="g2" x1="0" x2="1" y1="0" y2="1">
              <stop offset="0%" stop-color="#0f766e"/>
              <stop offset="100%" stop-color="#0ea5e9"/>
            </linearGradient>
          </defs>
          <rect width="900" height="420" rx="36" fill="url(#g1)"/>
          <circle cx="150" cy="110" r="60" fill="#fde68a" opacity="0.8"/>
          <path d="M80 320h740" stroke="#94a3b8" stroke-width="8" stroke-linecap="round" opacity="0.35"/>
          <rect x="350" y="120" width="170" height="200" rx="20" fill="#0f172a" opacity="0.08"/>
          <rect x="395" y="120" width="18" height="200" rx="8" fill="#f97316"/>
          <rect x="430" y="120" width="18" height="200" rx="8" fill="#f97316"/>
          <rect x="465" y="120" width="18" height="200" rx="8" fill="#f97316"/>
          <rect x="383" y="110" width="112" height="18" rx="9" fill="#f59e0b"/>
          <rect x="535" y="215" width="190" height="24" rx="12" transform="rotate(22 535 215)" fill="#8b5cf6" opacity="0.9"/>
          <circle cx="692" cy="158" r="28" fill="#ef4444"/>
          <path d="M690 145l14 8-10 4 14 9" stroke="#fff" stroke-width="3" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
          <path d="M210 280c40-90 140-130 250-120 82 7 156 46 210 108" stroke="url(#g2)" stroke-width="10" fill="none" stroke-linecap="round"/>
          <text x="66" y="54" fill="#0f172a" font-size="36" font-family="Arial, sans-serif" font-weight="700">Cricket insights</text>
          <text x="66" y="90" fill="#334155" font-size="22" font-family="Arial, sans-serif">Fast filters, clear charts, better decisions</text>
        </svg>
        '''
    else:
        svg = f'''
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 420" role="img" aria-label="Cricket analytics illustration">
          <defs>
            <linearGradient id="g1" x1="0" x2="1" y1="0" y2="1">
              <stop offset="0%" stop-color="#0f2944"/>
              <stop offset="100%" stop-color="#071225"/>
            </linearGradient>
            <linearGradient id="g2" x1="0" x2="1" y1="0" y2="1">
              <stop offset="0%" stop-color="#22c55e"/>
              <stop offset="100%" stop-color="#f97316"/>
            </linearGradient>
          </defs>
          <rect width="900" height="420" rx="36" fill="url(#g1)"/>
          <circle cx="140" cy="106" r="58" fill="#f59e0b" opacity="0.76"/>
          <path d="M80 320h740" stroke="#cbd5e1" stroke-width="8" stroke-linecap="round" opacity="0.18"/>
          <rect x="350" y="120" width="170" height="200" rx="20" fill="#e2e8f0" opacity="0.08"/>
          <rect x="395" y="120" width="18" height="200" rx="8" fill="#f59e0b"/>
          <rect x="430" y="120" width="18" height="200" rx="8" fill="#f59e0b"/>
          <rect x="465" y="120" width="18" height="200" rx="8" fill="#f59e0b"/>
          <rect x="383" y="110" width="112" height="18" rx="9" fill="#22c55e"/>
          <rect x="535" y="215" width="190" height="24" rx="12" transform="rotate(22 535 215)" fill="#60a5fa" opacity="0.9"/>
          <circle cx="692" cy="158" r="28" fill="#ef4444"/>
          <path d="M690 145l14 8-10 4 14 9" stroke="#fff" stroke-width="3" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
          <path d="M210 280c40-90 140-130 250-120 82 7 156 46 210 108" stroke="url(#g2)" stroke-width="10" fill="none" stroke-linecap="round"/>
          <text x="66" y="54" fill="#f8fafc" font-size="36" font-family="Arial, sans-serif" font-weight="700">Cricket insights</text>
          <text x="66" y="90" fill="#dbeafe" font-size="22" font-family="Arial, sans-serif">Fast filters, clear charts, better decisions</text>
        </svg>
        '''
    encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"


def render_theme_css(theme: str) -> None:
    tokens = _theme_tokens(theme)
    st.markdown(
        f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Manrope:wght@400;500;700;800&display=swap');

    .stApp {{
        background:
            radial-gradient(circle at 8% 14%, rgba(34, 197, 94, 0.16), transparent 32%),
            radial-gradient(circle at 88% 8%, rgba(249, 115, 22, 0.16), transparent 30%),
            linear-gradient(135deg, {tokens['bg_1']} 0%, {tokens['bg_2']} 50%, {tokens['bg_3']} 100%);
        color: {tokens['text']};
    }}
    .stApp, .stMarkdown, .stText, p, label, .stDataFrame, .stSelectbox, .stMultiSelect {{
        font-family: 'Manrope', sans-serif;
    }}
    .block-container {{
        padding-top: 1rem;
        padding-bottom: 1.8rem;
        max-width: 100%;
    }}
    h1, h2, h3, h4, h5, h6, .stMarkdown {{
        color: {tokens['text']} !important;
    }}
    .hero {{
        background: {tokens['hero']};
        border: 1px solid {tokens['stroke']};
        border-radius: 22px;
        padding: 1rem;
        box-shadow: 0 18px 40px rgba(2, 8, 23, 0.28);
        animation: fadeIn 0.6s ease;
    }}
    .hero-grid {{
        display: grid;
        grid-template-columns: 1.15fr 0.85fr;
        gap: 1rem;
        align-items: center;
    }}
    .hero-title {{
        font-family: 'Bebas Neue', cursive;
        font-size: clamp(2rem, 4vw, 3.2rem);
        letter-spacing: 0.06em;
        color: {tokens['text']};
        margin-bottom: 0.2rem;
    }}
    .hero-subtitle {{
        color: {tokens['subtext']};
        font-size: 0.98rem;
        line-height: 1.65;
        max-width: 62ch;
    }}
    .hero-badges {{
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
        margin-top: 0.8rem;
    }}
    .hero-badge {{
        border: 1px solid {tokens['stroke']};
        background: rgba(255,255,255,0.06);
        color: {tokens['text']};
        padding: 0.4rem 0.7rem;
        border-radius: 999px;
        font-size: 0.8rem;
    }}
    .hero-art {{
        width: 100%;
        border-radius: 18px;
        border: 1px solid {tokens['stroke']};
        box-shadow: 0 12px 28px rgba(0,0,0,0.18);
        display: block;
    }}
    .card {{
        background: {tokens['panel']};
        border: 1px solid {tokens['stroke']};
        border-radius: 18px;
        padding: 1rem 1.1rem;
        box-shadow: 0 10px 28px rgba(0, 0, 0, 0.18);
        animation: riseUp 0.5s ease;
    }}
    .metric-title {{
        font-size: 0.78rem;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: {tokens['subtext']};
        margin-bottom: 0.35rem;
    }}
    .metric-value {{
        font-size: 1.9rem;
        font-weight: 800;
        color: {tokens['text']};
    }}
    .metric-subtitle {{
        color: {tokens['subtext']};
        font-size: 0.86rem;
    }}
    .howto {{
        background: rgba(2, 132, 199, 0.12);
        border: 1px solid {tokens['stroke']};
        border-radius: 14px;
        padding: 0.9rem 1rem;
        color: {tokens['text']};
        line-height: 1.6;
    }}
    [data-testid="stSidebar"] {{
        background: {tokens['sidebar']};
    }}
    .stButton > button {{
        border-radius: 999px;
        border: 1px solid {tokens['stroke']};
        background: {tokens['button']};
        color: #f8fafc;
        font-weight: 700;
    }}
    .stButton > button:hover {{
        border-color: {tokens['accent']};
        background: {tokens['button_hover']};
    }}
    div[data-testid="stDataFrame"] table {{
        color: {tokens['text']} !important;
    }}
    div[data-testid="stDataFrame"] thead th {{
        color: {tokens['text']} !important;
        background: rgba(148, 163, 184, 0.08) !important;
    }}
    div[data-testid="stDataFrame"] tbody td {{
        color: {tokens['text']} !important;
    }}
    .stTabs [data-baseweb="tab"] {{
        color: {tokens['subtext']};
    }}
    .stTabs [aria-selected="true"] {{
        color: {tokens['accent_2']} !important;
    }}
    .stSelectbox div[data-baseweb="select"], .stMultiSelect div[data-baseweb="select"] {{
        background-color: rgba(255,255,255,0.96);
        color: #111827;
    }}
    .stExpander {{
        border-color: {tokens['stroke']};
    }}
    .chart-note {{
        color: {tokens['subtext']};
        font-size: 0.84rem;
    }}
    @keyframes fadeIn {{
        from {{ opacity: 0; transform: translateY(8px); }}
        to {{ opacity: 1; transform: translateY(0); }}
    }}
    @keyframes riseUp {{
        from {{ opacity: 0; transform: translateY(12px); }}
        to {{ opacity: 1; transform: translateY(0); }}
    }}
    @media (max-width: 900px) {{
        .hero-grid {{ grid-template-columns: 1fr; }}
        .hero-title {{ font-size: 2rem; }}
        .metric-value {{ font-size: 1.5rem; }}
        .stButton > button {{ width: 100%; }}
    }}
    @media (max-width: 640px) {{
        .block-container {{ padding-left: 0.65rem; padding-right: 0.65rem; }}
        .hero {{ padding: 0.85rem; }}
    }}
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


@st.cache_data(show_spinner=False)
def build_cached_summaries(matches_df: pd.DataFrame, deliveries_df: pd.DataFrame) -> tuple[pd.DataFrame, ...]:
    team_results = build_team_results(matches_df)
    batting_summary = build_batting_summary(deliveries_df)
    bowling_summary = build_bowling_summary(deliveries_df)
    match_metrics = build_match_metrics(matches_df, deliveries_df)
    venue_summary = build_venue_summary(match_metrics)
    toss_summary = build_toss_summary(match_metrics)
    return team_results, batting_summary, bowling_summary, match_metrics, venue_summary, toss_summary


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


def style_plot(fig: go.Figure, *, height: int = 500, theme: str = "Dark") -> go.Figure:
    tokens = _theme_tokens(theme)
    fig.update_layout(
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor=tokens["chart_bg"],
        font=dict(color=tokens["text"], family="Manrope"),
        legend_title_text="",
        margin=dict(t=70, l=40, r=30, b=40),
    )
    return fig


def _sanitize_selected(values: list[str], valid: list[str]) -> list[str]:
    valid_set = set(valid)
    return [item for item in values if item in valid_set]


def _ranked_table(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    if df.empty:
        return df
    ranked = df.loc[:, columns].copy().reset_index(drop=True)
    ranked.insert(0, "rank", range(1, len(ranked) + 1))
    return ranked


def main() -> None:
    if "theme_mode" not in st.session_state:
        st.session_state["theme_mode"] = "Dark"

    theme_mode = st.sidebar.radio("Theme", options=["Dark", "Light"], horizontal=True, key="theme_mode")
    render_theme_css(theme_mode)
    art_url = _make_cricket_hero_art(theme_mode)

    st.markdown(
        f"""
        <div class="hero">
            <div class="hero-grid">
                <div>
                    <div class="hero-title">IPL Match Intelligence Studio</div>
                    <div class="hero-subtitle">
                        Explore team form, player dominance, toss impact, and venue trends from ball-by-ball IPL data.
                        The dashboard is designed for fast decisions, simple reading, and smooth use on laptop, tablet,
                        and mobile.
                    </div>
                    <div class="hero-badges">
                        <span class="hero-badge">Fast-loading analytics</span>
                        <span class="hero-badge">Light and dark modes</span>
                        <span class="hero-badge">Responsive layout</span>
                        <span class="hero-badge">Clear beginner guidance</span>
                    </div>
                </div>
                <div>
                    <img class="hero-art" src="{art_url}" alt="Cricket analytics illustration">
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.write("")

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

    team_results, batting_summary, bowling_summary, match_metrics, venue_summary, toss_summary = build_cached_summaries(
        matches_df,
        deliveries_df,
    )

    seasons = sorted([season for season in matches_df["season"].dropna().astype(str).unique().tolist() if season])
    teams = sorted([team for team in pd.unique(matches_df[["team_1", "team_2"]].values.ravel("K")).tolist() if team])
    venues = sorted(matches_df["venue"].dropna().astype(str).unique().tolist())

    all_season_options = ["All"] + seasons
    if "seasons_filter" not in st.session_state:
        st.session_state["seasons_filter"] = ["All"]
    if "teams_filter" not in st.session_state:
        st.session_state["teams_filter"] = teams[: min(8, len(teams))]
    if "venues_filter" not in st.session_state:
        st.session_state["venues_filter"] = []

    st.session_state["seasons_filter"] = _sanitize_selected(st.session_state["seasons_filter"], all_season_options) or ["All"]
    st.session_state["teams_filter"] = _sanitize_selected(st.session_state["teams_filter"], teams)
    st.session_state["venues_filter"] = _sanitize_selected(st.session_state["venues_filter"], venues)

    st.sidebar.markdown("### Quick actions")
    c1, c2 = st.sidebar.columns(2)
    if c1.button("Reset all"):
        st.session_state["seasons_filter"] = ["All"]
        st.session_state["teams_filter"] = teams[: min(8, len(teams))]
        st.session_state["venues_filter"] = []
        st.rerun()
    if c2.button("All teams"):
        st.session_state["teams_filter"] = teams
        st.rerun()
    c3, c4 = st.sidebar.columns(2)
    if c3.button("Only latest season") and seasons:
        st.session_state["seasons_filter"] = [seasons[-1]]
        st.rerun()
    if c4.button("Clear venues"):
        st.session_state["venues_filter"] = []
        st.rerun()

    selected_seasons = st.sidebar.multiselect("Seasons", options=all_season_options, key="seasons_filter")
    selected_teams = st.sidebar.multiselect("Teams", options=teams, key="teams_filter")
    selected_venues = st.sidebar.multiselect("Venues", options=venues, key="venues_filter")

    st.sidebar.markdown(
        """
        <div class="howto">
            <b>How filters work</b><br>
            1) Pick a season or keep <i>All</i>.<br>
            2) Choose one or many teams.<br>
            3) Add venues for ground-specific insights.<br>
            All charts and tables update instantly.
        </div>
        """,
        unsafe_allow_html=True,
    )

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
    total_players = len(pd.unique(pd.concat([filtered_deliveries["batter"], filtered_deliveries["bowler"]], ignore_index=True)))
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

    with st.expander("Step-by-step guide for first-time users", expanded=False):
        st.markdown(
            """
            1. Start with sidebar filters and keep only the teams or seasons you want to compare.
            2. Open Team Performance to understand consistency and year-wise trends.
            3. Open Players to identify top batters and bowlers for your selected context.
            4. Open Toss Impact to check whether toss decisions influenced outcomes.
            5. Open Venues to find batting-friendly grounds and chasing/batting-first patterns.
            6. Check Data Quality to see skipped or malformed source records.
            """
        )

    with tab_team:
        st.subheader("Win rates by team")
        team_overall = (
            filtered_team_results.groupby("team", as_index=False)
            .agg(matches=("matches", "sum"), wins=("wins", "sum"))
        )
        team_overall["win_rate"] = team_overall["wins"] / team_overall["matches"]
        team_overall = team_overall[team_overall["matches"] >= 5].sort_values("win_rate", ascending=False)
        team_overall["losses"] = team_overall["matches"] - team_overall["wins"]

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
            style_plot(fig, height=500, theme=theme_mode)
            fig.update_layout(xaxis_tickformat=".0%", yaxis_title="")
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
                style_plot(fig, height=500, theme=theme_mode)
                fig.update_layout(yaxis_tickformat=".0%")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Select at least one team to view the season trend.")

        c1, c2 = st.columns([0.9, 1.1])
        with c1:
            if not team_overall.empty:
                team_results_chart = team_overall.head(8).copy()
                donut = px.pie(
                    team_results_chart,
                    names="team",
                    values="matches",
                    hole=0.52,
                    title="Share of matches among top teams",
                )
                style_plot(donut, height=420, theme=theme_mode)
                donut.update_traces(textposition="inside", textinfo="percent+label")
                st.plotly_chart(donut, use_container_width=True)
        with c2:
            if not team_overall.empty:
                seasons_for_heatmap = (
                    filtered_team_results.groupby(["season", "team"], as_index=False)
                    .agg(matches=("matches", "sum"), wins=("wins", "sum"))
                )
                seasons_for_heatmap["win_rate"] = seasons_for_heatmap["wins"] / seasons_for_heatmap["matches"]
                heat = seasons_for_heatmap.pivot(index="team", columns="season", values="win_rate").fillna(0)
                heat = heat.loc[team_overall.head(10)["team"].tolist(), :]
                heat_fig = px.imshow(
                    heat,
                    aspect="auto",
                    color_continuous_scale="Viridis",
                    title="Team win-rate heatmap by season",
                )
                style_plot(heat_fig, height=420, theme=theme_mode)
                heat_fig.update_layout(xaxis_title="Season", yaxis_title="Team")
                st.plotly_chart(heat_fig, use_container_width=True)

        display_team_table = _ranked_table(
            team_overall.head(20),
            ["team", "matches", "wins", "losses", "win_rate"],
        )
        st.dataframe(display_team_table, use_container_width=True, hide_index=True)

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
                style_plot(fig, height=520, theme=theme_mode)
                fig.update_layout(yaxis_title="")
                st.plotly_chart(fig, use_container_width=True)
                dist_fig = px.box(
                    batting_focus.head(60),
                    x="season",
                    y="strike_rate",
                    points="all",
                    title="Batting strike-rate spread",
                )
                style_plot(dist_fig, height=320, theme=theme_mode)
                dist_fig.update_layout(xaxis_title="Season", yaxis_tickformat=".0f")
                st.plotly_chart(dist_fig, use_container_width=True)
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
                style_plot(fig, height=520, theme=theme_mode)
                fig.update_layout(yaxis_title="")
                st.plotly_chart(fig, use_container_width=True)
                wicket_mix = bowling_focus.head(20).copy()
                wicket_mix["wicket_band"] = pd.cut(
                    wicket_mix["wickets"],
                    bins=[0, 5, 10, 15, 25, 100],
                    labels=["1-5", "6-10", "11-15", "16-25", "25+"] ,
                    include_lowest=True,
                )
                wickets_pie = wicket_mix.groupby("wicket_band", as_index=False).agg(players=("bowler", "count"))
                fig2 = px.bar(
                    wickets_pie,
                    x="wicket_band",
                    y="players",
                    title="Bowler wicket distribution",
                    color="players",
                    color_continuous_scale="Tealgrn",
                )
                style_plot(fig2, height=320, theme=theme_mode)
                fig2.update_layout(xaxis_title="Wicket band", yaxis_title="Players")
                st.plotly_chart(fig2, use_container_width=True)
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
                style_plot(fig, height=420, theme=theme_mode)
                fig.update_layout(yaxis_tickformat=".0%", xaxis_title="Toss decision")
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
                style_plot(fig, height=420, theme=theme_mode)
                fig.update_layout(yaxis_tickformat=".0%")
                st.plotly_chart(fig, use_container_width=True)

            decision_summary = decision_summary.sort_values(["win_rate", "matches"], ascending=[False, False]).reset_index(drop=True)
            decision_summary.insert(0, "rank", range(1, len(decision_summary) + 1))
            st.dataframe(decision_summary, use_container_width=True, hide_index=True)
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
            style_plot(fig, height=520, theme=theme_mode)
            fig.update_layout(xaxis_title="Average first innings runs", yaxis_tickformat=".0%")
            st.plotly_chart(fig, use_container_width=True)
            line_fig = px.line(
                venue_chart.sort_values("avg_first_innings_runs").head(12),
                x="venue",
                y="avg_first_innings_runs",
                markers=True,
                title="Average first innings runs by venue",
            )
            style_plot(line_fig, height=320, theme=theme_mode)
            line_fig.update_layout(xaxis_title="Venue", yaxis_title="Avg runs")
            st.plotly_chart(line_fig, use_container_width=True)
            venue_table = venue_chart[["venue", "matches", "avg_first_innings_runs", "batting_first_win_rate", "chasing_win_rate", "toss_winner_win_rate"]].copy().reset_index(drop=True)
            venue_table.insert(0, "rank", range(1, len(venue_table) + 1))
            st.dataframe(
                venue_table,
                use_container_width=True,
                hide_index=True,
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