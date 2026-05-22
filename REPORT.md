# REPORT

## Design decisions

- I used Cricsheet JSON because it exposes match metadata and ball-by-ball deliveries in one schema, which is enough to derive all required metrics without relying on pre-aggregated statistics.
- The pipeline is split from the dashboard so the parsing logic can be reused with other datasets that follow the same schema.
- The dashboard is built with Streamlit and Plotly so the filters and charts remain interactive during a live demo.

## Fault tolerance

- Each JSON file is parsed independently. A malformed file is logged and skipped rather than stopping the entire run.
- The parser checks for missing `info`, `innings`, `overs`, `deliveries`, and `runs` sections before using them.
- Invalid innings or deliveries are skipped and recorded in the issues table.
- Records with no decisive winner are kept for participation metrics but excluded from win-rate calculations.

## Metric adaptations

- Cricsheet match files do not provide ready-made batting strike rate or bowling economy fields, so those values are derived from deliveries.
- Batsman strike rate is computed from runs and legal balls faced.
- Bowling economy and average are computed from runs conceded and wickets taken, with byes and leg-byes excluded from bowler runs conceded when available.

## Data quality observations

- The archive contains a few matches with incomplete or inconsistent metadata across historical seasons, so the pipeline avoids hard assumptions about field presence or formatting.
- Team and venue names are treated as free-form values from the dataset instead of being hardcoded.

## Analysis notes

- Team win rates are shown both overall and by season.
- Batters are ranked by runs with strike rate and boundary counts as supporting metrics.
- Bowlers are ranked by wickets with economy, average, and strike rate as supporting metrics.
- Toss impact is summarized by decision type and over time.
- Venue trends compare average first innings totals against batting-first and chasing success.