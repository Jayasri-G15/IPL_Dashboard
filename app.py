from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import FastAPI, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

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

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
DATASET_PATH = BASE_DIR / "ipl_json.zip"

app = FastAPI(
    title="IPL Analytics Dashboard",
    description="Interactive IPL analytics built on the full Cricsheet archive.",
    version="3.0.0",
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class ChatRequest(BaseModel):
    question: str
    seasons: list[str] = ["All"]
    teams: list[str] = []
    venues: list[str] = []


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _clean(v: Any) -> Any:
    if pd.isna(v):
        return None
    if isinstance(v, float):
        return round(v, 4)
    return v


def _records(df: pd.DataFrame, limit: int | None = None) -> list[dict[str, Any]]:
    if df.empty:
        return []
    rows = df.head(limit).copy() if limit else df.copy()
    return [{k: _clean(val) for k, val in row.items()} for row in rows.to_dict("records")]


def _split(values: list[str] | None) -> list[str]:
    if not values:
        return []
    out: list[str] = []
    for v in values:
        out.extend(p.strip() for p in v.split(",") if p.strip())
    return out


@lru_cache(maxsize=1)
def _load() -> PipelineResult:
    return load_cricsheet_archive(DATASET_PATH)


def _filter(result: PipelineResult, seasons: list[str], teams: list[str], venues: list[str]):
    m = result.matches.copy()
    d = result.deliveries.copy()
    if seasons and "All" not in seasons:
        m = m[m["season"].astype(str).isin(seasons)]
        d = d[d["season"].astype(str).isin(seasons)]
    if teams:
        m = m[m["team_1"].isin(teams) | m["team_2"].isin(teams)]
        d = d[d["batting_team"].isin(teams) | d["bowling_team"].isin(teams)]
    if venues:
        m = m[m["venue"].isin(venues)]
        d = d[d["venue"].isin(venues)]
    mids = set(m["match_id"].astype(str))
    d = d[d["match_id"].astype(str).isin(mids)]
    return m, d


def _ctx(seasons: list[str], teams: list[str], venues: list[str]) -> dict:
    result = _load()
    m, d = _filter(result, seasons, teams, venues)
    team_results = build_team_results(m)
    batting  = build_batting_summary(d)
    bowling  = build_bowling_summary(d)
    mm       = build_match_metrics(m, d)
    venues_s = build_venue_summary(mm)
    toss_s   = build_toss_summary(mm)
    return dict(matches=m, deliveries=d, issues=result.issues,
                team_results=team_results, batting=batting, bowling=bowling,
                match_metrics=mm, venues=venues_s, toss=toss_s)


# ─── Aggregation helpers ──────────────────────────────────────────────────────

def _teams_overall(tr: pd.DataFrame) -> pd.DataFrame:
    if tr.empty:
        return pd.DataFrame()
    g = (
        tr.groupby("team", as_index=False)
        .agg(matches=("matches","sum"), decisive_matches=("decisive_matches","sum"),
             wins=("wins","sum"), losses=("losses","sum"),
             tied_or_no_results=("tied_or_no_results","sum"))
    )
    g["win_rate"] = g["wins"] / g["decisive_matches"].replace(0, pd.NA)
    return g.sort_values(["win_rate","wins"], ascending=False)


def _batting_overall(bat: pd.DataFrame) -> pd.DataFrame:
    if bat.empty:
        return pd.DataFrame()
    g = (
        bat.groupby("batter", as_index=False)
        .agg(runs=("runs","sum"), balls=("balls","sum"), fours=("fours","sum"),
             sixes=("sixes","sum"), dismissals=("dismissals","sum"))
    )
    g["strike_rate"] = g["runs"] / g["balls"].replace(0, pd.NA) * 100
    g["average"]     = g["runs"] / g["dismissals"].replace(0, pd.NA)
    return g.sort_values(["runs","strike_rate"], ascending=[False,False])


def _bowling_overall(bowl: pd.DataFrame) -> pd.DataFrame:
    if bowl.empty:
        return pd.DataFrame()
    g = (
        bowl.groupby("bowler", as_index=False)
        .agg(balls=("balls","sum"), runs_conceded=("runs_conceded","sum"),
             wickets=("wickets","sum"))
    )
    g["economy"]     = g["runs_conceded"] / (g["balls"] / 6).replace(0, pd.NA)
    g["average"]     = g["runs_conceded"] / g["wickets"].replace(0, pd.NA)
    g["strike_rate"] = g["balls"] / g["wickets"].replace(0, pd.NA)
    return g.sort_values(["wickets","economy"], ascending=[False,True])


def _safe_pct(num: float, den: float) -> float:
    return round(float(num) / float(den), 4) if den else 0.0


# ─── Chatbot ──────────────────────────────────────────────────────────────────

def answer_question(question: str, ctx: dict) -> str:
    q = question.lower().strip()
    teams   = _teams_overall(ctx["team_results"])
    batting = _batting_overall(ctx["batting"])
    bowling = _bowling_overall(ctx["bowling"])
    venues  = ctx["venues"]
    mm      = ctx["match_metrics"]

    if not q:
        return "Ask me anything about IPL! Try: 'Who has the best win rate?' or 'Tell me about IPL history.'"

    # ── IPL history ──────────────────────────────────────────────────────────
    if any(w in q for w in ["history","what is ipl","ipl started","ipl founded","tell me about","explain ipl","origin","bcci","lalit"]):
        return (
            "🏏 The Indian Premier League (IPL) started in 2008!\n\n"
            "Think of it like this — just as cities in England have football clubs,\n"
            "Indian cities have their own cricket teams in the IPL! Mumbai, Chennai,\n"
            "Kolkata, Delhi, Bangalore... they all compete for the big trophy!\n\n"
            "📅 First ever match: April 18, 2008 — Bangalore vs Kolkata\n"
            "🏆 Most successful: Mumbai Indians & Chennai Super Kings (5 titles each!)\n"
            "💰 League value: Over $10 Billion — cricket's richest competition\n"
            "🌍 Fans worldwide: 750 million+ people watch IPL every year!\n"
            "⚡ Fun Fact: IPL was created by Lalit Modi of the BCCI. The first auction\n"
            "   sold Sachin Tendulkar for ₹6.9 crore — a cricket legend going on auction! 😮"
        )

    # ── T20 cricket basics ───────────────────────────────────────────────────
    if any(w in q for w in ["how to play","cricket rules","what is t20","twenty20","t20 format","basics of cricket","explain cricket","cricket for beginner"]):
        return (
            "🏏 T20 Cricket — Easy Explained!\n\n"
            "Think of it like the 'fast food' version of cricket (full cricket = 5 days! 😄)\n\n"
            "Step 1: Two teams — one BATS, one BOWLS (fields)\n"
            "Step 2: The batting team gets 20 OVERS (1 over = 6 balls = 120 balls total)\n"
            "Step 3: Batters try to score RUNS by hitting the ball\n"
            "         • Ball reaches the rope (boundary) = 4 runs 🎯\n"
            "         • Ball clears the rope (six) = 6 runs! 🎆\n"
            "Step 4: Bowling team tries to get batters OUT (= wicket)\n"
            "Step 5: Teams switch after 20 overs or 10 wickets\n"
            "Step 6: Second team needs to beat the first team's total to WIN! 🏆\n\n"
            "A T20 match lasts about 3 hours — perfect for an evening game! ⏰"
        )

    # ── IPL format ───────────────────────────────────────────────────────────
    if any(w in q for w in ["format","how does ipl work","how many team","playoff","qualifier","knockout","league stage","structure"]):
        return (
            "📋 How the IPL Tournament Works:\n\n"
            "🔵 PHASE 1 — League Stage (the main tournament):\n"
            "   • 10 teams each play 14 matches\n"
            "   • Like a school class tournament — everyone plays everyone!\n"
            "   • Top 4 teams advance to the Playoffs\n\n"
            "🔴 PHASE 2 — Playoffs (the exciting knockout stage):\n"
            "   • Qualifier 1: Team 1 vs Team 2 → Winner goes straight to Final! ✅\n"
            "   • Eliminator: Team 3 vs Team 4 → Loser goes home 😢\n"
            "   • Qualifier 2: Loser of Q1 vs Winner of Eliminator → Winner reaches Final\n"
            "   • 🏆 GRAND FINAL: Two remaining teams battle it out!\n\n"
            "Current 10 Teams: CSK, MI, RCB, KKR, RR, SRH, DC, PBKS, GT, LSG"
        )

    # ── IPL champions ────────────────────────────────────────────────────────
    if any(w in q for w in ["champion","winner","title","trophy","most title","won ipl","best team ever","who won"]):
        return (
            "🏆 IPL Champions — All-Time Winners List!\n\n"
            "👑 5 TITLES each:\n"
            "   • Mumbai Indians (2013, 2015, 2017, 2019, 2020)\n"
            "   • Chennai Super Kings (2010, 2011, 2018, 2021, 2023)\n\n"
            "🥈 3 TITLES:\n"
            "   • Kolkata Knight Riders (2012, 2014, 2024)\n\n"
            "🥉 2 TITLES:\n"
            "   • Rajasthan Royals (2008, 2022)\n"
            "   • Sunrisers Hyderabad (2016) + 1 more?\n\n"
            "1 TITLE each:\n"
            "   • Deccan Chargers (2009), Gujarat Titans (2022)\n\n"
            "💡 Fun Fact: Chennai Super Kings qualified for IPL Playoffs in\n"
            "   ALL their seasons except 2 — an almost perfect record! 😮"
        )

    # ── IPL auction ──────────────────────────────────────────────────────────
    if any(w in q for w in ["auction","salary","expensive","crore","money","bid","price","bought","cost"]):
        return (
            "💰 IPL Auction — Where Players Become Millionaires!\n\n"
            "Before each season, teams BID for players like an online auction!\n\n"
            "📏 Rules:\n"
            "   • Each team gets a budget (salary cap) of ₹120 crore (~$14M)\n"
            "   • Teams can RETAIN 3-4 star players without auction\n"
            "   • For the rest, teams bid — highest bid wins the player!\n\n"
            "💎 Biggest Auction Sales Ever:\n"
            "   🥇 Mitchell Starc (KKR, 2024): ₹24.75 crore — ALL-TIME RECORD!\n"
            "   🥈 Pat Cummins (SRH, 2024): ₹20.5 crore\n"
            "   🥉 Sam Curran (PBKS, 2023): ₹18.5 crore\n\n"
            "For reference: ₹24.75 crore = about $3 million just for ONE cricket season! 🤑"
        )

    # ── Records (data-driven) ────────────────────────────────────────────────
    if any(w in q for w in ["record","highest","most runs","most wicket","all time","milestone","best ever"]):
        parts = []
        if not batting.empty:
            r = batting.iloc[0]
            parts.append(f"🏏 Most Runs: {r['batter']} — {int(r['runs'])} runs (SR: {r['strike_rate']:.1f})")
        if not bowling.empty:
            r = bowling.iloc[0]
            parts.append(f"⚡ Most Wickets: {r['bowler']} — {int(r['wickets'])} wkts (ECO: {r['economy']:.2f})")
        data_line = "\n".join(parts)
        return (
            f"📈 Records in Current View:\n{data_line}\n\n"
            "🌟 Famous All-Time IPL Records:\n"
            "   • Most IPL runs ever: Virat Kohli — 9,000+ runs 👑\n"
            "   • Highest team score: RCB — 263/5 (vs Pune Warriors, 2013)\n"
            "   • Most wickets: Yuzvendra Chahal — 200+ wickets 🎯\n"
            "   • Fastest fifty: Chris Gayle — just 17 balls! ⚡\n"
            "   • Most sixes in IPL history: Chris Gayle — 350+ sixes 💥\n"
            "   • Highest individual T20 score: Chris Gayle — 175* (off 66 balls!)"
        )

    # ── Best team (data-driven) ──────────────────────────────────────────────
    if any(w in q for w in ["team","win rate","strongest team","best team","which team"]):
        if teams.empty:
            return "No team data available for the current filters."
        r = teams.iloc[0]
        return (
            f"🏆 Best team in current view: {r['team']}!\n\n"
            f"Win Rate: {r['win_rate']:.1%}\n"
            f"That means they win {r['win_rate']*100:.0f} out of every 100 matches they play!\n\n"
            f"📊 Their record:\n"
            f"   Wins: {int(r['wins'])} | Losses: {int(r['losses'])} | "
            f"Total decisive matches: {int(r['decisive_matches'])}\n\n"
            f"💡 Think of win rate like a grade in school:\n"
            f"   60%+ = Excellent ⭐ | 50-60% = Good 👍 | Below 50% = Struggling 😅"
        )

    # ── Top batter (data-driven) ─────────────────────────────────────────────
    if any(w in q for w in ["batter","batsman","top scorer","most run","run scorer","batting"]):
        if batting.empty:
            return "No batting data available for the current filters."
        r = batting.iloc[0]
        return (
            f"🏏 Top Batter: {r['batter']}!\n\n"
            f"Runs scored: {int(r['runs'])}\n"
            f"Balls faced: {int(r['balls'])}\n"
            f"Strike Rate: {r['strike_rate']:.1f} — this means for every 100 balls,\n"
            f"  they score {r['strike_rate']:.0f} runs. Above 140 = excellent! ⚡\n"
            f"Average: {r['average']:.1f if not pd.isna(r['average']) else 'N/A'} — runs per dismissal\n\n"
            f"💡 Strike Rate explained for beginners:\n"
            f"   If you score 6 runs off 4 balls → SR = 6/4 × 100 = 150! Really fast! 🚀"
        )

    # ── Top bowler (data-driven) ─────────────────────────────────────────────
    if any(w in q for w in ["bowler","wicket","most wicket","bowling","wicket taker"]):
        if bowling.empty:
            return "No bowling data available for the current filters."
        r = bowling.iloc[0]
        return (
            f"⚡ Top Bowler: {r['bowler']}!\n\n"
            f"Wickets taken: {int(r['wickets'])}\n"
            f"Economy Rate: {r['economy']:.2f} — they give away only {r['economy']:.2f} runs per over.\n"
            f"   Lower economy = better bowler! Under 7.5 is excellent in T20. 🎯\n\n"
            f"💡 Wicket explained for beginners:\n"
            f"   A 'wicket' means the batter is OUT! Getting wickets is how bowlers\n"
            f"   win matches for their team. 5 wickets in one innings = 'Five-For' (very rare!) 🏆"
        )

    # ── Toss (data-driven) ───────────────────────────────────────────────────
    if any(w in q for w in ["toss","coin","bat first","field first","chase","chasing"]):
        if mm.empty:
            return "No toss data available for the current filters."
        rate = _safe_pct(mm["toss_winner_won"].sum(), mm["decisive_match"].sum())
        verdict = ("YES! Winning the toss gives a real advantage here! 🪙"
                   if rate > 0.55 else
                   "Not really — the toss doesn't decide the winner much! 💪"
                   if rate < 0.48 else
                   "A slight edge, but skill matters more than the coin! ⚖️")
        return (
            f"🪙 Toss Impact Analysis:\n\n"
            f"Toss winners won: {rate:.1%} of matches\n"
            f"Verdict: {verdict}\n\n"
            f"🧠 How to interpret this:\n"
            f"   • If toss had ZERO effect → we'd expect exactly 50%\n"
            f"   • Above 55% → toss really helps!\n"
            f"   • Below 45% → toss actually HURTS? (rare but possible!)\n\n"
            f"📊 In modern IPL, most captains choose to FIELD first (bowl)\n"
            f"   because chasing is easier — you know the exact score to beat! 🎯"
        )

    # ── Venue (data-driven) ──────────────────────────────────────────────────
    if any(w in q for w in ["venue","ground","stadium","best venue","worst venue","wankhede","eden","chepauk","chinnaswamy"]):
        if venues.empty:
            return "No venue data available for the current filters."
        best_chase = venues.sort_values("chasing_win_rate", ascending=False).iloc[0]
        best_bat   = venues.sort_values("batting_first_win_rate", ascending=False).iloc[0]
        hi_score   = venues.sort_values("avg_first_innings_runs", ascending=False).iloc[0]
        return (
            f"🏟️ Venue Insights!\n\n"
            f"Best for CHASING (batting 2nd):\n"
            f"  → {best_chase['venue']} ({best_chase['chasing_win_rate']:.1%} chase win rate!)\n\n"
            f"Best for DEFENDING (batting 1st):\n"
            f"  → {best_bat['venue']} ({best_bat['batting_first_win_rate']:.1%} defend rate!)\n\n"
            f"Highest scoring ground:\n"
            f"  → {hi_score['venue']} (avg 1st innings: {hi_score['avg_first_innings_runs']:.0f} runs)\n\n"
            f"🌟 Famous IPL Venues to know:\n"
            f"  • Wankhede (Mumbai): Small boundaries → TONS of sixes! ⚡\n"
            f"  • Eden Gardens (Kolkata): 68,000 fans — the LOUDEST stadium! 📣\n"
            f"  • Chepauk (Chennai): Slow pitch → bowlers love it here! 🎯"
        )

    # ── Famous players ────────────────────────────────────────────────────────
    if any(w in q for w in ["dhoni","mahi","ms dhoni","csk captain","captain cool"]):
        return (
            "🦁 MS Dhoni — The Legend of IPL!\n\n"
            "Full name: Mahendra Singh Dhoni\n"
            "Team: Chennai Super Kings (CSK)\n"
            "IPL Titles as Captain: 5 (the most anyone has won!)\n"
            "Nickname: 'Captain Cool' — he NEVER panics under pressure!\n\n"
            "🚁 Famous for his 'Helicopter Shot' — he swings the bat in a full circle\n"
            "   like a helicopter rotor and sends the ball for a six!\n\n"
            "🏅 Why he is special:\n"
            "   • Won World Cup, Champions Trophy AND IPL — complete champion!\n"
            "   • Best finisher — can win matches in the very last ball 😮\n"
            "   • As a wicket-keeper, his LIGHTNING fast stumpings are legendary!\n\n"
            "Fun Fact: Before cricket stardom, Dhoni was a railway ticket collector\n"
            "at Kharagpur station! From TTE to Champion — what a journey! 🚂"
        )

    if any(w in q for w in ["kohli","virat","king kohli","rcb","royal challengers"]):
        return (
            "👑 Virat Kohli — The Run Machine!\n\n"
            "Team: Royal Challengers Bengaluru (RCB)\n"
            "IPL Runs: 9,000+ — the ALL-TIME record! (No one else is even close!)\n"
            "Nickname: 'King Kohli' or 'The Chase Master'\n\n"
            "📊 His Best IPL Season (2016):\n"
            "   973 runs in a single season — still the record!\n"
            "   4 consecutive Man of the Match awards — incredible consistency!\n\n"
            "💡 He scores runs like collecting coins in a video game — fast,\n"
            "   consistent, and he never stops! 🎮\n\n"
            "Fun Fact: RCB fans are the most passionate in IPL — they fill\n"
            "Chinnaswamy Stadium even when RCB struggles. Their loyalty = legendary! 😅"
        )

    if any(w in q for w in ["rohit","hitman","mumbai indians","mi captain","sharma"]):
        return (
            "💙 Rohit Sharma — The Hitman!\n\n"
            "Team: Mumbai Indians (MI)\n"
            "IPL Titles as Captain: 5 (equals Dhoni's record!)\n"
            "Nickname: 'Hitman' because he HITS the ball incredibly hard!\n\n"
            "🏆 Mumbai Indians under Rohit:\n"
            "   Won the title in alternating years: 2013, 2015, 2017, 2019, 2020!\n"
            "   They're like the New York Yankees of cricket — always competitive!\n\n"
            "Fun Fact: MI is supported by Reliance Industries (one of India's biggest\n"
            "companies), making them the richest franchise in IPL! 💰\n"
            "Their fans call themselves the 'MI Paltan' (MI Army)! 💙"
        )

    if any(w in q for w in ["gayle","universe boss","chris gayle","six"]):
        return (
            "💥 Chris Gayle — The Universe Boss!\n\n"
            "From: Jamaica, West Indies 🌴\n"
            "Teams: RCB, PBKS, and more\n"
            "IPL Sixes: 350+ — THE MOST EVER! 🚀\n\n"
            "🌟 His mind-blowing records:\n"
            "   • Fastest IPL century: 30 balls (THIRTY! Most players take 60+)\n"
            "   • Highest T20 score: 175* off 66 balls (2013, for RCB vs Pune)\n"
            "   • 17 sixes in ONE innings at one point!\n\n"
            "When Gayle hits a six, the ball often lands OUTSIDE the stadium! 😮\n"
            "He once said: 'I am the Universe Boss. The game belongs to me!' 😄\n\n"
            "Fun Fact: Gayle's famous 'gangnam style' celebrations after sixes\n"
            "made the whole stadium dance with him! 🕺"
        )

    # ── Chatbot help ─────────────────────────────────────────────────────────
    if any(w in q for w in ["help","suggest","what can you","question","ask"]):
        return (
            "💬 What I Can Help You With!\n\n"
            "🏆 Teams & Performance:\n"
            "   'Who has the best win rate?' | 'Tell me about IPL champions'\n\n"
            "🏏 Players:\n"
            "   'Which batter scored most runs?' | 'Top wicket taker?'\n"
            "   'Tell me about Dhoni/Kohli/Rohit'\n\n"
            "📊 Analysis:\n"
            "   'Does winning the toss help?' | 'Best venue for chasing?'\n\n"
            "📚 Cricket Education:\n"
            "   'What is T20 cricket?' | 'How does IPL work?'\n"
            "   'What is a wicket?' | 'Tell me about IPL history'\n\n"
            "🎊 Fun stuff:\n"
            "   'IPL fun facts' | 'Tell me about Chris Gayle'\n"
            "   'What is the IPL auction?'"
        )

    # ── Fun facts ────────────────────────────────────────────────────────────
    if any(w in q for w in ["fun fact","interesting fact","did you know","trivia","cool"]):
        return (
            "🎊 Amazing IPL Facts You Probably Didn't Know!\n\n"
            "1. 🎵 IPL has its own anthem: 'Ye Hai Nayi Duniya' ('This is a New World')\n"
            "2. 🌍 Players from 25+ different countries play in the IPL!\n"
            "3. 🏟️ Largest IPL crowd ever: 101,566 fans at Narendra Modi Stadium!\n"
            "4. 🎂 First IPL auction: Sachin Tendulkar sold for ₹6.9 crore (2008)\n"
            "5. 🌡️ Chennai matches are in 40°C heat — players sweat buckets!\n"
            "6. 💡 The IPL pink ball night matches started in 2013 (first ever in T20!)\n"
            "7. 📱 IPL is the most-followed sports league in South Asia on social media\n"
            "8. 🦁 CSK's mascot is a Super King lion. KKR's is a knight on horseback! 🐴"
        )

    # ── Fallback ─────────────────────────────────────────────────────────────
    return (
        "🤔 Hmm, I'm not sure about that specific question!\n\n"
        "But I know loads about IPL! Try:\n"
        "   • 'What is IPL?' — for history\n"
        "   • 'Best team?' — for win rate stats\n"
        "   • 'Top batter?' — for batting numbers\n"
        "   • 'Toss impact?' — for toss analysis\n"
        "   • 'Fun facts?' — for cool IPL trivia 🎊\n"
        "   • 'Help' — to see everything I can answer!\n\n"
        "Or just explore the dashboard — the charts tell the story! 📊"
    )


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/options")
def options() -> dict[str, Any]:
    result = _load()
    m = result.matches
    seasons = sorted(s for s in m["season"].dropna().astype(str).unique() if s)
    teams   = sorted(t for t in pd.unique(m[["team_1","team_2"]].values.ravel("K")) if t)
    venues  = sorted(m["venue"].dropna().astype(str).unique())
    return {
        "seasons": seasons,
        "teams":   teams,
        "venues":  venues,
        "dataset": {
            "matches":    len(result.matches),
            "deliveries": len(result.deliveries),
            "issues":     len(result.issues),
        },
    }


@app.get("/api/dashboard")
def dashboard(
    seasons: list[str] | None = Query(default=None),
    teams:   list[str] | None = Query(default=None),
    venues:  list[str] | None = Query(default=None),
) -> dict[str, Any]:
    s = _split(seasons) or ["All"]
    t = _split(teams)
    v = _split(venues)
    ctx = _ctx(s, t, v)
    m   = ctx["matches"]
    d   = ctx["deliveries"]
    mm  = ctx["match_metrics"]
    to  = _teams_overall(ctx["team_results"])
    bat = _batting_overall(ctx["batting"])
    bowl = _bowling_overall(ctx["bowling"])

    bat  = bat[bat["balls"] >= 30].sort_values(["runs","strike_rate"], ascending=[False,False])
    bowl = bowl[bowl["balls"] >= 30].sort_values(["wickets","economy"], ascending=[False,True])

    st = ctx["team_results"].copy()
    if not st.empty:
        st["win_rate"] = st["wins"] / st["matches"].replace(0, pd.NA)

    td = pd.DataFrame()
    if not mm.empty:
        td = (
            mm.groupby("toss_decision", dropna=False, as_index=False)
            .agg(matches=("match_id","count"), decisive_matches=("decisive_match","sum"),
                 toss_winner_wins=("toss_winner_won","sum"))
        )
        td["win_rate"] = td["toss_winner_wins"] / td["decisive_matches"].replace(0, pd.NA)

    players = 0
    if not d.empty:
        players = int(pd.unique(pd.concat([d["batter"],d["bowler"]], ignore_index=True)).size)

    return {
        "filters": {"seasons": s, "teams": t, "venues": v},
        "metrics": {
            "matches":     len(m),
            "seasons":     int(m["season"].nunique()) if not m.empty else 0,
            "teams":       int(pd.unique(m[["team_1","team_2"]].values.ravel("K")).size) if not m.empty else 0,
            "players":     players,
            "issues":      len(ctx["issues"]),
            "tossWinRate": _safe_pct(mm["toss_winner_won"].sum(), mm["decisive_match"].sum()) if not mm.empty else 0,
        },
        "teams":      _records(to, 20),
        "teamSeason": _records(st, 280),
        "batters":    _records(bat, 30),
        "bowlers":    _records(bowl, 30),
        "toss":       _records(td, 10),
        "tossSeason": _records(ctx["toss"], 120),
        "venues":     _records(ctx["venues"].sort_values(["matches","avg_first_innings_runs"], ascending=False), 35),
        "issues":     _records(ctx["issues"], 100),
    }


@app.get("/api/records")
def records_api() -> dict[str, Any]:
    result = _load()
    d = result.deliveries
    m = result.matches
    if d.empty or m.empty:
        return {"topInnings": [], "topTotals": [], "topBowling": []}

    # Top individual innings
    bi = (
        d.groupby(["match_id","batter"], as_index=False)
        .agg(runs=("runs_batter","sum"), balls=("legal_delivery","sum"),
             sixes=("runs_batter", lambda x: int((x == 6).sum())),
             fours=("runs_batter", lambda x: int((x == 4).sum())))
    )
    bi["strike_rate"] = bi["runs"] / bi["balls"].replace(0, pd.NA) * 100
    top_innings = (
        bi.nlargest(10, "runs")
        .merge(m[["match_id","date","venue","season","team_1","team_2"]], on="match_id", how="left")
    )

    # Highest team totals (1st innings)
    t1 = (
        d[d["innings"] == 1]
        .groupby(["match_id","batting_team"], as_index=False)
        .agg(total=("runs_total","sum"))
    )
    top_totals = (
        t1.nlargest(10, "total")
        .merge(m[["match_id","date","venue","season"]], on="match_id", how="left")
    )

    # Best bowling figures in a match
    bm = (
        d.groupby(["match_id","bowler"], as_index=False)
        .agg(wickets=("bowler_wickets","sum"), runs=("bowler_runs_conceded","sum"),
             balls=("legal_delivery","sum"))
    )
    bm["economy"] = bm["runs"] / (bm["balls"] / 6).replace(0, pd.NA)
    top_bowling = (
        bm.nlargest(10, "wickets")
        .merge(m[["match_id","date","venue","season"]], on="match_id", how="left")
    )

    return {
        "topInnings": _records(top_innings, 10),
        "topTotals":  _records(top_totals,  10),
        "topBowling": _records(top_bowling, 10),
    }


@app.get("/api/seasons")
def seasons_api() -> dict[str, Any]:
    result = _load()
    m = result.matches
    d = result.deliveries
    if m.empty:
        return {"seasons": []}

    sm = m.groupby("season", as_index=False).agg(matches=("match_id","count"))

    if not d.empty:
        sb = d.groupby(["season","batter"], as_index=False).agg(runs=("runs_batter","sum"))
        tb = (
            sb.loc[sb.groupby("season")["runs"].idxmax()]
            .rename(columns={"batter":"top_scorer","runs":"top_scorer_runs"})
        )
        sw = d.groupby(["season","bowler"], as_index=False).agg(wickets=("bowler_wickets","sum"))
        tw = (
            sw.loc[sw.groupby("season")["wickets"].idxmax()]
            .rename(columns={"bowler":"top_bowler","wickets":"top_bowler_wickets"})
        )
        sm = sm.merge(tb[["season","top_scorer","top_scorer_runs"]], on="season", how="left")
        sm = sm.merge(tw[["season","top_bowler","top_bowler_wickets"]], on="season", how="left")

    # Season avg first innings runs
    mi = (
        d[d["innings"] == 1]
        .groupby(["season","match_id"], as_index=False)
        .agg(inns_runs=("runs_total","sum"))
        .groupby("season", as_index=False)
        .agg(avg_runs=("inns_runs","mean"))
    )
    sm = sm.merge(mi, on="season", how="left")

    return {"seasons": _records(sm.sort_values("season"))}


@app.post("/api/chat")
def chat(payload: ChatRequest) -> dict[str, str]:
    ctx = _ctx(payload.seasons or ["All"], payload.teams, payload.venues)
    return {"answer": answer_question(payload.question, ctx)}
