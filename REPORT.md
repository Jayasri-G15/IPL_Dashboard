# REPORT

## Project Goal

End-to-end IPL Analytics Dashboard built on the full Cricsheet JSON archive (1,233 matches, 293,308 deliveries, 19 seasons). The interface is beginner-friendly — large team cards, ranked tables, color-coded charts, plain-language explanations, and a chatbot make the IPL story readable by anyone.

## Technology Stack

- **Backend:** FastAPI — serves the static frontend and exposes JSON APIs for all analytics.
- **Frontend:** Vanilla HTML / CSS / JavaScript — no build step, works offline-first.
- **Charts:** Plotly.js (CDN) for fully interactive bar, scatter, and line charts.
- **Pipeline:** `pipeline.py` parses Cricsheet JSON files independently of the UI.
- **Deployment:** One Python web service via `uvicorn app:app --host 0.0.0.0 --port $PORT`.

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/options` | Available teams, venues, seasons for filters |
| `GET /api/dashboard` | All dashboard data (teams, players, toss, venues, issues) |
| `GET /api/records` | Top 10 batting innings, team totals, bowling figures |
| `GET /api/seasons` | Per-season stats (matches, top scorer, top bowler, avg runs) |
| `POST /api/chat` | IPL chatbot — history, rules, player facts, live stats |

## Dashboard Pages

1. **Home** — hero banner, animated metric counters, team cards, cricket concept explainer
2. **Teams** — win rate charts, season trend lines, full stats table with search
3. **Players** — batting/bowling charts (color = strike rate / economy), searchable tables
4. **Toss Analysis** — bat-vs-field win rates, toss impact trend across 19 seasons
5. **Venues** — scatter plot (personality map), average first-innings runs bar chart
6. **Records** — top 10 batting innings, team totals, bowling figures — all from live data
7. **Season History** — year-by-year table: matches, top scorer, top bowler, avg score
8. **Data Quality** — parse issue log with fault-tolerance explanation
9. **Chatbot** — answers IPL history, rules, player facts, and live stats questions

## Logo and Image Handling

- Team logos loaded from Wikipedia CDN (e.g. `upload.wikimedia.org`). If a URL fails, the browser fires `onerror` and swaps to an inline SVG gradient badge generated from team colors.
- Background images loaded from Unsplash (cricket/sports photography). CSS `linear-gradient` overlay ensures text contrast even if images fail.
- No local image files required — the dashboard works with no `static/assets/` folder.

## Fault Tolerance

- Each JSON file is parsed independently. A malformed file is logged and skipped.
- Missing or malformed sections (`info`, `innings`, `overs`, `deliveries`, `runs`) are recorded in the issue log.
- Non-numeric run / extras values are converted to `0` and logged as warnings.
- Ties and no-results are counted in total matches but excluded from win-rate denominators.

## Derived Metrics

Cricsheet JSON does not include pre-computed stats; these are all calculated from ball-by-ball data:

- **Batting strike rate** = batter runs / legal balls faced × 100
- **Batting average** = batter runs / dismissals (`retired hurt` excluded, `retired out` counted)
- **Bowling economy** = bowler runs conceded / overs bowled
- **Bowling average** = bowler runs conceded / bowler wickets
- **Toss win rate** = matches where toss winner = match winner / decisive matches

## Analyses Covered (Problem Statement)

- Win rates by team: overall leaderboard + season-by-season trend
- Best batters: runs, strike rate, average (min 30 balls)
- Best bowlers: wickets, economy, average (min 30 balls)
- Toss impact: by decision (bat/field) and across seasons
- Venue trends: avg 1st innings runs, chasing rate, personality scatter
- Season history: year-by-year records
- Data quality: issue log with parser fault-tolerance
- Chatbot: IPL history, T20 rules, player Q&A, live stats

## Data Quality

Archive: 1,233 matches, 293,308 deliveries, 0 parser issues.
Audit verified: team win rates, batter run totals, bowler wicket totals, overall toss win rate.

## Testing Performed

- `python audit_dashboard.py` — all assertions pass
- API smoke tests: `/api/options`, `/api/dashboard`, `/api/records`, `/api/seasons`, `/api/chat`
- JavaScript syntax check: `node --check static/app.js`
- Manual browser test: all 9 pages, dark/light mode, filters, search, chatbot, records, seasons
